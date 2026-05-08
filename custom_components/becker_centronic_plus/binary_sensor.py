from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorDeviceClass,
)
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.device_registry import format_mac
from homeassistant.helpers.entity import EntityCategory
from .entity import BeckerCentronicPlusEntity
from .const import async_signal_device_update, BeckerConfigEntry

async def async_setup_entry(hass, entry: BeckerConfigEntry, async_add_entities):
    """Set up Becker binary sensors."""
    client = entry.runtime_data

    @callback
    def _device_discovered(device):
        async_add_entities([
            BeckerProblemSensor(client, device, entry.entry_id, "blocked"),
            BeckerProblemSensor(client, device, entry.entry_id, "overheated"),
        ])

    entry.async_on_unload(
        async_dispatcher_connect(hass, async_signal_device_update(entry.entry_id), _device_discovered)
    )

class BeckerProblemSensor(BinarySensorEntity, BeckerCentronicPlusEntity):
    """Sensor for blocked or overheated states."""
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, client, device, entry_id, problem_type):
        super().__init__(client, device, entry_id)
        self._type = problem_type
        self._attr_translation_key = problem_type
        self._attr_unique_id = f"{format_mac(device.mac_id)}-{problem_type}"

    @property
    def is_on(self):
        return getattr(self._device, self._type, False)