"""Switches for Becker Centronic Plus."""

from typing import Any, NamedTuple

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import format_mac
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from propcache.api import cached_property
from pybeckerplus import Action, BeckerClient, CentronicPlusDevice

from .const import BeckerConfigEntry, async_signal_device_update
from .entity import BeckerCentronicPlusEntity


class _BeckerToggleSwitchDescription(NamedTuple):
    translation_key: str
    state_attr: str
    action: Action


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BeckerConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Becker switches."""
    client: BeckerClient = entry.runtime_data.client

    @callback
    def _device_discovered(device: CentronicPlusDevice) -> None:
        async_add_entities(
            [
                BeckerToggleSwitch(
                    client,
                    device,
                    entry.entry_id,
                    _BeckerToggleSwitchDescription(
                        "fly_screen_protection",
                        "fly_screen",
                        Action.TOGGLE_FLY_SCREEN,
                    ),
                ),
                BeckerToggleSwitch(
                    client,
                    device,
                    entry.entry_id,
                    _BeckerToggleSwitchDescription(
                        "anti_freeze_protection",
                        "anti_freeze",
                        Action.TOGGLE_ANTI_FREEZE,
                    ),
                ),
            ]
        )

    entry.async_on_unload(
        async_dispatcher_connect(
            hass, async_signal_device_update(entry.entry_id), _device_discovered
        )
    )


class BeckerToggleSwitch(BeckerCentronicPlusEntity, SwitchEntity):
    """Generic switch for Becker Centronic Plus toggle actions."""

    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self,
        client: BeckerClient,
        device: CentronicPlusDevice,
        entry_id: str,
        description: _BeckerToggleSwitchDescription,
    ) -> None:
        """Initialize the switch."""
        super().__init__(client, device, entry_id)
        self._attr_translation_key = description.translation_key
        self._attr_unique_id = (
            f"{format_mac(device.mac_id)}-{description.translation_key}"
        )
        self._state_attr = description.state_attr
        self._action = description.action

    @cached_property
    def is_on(self) -> bool | None:
        """Return true if the switch is on."""
        return getattr(self._device, self._state_attr, False)

    async def async_turn_on(self, **_kwargs: Any) -> None:
        """Turn the switch on."""
        if not getattr(self._device, self._state_attr, False):
            await self._device.action(self._action)

    async def async_turn_off(self, **_kwargs: Any) -> None:
        """Turn the switch off."""
        if getattr(self._device, self._state_attr, False):
            await self._device.action(self._action)
