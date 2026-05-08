import asyncio
import logging
import time

from homeassistant.components.cover import (
    CoverEntity,
    CoverDeviceClass,
    CoverEntityFeature,
)
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.device_registry import format_mac
from pybeckerplus import Action, CentronicDevice
from .polling_helper import BackoffPollingTask
from .entity import BeckerCentronicPlusEntity
from .const import async_signal_device_update, BeckerConfigEntry

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry: BeckerConfigEntry, async_add_entities):
    """Set up Becker covers based on a config entry."""
    client = entry.runtime_data

    @callback
    def _device_discovered(device: CentronicDevice):
        """Handle discovery or update of a device."""
        async_add_entities([BeckerCover(client, device, entry.entry_id)])

    # Listen for device updates from the library
    entry.async_on_unload(
        async_dispatcher_connect(
            hass, 
            async_signal_device_update(entry.entry_id), 
            _device_discovered
        )
    )

class BeckerCover(BeckerCentronicPlusEntity, CoverEntity):
    """Representation of a Becker Centronic Plus Cover."""

    _attr_name = None
    _attr_device_class = CoverDeviceClass.SHUTTER
    _attr_supported_features = (
        CoverEntityFeature.OPEN
        | CoverEntityFeature.CLOSE
        | CoverEntityFeature.STOP
        | CoverEntityFeature.SET_POSITION
    )

    def __init__(self, client, device: CentronicDevice, entry_id):
        """Initialize the cover."""
        super().__init__(client, device, entry_id)
        self._attr_unique_id = format_mac(device.mac_id)
        self._last_action = None
        self._poller = BackoffPollingTask(
            self.hass, _LOGGER, f"becker_poll_{self._device.mac_id}",
            initial_interval=3.5,
            max_interval=30.0,
            backoff_start_delay=60.0,
            max_elapsed_time=600.0,
            grace_period=5.0
        )

    def _start_polling(self) -> None:
        """Start polling using helper."""
        self._poller.start(
            self._device.request_status,
            lambda: self.available and not self._device.moving
        )

    async def async_added_to_hass(self) -> None:
        """Register callbacks."""
        await super().async_added_to_hass()
        self.async_on_remove(self._poller.stop)

    @callback
    def _update_callback(self, device: CentronicDevice) -> None:
        """Update the entity state and check if we need to poll."""
        super()._update_callback(device)
        if not self._device.moving:
            self._last_action = None
        if self._device.moving or not self.available:
            self._start_polling()
        else:
            self._poller.stop()

    @property
    def current_cover_position(self):
        """Return current position of cover. HA: 0 closed, 100 open."""
        # Library: 0 is open, 100 is closed. Invert for HA.
        return 100 - self._device.position

    @property
    def is_closed(self):
        """Return if the cover is closed."""
        return self._device.lower_limit

    @property
    def is_opening(self):
        """Return if the cover is opening."""
        return self._device.moving and self._last_action == Action.UP

    @property
    def is_closing(self):
        """Return if the cover is closing."""
        return self._device.moving and self._last_action == Action.DOWN

    async def async_open_cover(self, **kwargs):
        """Open the cover."""
        self._last_action = Action.UP
        await self._device.up()
        self._start_polling()

    async def async_close_cover(self, **kwargs):
        """Close the cover."""
        self._last_action = Action.DOWN
        await self._device.down()
        self._start_polling()

    async def async_stop_cover(self, **kwargs):
        """Stop the cover."""
        self._last_action = Action.STOP
        await self._device.stop()
        self._start_polling()

    async def async_set_cover_position(self, **kwargs):
        """Move the cover to a specific position."""
        pos = kwargs.get("position")
        if pos > self.current_cover_position:
            self._last_action = Action.UP
        elif pos < self.current_cover_position:
            self._last_action = Action.DOWN
        else:
            self._last_action = Action.STOP
        # Invert HA position (0-100) to Becker position (100-0)
        await self._device.move_to(100 - pos)
        self._start_polling()