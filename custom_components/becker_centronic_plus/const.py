"""Constants for the Becker Centronic Plus integration."""
from homeassistant.config_entries import ConfigEntry
from pybeckerplus import BeckerClient

DOMAIN = "becker_centronic_plus"
CONF_PORT = "port"
SIGNAL_DEVICE_UPDATE = f"{DOMAIN}_device_update"
PLATFORMS = ["cover", "sensor", "binary_sensor", "switch", "button"]

type BeckerConfigEntry = ConfigEntry[BeckerClient]

def async_signal_device_update(entry_id: str, mac_id: str | None = None) -> str:
    """Helper to generate signal names."""
    if mac_id:
        return f"{SIGNAL_DEVICE_UPDATE}_{entry_id}_{mac_id}"
    return f"{SIGNAL_DEVICE_UPDATE}_{entry_id}"