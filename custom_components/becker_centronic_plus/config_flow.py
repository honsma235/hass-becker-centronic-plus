"""Config flow for Becker Centronic Plus."""

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import SOURCE_RECONFIGURE, ConfigFlowResult
from homeassistant.helpers.device_registry import format_mac
from homeassistant.helpers.service_info.usb import UsbServiceInfo
from pybeckerplus import BeckerClient, BeckerError

from .const import CONF_PORT, DOMAIN

_LOGGER = logging.getLogger(__name__)


class BeckerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Becker Centronic Plus."""

    VERSION = 1

    async def _validate_serial_port(self, serial_port: str) -> str:
        """
        Validate the serial port by connecting to it and reading the MAC adsress.
        Returns the mac addres or raises an error.
        """  # noqa: D205
        client = BeckerClient(serial_port)
        mac: str
        try:
            await client.connect()
            await client.initialize()
            mac = format_mac(client.stick_mac)
        finally:
            try:
                await client.close()
            except Exception:  # noqa: BLE001 - defensive close; don't mask original exceptions
                _LOGGER.debug(
                    "Error closing BeckerClient for %s", serial_port, exc_info=True
                )

        return mac

    async def async_step_usb(self, discovery_info: UsbServiceInfo) -> ConfigFlowResult:
        """Handle a flow initialized by USB discovery."""
        try:
            # Validate by connecting to the stick and reading its MAC address
            mac = await self._validate_serial_port(discovery_info.device)
        except Exception:  # noqa: BLE001
            # Silent abort on failure to avoid popups for unrelated USB devices
            return self.async_abort(reason="not_centronic_plus_device")

        # Create a unique ID based on MAC to prevent duplicates
        await self.async_set_unique_id(mac)

        # If this stick is already configured, abort discovery.
        # Respect the manually configured port; users can reconfigure if needed.
        self._abort_if_unique_id_configured()

        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        self._discovery_info = discovery_info
        return await self.async_step_discovery_confirm()

    async def async_step_discovery_confirm(
        self, user_input: Any = None
    ) -> ConfigFlowResult:
        """Confirm discovery from USB."""
        if user_input is not None:
            return self.async_create_entry(
                title="Becker Centronic Plus",
                data={
                    CONF_PORT: self._discovery_info.device,
                    "discovery_info": {
                        "vid": self._discovery_info.vid,
                        "pid": self._discovery_info.pid,
                        "manufacturer": self._discovery_info.manufacturer,
                        "description": self._discovery_info.description,
                    },
                },
            )
        return self.async_show_form(
            step_id="discovery_confirm",
            description_placeholders={"port": self._discovery_info.device},
        )

    async def async_step_user(self, user_input: Any = None) -> ConfigFlowResult:
        """Handle the initial step."""
        # Ensure only one instance of the integration can be configured,
        # but allow the reconfigure flow to proceed.
        if self.source != SOURCE_RECONFIGURE and self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        errors: dict[str, str] = {}
        description_placeholders: dict[str, str] = {}
        reconfigure_entry = (
            self._get_reconfigure_entry() if self.source == SOURCE_RECONFIGURE else None
        )

        if user_input is not None:
            if reconfigure_entry is not None:
                # unload existing entry
                await self.hass.config_entries.async_unload(reconfigure_entry.entry_id)

            try:
                mac = await self._validate_serial_port(user_input[CONF_PORT])
            except (BeckerError, OSError, ValueError) as err:
                _LOGGER.debug(
                    "Failed to connect to Becker stick at %s: %s",
                    user_input[CONF_PORT],
                    err,
                )
                errors["base"] = "cannot_connect"
                description_placeholders["error_detail"] = str(err)
                if reconfigure_entry is not None:
                    # reload the old entry
                    await self.hass.config_entries.async_setup(
                        reconfigure_entry.entry_id
                    )
            else:
                await self.async_set_unique_id(mac)
                if self.source != SOURCE_RECONFIGURE:
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(
                        title="Becker Centronic Plus", data=user_input
                    )

                # For reconfigure flows, update the existing entry instead
                # of creating a new one.
                if reconfigure_entry is None:
                    raise RuntimeError
                return self.async_update_reload_and_abort(
                    reconfigure_entry,
                    data_updates=user_input,
                    reason="reconfigure_successful",
                )

        default_port = (
            user_input[CONF_PORT]
            if user_input is not None
            else reconfigure_entry.data.get(CONF_PORT, "")
            if reconfigure_entry is not None
            else "/dev/serial/by-id/usb-Becker-Antriebe_GmbH_CentronicPlus_Stick-if00"
        )

        # Use "reconfigure" step ID if we are in reconfiguration mode
        # to show appropriate text
        step_id = "reconfigure" if self.source == SOURCE_RECONFIGURE else "user"

        return self.async_show_form(
            step_id=step_id,
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_PORT, default=default_port): str,
                }
            ),
            errors=errors,
            description_placeholders=description_placeholders,
        )

    async def async_step_reconfigure(self, user_input: Any = None) -> ConfigFlowResult:
        """Handle reconfiguration of the serial port for an existing entry."""
        return await self.async_step_user(user_input)
