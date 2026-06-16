"""Diagnostics support for Becker Centronic Plus."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .const import BeckerConfigEntry


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,  # noqa: ARG001
    entry: BeckerConfigEntry,
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    client = entry.runtime_data.client

    return {
        "port": client.port,
        "discovery_info": entry.data.get("discovery_info"),
        "fw_version": client.stick_fw,
        "devices": [
            {
                "name": device.name,
                "rssi": device.rssi,
                "firmware_version": device.firmware_version,
                "available": device.available,
                "got_status": device._got_status,  # noqa: SLF001 # pyright: ignore[reportPrivateUsage]
                "position": device.position,
                "blocked": device.blocked,
                "overheated": device.overheated,
            }
            for device in client.devices.values()
        ],
    }
