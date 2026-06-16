"""Binary sensors for Becker Centronic Plus."""

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
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
    """Set up Becker binary sensors."""
    client = entry.runtime_data.client

    @callback
    def _device_discovered(device: CentronicPlusDevice) -> None:
        async_add_entities(
            [
                BeckerProblemSensor(client, device, entry.entry_id, "blocked"),
                BeckerProblemSensor(client, device, entry.entry_id, "overheated"),
            ]
        )

    entry.async_on_unload(
        async_dispatcher_connect(
            hass, async_signal_device_update(entry.entry_id), _device_discovered
        )
    )


class BeckerProblemSensor(BeckerCentronicPlusEntity, BinarySensorEntity):
    """Sensor for blocked or overheated states."""

    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        client: BeckerClient,
        device: CentronicPlusDevice,
        entry_id: str,
        problem_type: str,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(client, device, entry_id)
        self._type = problem_type
        # Present the sensor as the positive state (e.g. "not_blocked") so
        # the check/OK shown by Home Assistant corresponds to the "good" state.
        self._attr_translation_key = f"{problem_type}"
        self._attr_unique_id = f"{format_mac(device.mac_id)}-{problem_type}"

    @cached_property
    def is_on(self) -> bool | None:
        """Return the sensor state."""
        # Invert the underlying problem flag so the entity is ON when there
        # is no problem (so the UI shows the check/OK as a positive state).
        return getattr(self._device, self._type, False)
