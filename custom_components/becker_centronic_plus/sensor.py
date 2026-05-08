from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.device_registry import format_mac
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from .entity import BeckerCentronicPlusEntity
from .const import async_signal_device_update, BeckerConfigEntry

async def async_setup_entry(hass, entry: BeckerConfigEntry, async_add_entities):
    """Set up Becker sensors."""
    client = entry.runtime_data

    @callback
    def _device_discovered(device):
        async_add_entities([BeckerRSSISensor(client, device, entry.entry_id)])

    entry.async_on_unload(
        async_dispatcher_connect(hass, async_signal_device_update(entry.entry_id), _device_discovered)
    )

class BeckerRSSISensor(BeckerCentronicPlusEntity, SensorEntity):
    """Representation of the RSSI sensor."""

    _attr_device_class = SensorDeviceClass.SIGNAL_STRENGTH
    _attr_state_class = SensorStateClass.MEASUREMENT
    # Not sure if that value has a proper unit. Seems just a value between 0 and 255. Todo: check radio ic datasheet
    # _attr_native_unit_of_measurement = SIGNAL_STRENGTH_DECIBELS_MILLIWATT
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False
    _attr_translation_key = "rssi"

    def __init__(self, client, device, entry_id):
        super().__init__(client, device, entry_id)
        self._attr_unique_id = f"{format_mac(device.mac_id)}-rssi"

    @property
    def native_value(self):
        return self._device.rssi