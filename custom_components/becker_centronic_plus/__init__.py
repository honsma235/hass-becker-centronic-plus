import asyncio
import logging
from typing import Optional
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.device_registry import format_mac

from pybeckerplus import BeckerClient, CentronicDevice
from .const import DOMAIN, CONF_PORT, BeckerConfigEntry, PLATFORMS, async_signal_device_update
from .polling_helper import BackoffPollingTask

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: BeckerConfigEntry) -> bool:
    """Set up Becker Centronic Plus from a config entry."""
    
    known_devices: set[str] = set()

    def _sync_name(mac_id: str, new_name: str | None) -> None:
        """Schedule a background task to push the name to hardware if it differs."""
        if not new_name or not (device_obj := client.get_device(mac_id)):
            return

        if device_obj.name == new_name:
            return

        async def _perform_sync() -> None:
            _LOGGER.debug("Syncing name for %s to Becker hardware: %s", mac_id, new_name)
            try:
                await device_obj.set_name(new_name)
            except Exception as err:
                _LOGGER.warning("Could not sync name for %s: %s", mac_id, err)

        entry.async_create_background_task(hass, _perform_sync(), f"becker_sync_name_{mac_id}")

    @callback
    def _handle_disconnect(exception: Optional[Exception]) -> None:
        _LOGGER.warning("Becker USB stick disconnected: %s", exception)
        # Signal entities to update their availability (show as 'unavailable' in UI)
        async_dispatcher_send(hass, f"{async_signal_device_update(entry.entry_id)}_status")
        # Trigger a full reload of the integration
        hass.config_entries.async_schedule_reload(entry.entry_id)

    @callback
    def _on_device_update(device: CentronicDevice) -> None:
        """Forward library callbacks to Home Assistant dispatcher."""
        # Discovery: only signal once per MAC per entry to avoid race conditions
        if device.mac_id not in known_devices:
            known_devices.add(device.mac_id)
            _LOGGER.debug("Discovered new Becker device: %s", device.mac_id)
            
            # Sync custom name from HA registry to hardware on first discovery
            dev_reg = dr.async_get(hass)
            if (dev_entry := dev_reg.async_get_device(identifiers={(DOMAIN, format_mac(device.mac_id))})):
                _sync_name(device.mac_id, dev_entry.name_by_user)

            async_dispatcher_send(hass, async_signal_device_update(entry.entry_id), device)
        
        # State update: signal individual entity for state changes
        async_dispatcher_send(hass, async_signal_device_update(entry.entry_id, device.mac_id), device)

    client = BeckerClient(
        entry.data[CONF_PORT], 
        device_callback=lambda dev: hass.add_job(_on_device_update, dev),
        on_disconnect=lambda exc: hass.add_job(_handle_disconnect, exc)
    )
    
    try:
        await client.connect()
        await client.update_stick_info()
    except Exception as err:
        raise ConfigEntryNotReady(
            f"Could not connect to Becker USB stick at {entry.data[CONF_PORT]}: {err}"
        ) from err

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
    def _handle_device_registry_update(event: dr.EventDeviceRegistryUpdatedData) -> None:
        """Handle device registry updates to propagate name changes to hardware."""
        if event.data["action"] != "update" or "name_by_user" not in event.data["changes"]:
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

    entry.async_on_unload(hass.bus.async_listen(dr.EVENT_DEVICE_REGISTRY_UPDATED, _handle_device_registry_update))

    async def _async_discovery_and_status_loop() -> None:
        """Manages discovery and periodic status requests."""
        # Phase 1: Aggressive Discovery (One-way)
        discovery_poller = BackoffPollingTask(
            hass, _LOGGER, "becker_discovery_loop",
            initial_interval=30.0,
            max_interval=300.0,
            backoff_start_delay=300.0,
            max_elapsed_time=1800.0
        )
        discovery_poller.start(client.start_discovery, lambda: client.all_devices_ready)
        
        # Wait until discovery is "finished" (all devices ready)
        await discovery_poller.wait()

        # Phase 2: Maintenance Phase
        _LOGGER.info("All Becker devices ready. Switching to periodic status updates.")
        while True:
            # Global status request on the client
            await client.global_request_status()
            # Wait for 30 minutes
            await asyncio.sleep(1800)

    entry.runtime_data = client
    
    # Load platforms (cover.py)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    _LOGGER.debug("Becker Centronic Plus integration set up for port %s", entry.data[CONF_PORT])
    
    # Start the continuous discovery and status loop
    entry.async_create_background_task(hass, _async_discovery_and_status_loop(), "becker_discovery_status_loop")
    
    return True

async def async_unload_entry(hass: HomeAssistant, entry: BeckerConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        await entry.runtime_data.close()
    return unload_ok