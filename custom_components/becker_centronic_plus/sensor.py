"""Sensors for Becker Centronic Plus."""

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import format_mac
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from propcache.api import cached_property
from pybeckerplus import BeckerClient, CentronicPlusDevice

from .const import BeckerConfigEntry, async_signal_device_update
from .entity import BeckerCentronicPlusEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BeckerConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Becker sensors."""
    client: BeckerClient = entry.runtime_data.client

    @callback
    def _device_discovered(device: CentronicPlusDevice) -> None:
        async_add_entities([BeckerRSSISensor(client, device, entry.entry_id)])

    entry.async_on_unload(
        async_dispatcher_connect(
            hass, async_signal_device_update(entry.entry_id), _device_discovered
        )
    )


class BeckerRSSISensor(BeckerCentronicPlusEntity, SensorEntity):
    """Representation of the RSSI sensor."""

    _attr_device_class = SensorDeviceClass.SIGNAL_STRENGTH
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False
    _attr_translation_key = "rssi"

    def __init__(
        self, client: BeckerClient, device: CentronicPlusDevice, entry_id: str
    ) -> None:
        """Initialize the sensor."""
        super().__init__(client, device, entry_id)
        self._attr_unique_id = f"{format_mac(device.mac_id)}-rssi"

    @cached_property
    def native_value(self) -> int | None:
        """Return the RSSI signal strength."""
        return self._device.rssi
