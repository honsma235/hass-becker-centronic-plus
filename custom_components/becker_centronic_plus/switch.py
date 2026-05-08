from homeassistant.components.switch import SwitchEntity
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.device_registry import format_mac
from homeassistant.helpers.entity import EntityCategory
from pybeckerplus import Action
from .entity import BeckerCentronicPlusEntity
from .const import async_signal_device_update, BeckerConfigEntry

async def async_setup_entry(hass, entry: BeckerConfigEntry, async_add_entities):
    """Set up Becker switches."""
    client = entry.runtime_data

    @callback
    def _device_discovered(device):
        async_add_entities([
            BeckerFlyScreenSwitch(client, device, entry.entry_id),
        ])

    entry.async_on_unload(
        async_dispatcher_connect(hass, async_signal_device_update(entry.entry_id), _device_discovered)
    )

class BeckerFlyScreenSwitch(BeckerCentronicPlusEntity, SwitchEntity):
    """Switch for fly screen protection."""
    _attr_entity_category = EntityCategory.CONFIG
    _attr_translation_key = "fly_screen_protection"
    
    def __init__(self, client, device, entry_id):
        super().__init__(client, device, entry_id)
        self._attr_unique_id = f"{format_mac(device.mac_id)}-fly_screen_protection"

    @property
    def is_on(self):
        """Return true if the switch is on."""
        return self._device.fly_screen

    # The Becker protocol uses a single TOGGLE command.
    # If the fly_screen is already off, TOGGLE will turn it on.
    # If it's on, TOGGLE will turn it off.
    # So, we only send the command if the state is not already what we want.

    async def async_turn_on(self, **kwargs):
        """Turn the switch on."""
        if not self._device.fly_screen:
            await self._device.action(Action.TOGGLE_FLY_SCREEN)

    async def async_turn_off(self, **kwargs):
        """Turn the switch off."""
        if self._device.fly_screen:
            await self._device.action(Action.TOGGLE_FLY_SCREEN)