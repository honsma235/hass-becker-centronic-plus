"""Buttons for Becker Centronic Plus."""

import logging

from homeassistant.components.button import ButtonDeviceClass, ButtonEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo, format_mac
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from propcache.api import cached_property
from pybeckerplus import Action, BeckerClient, CentronicPlusDevice

from .const import DOMAIN, BeckerConfigEntry, async_signal_device_update
from .entity import BeckerCentronicPlusEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BeckerConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Becker buttons based on a config entry."""
    client: BeckerClient = entry.runtime_data.client

    # Add USB Stick refresh button
    async_add_entities(
        [
            BeckerStickRefreshButton(client, entry.entry_id),
        ]
    )

    @callback
    def _device_discovered(device: CentronicPlusDevice) -> None:
        """Handle discovery or update of a device."""
        async_add_entities(
            [
                BeckerIdentifyButton(client, device, entry.entry_id),
                BeckerPresetButton(client, device, entry.entry_id, 1),
                BeckerPresetButton(client, device, entry.entry_id, 2),
            ]
        )

    entry.async_on_unload(
        async_dispatcher_connect(
            hass, async_signal_device_update(entry.entry_id), _device_discovered
        )
    )


class BeckerPresetButton(BeckerCentronicPlusEntity, ButtonEntity):
    """Button to trigger a preset position."""

    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self,
        client: BeckerClient,
        device: CentronicPlusDevice,
        entry_id: str,
        preset_num: int,
    ) -> None:
        """Initialize the button."""
        super().__init__(client, device, entry_id)
        self._preset_num: int = preset_num
        self._attr_translation_key = f"preset_{preset_num}"
        self._attr_unique_id = f"{format_mac(device.mac_id)}-preset_{preset_num}"

    async def async_press(self) -> None:
        """Handle the button press."""
        action = Action.PRESET_1 if self._preset_num == 1 else Action.PRESET_2
        await self._device.action(action)


class BeckerIdentifyButton(BeckerCentronicPlusEntity, ButtonEntity):
    """Button to identify a device (jog)."""

    _attr_device_class = ButtonDeviceClass.IDENTIFY
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_translation_key = "identify"

    def __init__(
        self, client: BeckerClient, device: CentronicPlusDevice, entry_id: str
    ) -> None:
        """Initialize the button."""
        super().__init__(client, device, entry_id)
        self._attr_unique_id = f"{format_mac(device.mac_id)}-identify"

    async def async_press(self) -> None:
        """Handle the button press."""
        await self._device.identify()


class BeckerStickRefreshButton(ButtonEntity):
    """Button to refresh the USB stick monitoring."""

    _attr_device_class = ButtonDeviceClass.RESTART
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_translation_key = "refresh"
    _attr_has_entity_name = True

    def __init__(self, client: BeckerClient, entry_id: str) -> None:
        """Initialize the button."""
        self._client = client
        self._entry_id = entry_id
        self._attr_unique_id = f"{format_mac(client.stick_mac)}-refresh"

    @cached_property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return DeviceInfo(
            identifiers={(DOMAIN, format_mac(self._client.stick_mac))},
            manufacturer="Becker",
            model="Centronic PLUS USB",
        )

    @cached_property
    def available(self) -> bool:
        """Return True if the USB stick is connected."""
        return self._client.connected

    async def async_press(self) -> None:
        """Handle the button press."""
        _LOGGER.debug("Refreshing Becker USB stick monitoring")
        await self._client.start_monitoring(restart=True)
