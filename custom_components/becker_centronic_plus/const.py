"""Constants for the Becker Centronic Plus integration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.config_entries import ConfigEntry

if TYPE_CHECKING:
    from pybeckerplus import BeckerClient

DOMAIN = "becker_centronic_plus"
CONF_PORT = "port"
SIGNAL_DEVICE_UPDATE = f"{DOMAIN}_device_update"
PLATFORMS = ["cover", "sensor", "binary_sensor", "switch", "button"]


class BeckerClientData:
    """Wrapper for BeckerClient with unload state tracking."""

    def __init__(self, client: BeckerClient) -> None:
        """Initialize the wrapper."""
        self.client = client
        self.is_unloading = False

    async def close(self) -> None:
        """Close the client and mark as unloading."""
        self.is_unloading = True
        await self.client.close()


type BeckerConfigEntry = ConfigEntry[BeckerClientData]


def async_signal_device_update(entry_id: str, mac_id: str | None = None) -> str:
    """Generate a device update signal name."""
    if mac_id:
        return f"{SIGNAL_DEVICE_UPDATE}_{entry_id}_{mac_id}"
    return f"{SIGNAL_DEVICE_UPDATE}_{entry_id}"
