"""Covers for Becker Centronic Plus."""

import logging
from typing import Any

from homeassistant.components.cover import (
    CoverDeviceClass,
    CoverEntity,
    CoverEntityFeature,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import format_mac
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from propcache.api import cached_property
from pybeckerplus import Action, BeckerClient, CentronicPlusDevice

from .const import BeckerConfigEntry, async_signal_device_update
from .entity import BeckerCentronicPlusEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BeckerConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Becker covers based on a config entry."""
    client: BeckerClient = entry.runtime_data.client

    @callback
    def _device_discovered(device: CentronicPlusDevice) -> None:
        """Handle discovery or update of a device."""
        async_add_entities([BeckerCover(client, device, entry.entry_id)])

    # Listen for device updates from the library
    entry.async_on_unload(
        async_dispatcher_connect(
            hass, async_signal_device_update(entry.entry_id), _device_discovered
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

    def __init__(
        self, client: BeckerClient, device: CentronicPlusDevice, entry_id: str
    ) -> None:
        """Initialize the cover."""
        super().__init__(client, device, entry_id)
        self._attr_unique_id = format_mac(device.mac_id)
        self._last_action: Action | None = None

    @callback
    def _update_callback(self, device: CentronicPlusDevice) -> None:
        """Update the entity state and check if we need to poll."""
        super()._update_callback(device)
        if not self._device.moving:
            self._last_action = None

    @cached_property
    def current_cover_position(self) -> int | None:
        """Return current position of cover. HA: 0 closed, 100 open."""
        # Library: 0 is open, 100 is closed. Invert for HA.
        return 100 - int(self._device.position)

    @cached_property
    def is_closed(self) -> bool | None:
        """Return if the cover is closed."""
        return self._device.lower_limit

    @cached_property
    def is_opening(self) -> bool | None:
        """Return if the cover is opening."""
        return self._device.moving and self._last_action == Action.UP

    @cached_property
    def is_closing(self) -> bool | None:
        """Return if the cover is closing."""
        return self._device.moving and self._last_action == Action.DOWN

    async def async_open_cover(self, **_kwargs: Any) -> None:
        """Open the cover."""
        self._last_action = Action.UP
        await self._device.up()

    async def async_close_cover(self, **_kwargs: Any) -> None:
        """Close the cover."""
        self._last_action = Action.DOWN
        await self._device.down()

    async def async_stop_cover(self, **_kwargs: Any) -> None:
        """Stop the cover."""
        self._last_action = Action.STOP
        await self._device.stop()

    async def async_set_cover_position(self, **kwargs: Any) -> None:
        """Move the cover to a specific position."""
        pos: int | None = kwargs.get("position")
        if pos is None:
            return
        current_pos = self.current_cover_position
        if current_pos is not None and pos > current_pos:
            self._last_action = Action.UP
        elif current_pos is not None and pos < current_pos:
            self._last_action = Action.DOWN
        else:
            self._last_action = Action.STOP
        # Invert HA position (0-100) to Becker position (100-0)
        await self._device.move_to(100 - pos)

    async def async_set_preset(self, preset: int) -> None:
        """Set the current position as a preset."""
        action = Action.SET_PRESET_1 if preset == 1 else Action.SET_PRESET_2
        await self._device.action(action)

    async def async_delete_preset(self) -> None:
        """Delete both preset positions (Intermediate Position 1 and 2)."""
        await self._device.action(Action.DELETE_PRESETS)
