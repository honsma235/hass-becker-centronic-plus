"""
Becker Centronic Plus integration for Home Assistant.

Provides setup/unload entry points and bridges the pybeckerplus
library to Home Assistant entities and device registry.
"""

import logging
from typing import TYPE_CHECKING

import voluptuous as vol
from homeassistant.components.cover import DOMAIN as COVER_DOMAIN
from homeassistant.config_entries import UnknownEntry
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import service
from homeassistant.helpers.device_registry import format_mac
from homeassistant.helpers.dispatcher import async_dispatcher_send
from pybeckerplus import BeckerClient, CentronicPlusDevice

from .const import (
    CONF_PORT,
    DOMAIN,
    PLATFORMS,
    BeckerClientData,
    BeckerConfigEntry,
    async_signal_device_update,
)

if TYPE_CHECKING:
    from homeassistant.helpers.typing import ConfigType

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, _config: ConfigType) -> bool:
    """Set up the Becker Centronic Plus integration."""
    # Register entity services in async_setup as per documentation guidelines
    # to ensure they are available even if config entries are not yet loaded.
    service.async_register_platform_entity_service(
        hass,
        DOMAIN,
        "set_preset",
        entity_domain=COVER_DOMAIN,
        schema={vol.Required("preset"): vol.All(vol.Coerce(int), vol.In([1, 2]))},
        func="async_set_preset",
    )
    service.async_register_platform_entity_service(
        hass,
        DOMAIN,
        "delete_preset",
        entity_domain=COVER_DOMAIN,
        schema=None,
        func="async_delete_preset",
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: BeckerConfigEntry) -> bool:  # noqa: PLR0915
    """Set up Becker Centronic Plus from a config entry."""
    known_devices: set[str] = set()

    def _sync_name(mac_id: str, new_name: str | None) -> None:
        """Schedule a background task to push the name to hardware if it differs."""
        if not new_name or not (device_obj := client.get_device(mac_id)):
            return

        if device_obj.name == new_name:
            return

        async def _perform_sync() -> None:
            _LOGGER.debug(
                "Syncing name for %s to Becker hardware: %s", mac_id, new_name
            )
            try:
                await device_obj.set_name(new_name)
            except Exception as err:  # noqa: BLE001
                _LOGGER.warning("Could not sync name for %s: %s", mac_id, err)

        entry.async_create_background_task(
            hass, _perform_sync(), f"becker_sync_name_{mac_id}"
        )

    @callback
    def _handle_disconnect(exception: Exception | None) -> None:
        # Skip handling if we're already unloading or not yet initialized
        try:
            if entry.runtime_data.is_unloading:
                _LOGGER.debug(
                    "Becker USB stick disconnected during unload: %s", exception
                )
                return
        except AttributeError, RuntimeError:
            pass

        _LOGGER.warning("Becker USB stick disconnected: %s", exception)
        # Signal entities to update their availability (show as 'unavailable' in UI)
        async_dispatcher_send(
            hass, f"{async_signal_device_update(entry.entry_id)}_status"
        )
        # Trigger a full reload of the integration
        # Handle race condition: entry may be deleted while we're trying to reload
        try:
            hass.config_entries.async_schedule_reload(entry.entry_id)
        except UnknownEntry:
            _LOGGER.debug(
                "Config entry %s no longer exists; skipping reload", entry.entry_id
            )

    @callback
    def _on_device_update(device: CentronicPlusDevice) -> None:
        """Forward library callbacks to Home Assistant dispatcher."""
        # Discovery: only signal once per MAC per entry to avoid race conditions
        if device.mac_id not in known_devices:
            known_devices.add(device.mac_id)
            _LOGGER.debug("Discovered new Becker device: %s", device.mac_id)

            # Sync custom name from HA registry to hardware on first discovery
            dev_reg = dr.async_get(hass)
            if dev_entry := dev_reg.async_get_device(
                identifiers={(DOMAIN, format_mac(device.mac_id))}
            ):
                _sync_name(device.mac_id, dev_entry.name_by_user)

            async_dispatcher_send(
                hass, async_signal_device_update(entry.entry_id), device
            )

        # State update: signal individual entity for state changes
        async_dispatcher_send(
            hass, async_signal_device_update(entry.entry_id, device.mac_id), device
        )

    client = BeckerClient(
        entry.data[CONF_PORT],
        device_callback=lambda dev: hass.add_job(_on_device_update, dev),
        on_disconnect=lambda exc: hass.add_job(_handle_disconnect, exc),
        enable_polling=True,
    )

    try:
        await client.connect()
        await client.initialize()
    except Exception as err:
        await client.close()
        msg = f"Could not connect to Becker USB stick at {entry.data[CONF_PORT]}: {err}"
        raise ConfigEntryNotReady(msg) from err

    # Explicitly register the USB Stick device before loading platforms
    # to prevent "via_device" race conditions.
    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, format_mac(client.stick_mac))},
        manufacturer="Becker",
        translation_key="becker",
        model="Centronic PLUS USB",
        sw_version=client.stick_fw,
    )

    @callback
    def _handle_device_registry_update(
        event: Event[dr.EventDeviceRegistryUpdatedData],
    ) -> None:
        """Handle device registry updates to propagate name changes to hardware."""
        if (
            event.data["action"] != "update"
            or "name_by_user" not in event.data["changes"]
        ):
            return

        dev_reg = dr.async_get(hass)
        if not (device := dev_reg.async_get(event.data["device_id"])):
            return

        if entry.entry_id not in device.config_entries:
            return

        # Find the MAC address in the device identifiers
        for domain, mac in device.identifiers:
            if domain == DOMAIN:
                # Skip the USB stick itself if the library renaming is only for shutters
                if mac == format_mac(client.stick_mac):
                    continue

                _sync_name(mac, device.name_by_user)
                break

    entry.async_on_unload(
        hass.bus.async_listen(
            dr.EVENT_DEVICE_REGISTRY_UPDATED, _handle_device_registry_update
        )
    )

    entry.runtime_data = BeckerClientData(client)

    # Load platforms (cover.py)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    _LOGGER.debug(
        "Becker Centronic Plus integration set up for port %s", entry.data[CONF_PORT]
    )

    # Start the library's internal monitoring
    await client.start_monitoring(restart=False)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: BeckerConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        await entry.runtime_data.close()
    return unload_ok


async def async_remove_config_entry_device(
    _hass: HomeAssistant, entry: BeckerConfigEntry, device_entry: dr.DeviceEntry
) -> bool:
    """Remove a config entry from a device."""
    client = entry.runtime_data.client
    stick_mac = format_mac(client.stick_mac)
    for identifier in device_entry.identifiers:
        if identifier[0] == DOMAIN:
            if identifier[1] == stick_mac:
                return False
            if device := client.get_device(identifier[1]):
                return not device.available
    return True
