from homeassistant.components.button import ButtonEntity, ButtonDeviceClass
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.device_registry import format_mac
from homeassistant.helpers.entity import EntityCategory
from pybeckerplus import Action
from .entity import BeckerCentronicPlusEntity
from .const import async_signal_device_update, BeckerConfigEntry

async def async_setup_entry(hass, entry: BeckerConfigEntry, async_add_entities):
    """Set up Becker buttons based on a config entry."""
    client = entry.runtime_data

    @callback
    def _device_discovered(device):
        """Handle discovery or update of a device."""
        async_add_entities([
            BeckerIdentifyButton(client, device, entry.entry_id),
            BeckerPresetButton(client, device, entry.entry_id, 1),
            BeckerPresetButton(client, device, entry.entry_id, 2),
        ])

    entry.async_on_unload(
        async_dispatcher_connect(hass, async_signal_device_update(entry.entry_id), _device_discovered)
    )

class BeckerPresetButton(BeckerCentronicPlusEntity, ButtonEntity):
    """Button to trigger a preset position."""

    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, client, device, entry_id, preset_num):
        """Initialize the button."""
        super().__init__(client, device, entry_id)
        self._preset_num = preset_num
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

    def __init__(self, client, device, entry_id):
        """Initialize the button."""
        super().__init__(client, device, entry_id)
        self._attr_unique_id = f"{format_mac(device.mac_id)}-identify"

    async def async_press(self) -> None:
        """Handle the button press."""
        await self._device.identify()