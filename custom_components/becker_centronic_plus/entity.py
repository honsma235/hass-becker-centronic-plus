"""Base entity for Becker Centronic Plus."""
from homeassistant.core import callback
from homeassistant.helpers.device_registry import format_mac
from homeassistant.helpers.entity import DeviceInfo, Entity
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from pybeckerplus import CentronicDevice, BeckerClient
from .const import DOMAIN, async_signal_device_update

class BeckerCentronicPlusEntity(Entity):
    """Base class for Becker Centronic Plus entities."""

    _attr_has_entity_name = True

    def __init__(self, client: BeckerClient, device: CentronicDevice, entry_id: str) -> None:
        """Initialize the entity."""
        self._client = client
        self._device = device
        self._entry_id = entry_id

    @property
    def available(self) -> bool:
        """Return True if both the stick is connected and the device is known."""
        return self._client.connected and self._device.available

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return DeviceInfo(
            identifiers={(DOMAIN, format_mac(self._device.mac_id))},
            name=self._device.name or f"Becker {self._device.mac_id[-4:]}",
            manufacturer="Becker",
            model="Centronic Plus Shutter",
            via_device=(DOMAIN, format_mac(self._client.stick_mac)),
            sw_version=self._device.firmware_version,
            serial_number=self._device.serial_number,
        )

    async def async_added_to_hass(self) -> None:
        """Register callbacks."""
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                async_signal_device_update(self._entry_id, self._device.mac_id),
                self._update_callback,
            )
        )
        # Listen for connection status changes (connected/disconnected)
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{async_signal_device_update(self._entry_id)}_status",
                self.async_write_ha_state,
            )
        )

    @callback
    def _update_callback(self, device: CentronicDevice) -> None:
        """Update the entity state."""
        self._device = device
        self.async_write_ha_state()