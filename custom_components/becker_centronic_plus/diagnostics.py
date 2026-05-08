"""Diagnostics support for Becker Centronic Plus."""
from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from .const import BeckerConfigEntry

TO_REDACT = {"unique_id", "mac_id", "serial_number"}

async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: BeckerConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    client = entry.runtime_data

    return async_redact_data(
        {
            "fw_version": client.stick_fw,
            "install_id": client.stick_install_id,
        },
        TO_REDACT,
    )