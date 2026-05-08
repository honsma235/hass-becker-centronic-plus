import logging
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components import usb
from homeassistant.helpers.device_registry import format_mac
from pybeckerplus import BeckerClient
from .const import DOMAIN, CONF_PORT

_LOGGER = logging.getLogger(__name__)

class BeckerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Becker Centronic Plus."""

    VERSION = 1

    async def _validate_serial_port(self, serial_port):
        """Validate the serial port by connecting to it and reading the MAC adsress.
        Returns the mac addres or raises an error."""
        client = BeckerClient(serial_port)
        await client.connect()
        await client.update_stick_info()
        mac = format_mac(client.stick_mac)
        await client.close()
        return mac


    async def async_step_usb(self, discovery_info: usb.UsbServiceInfo):
        """Handle a flow initialized by USB discovery."""

        try:
            # Validate by connecting to the stick and reading its MAC address
            mac = await self._validate_serial_port(discovery_info.device)
        except Exception as err:
            # Silent abort on failure to avoid popups for unrelated USB devices
            return self.async_abort(reason="not_centronic_plus_device")
        
        
        # Create a unique ID based on MAC to prevent duplicates and handle port changes
        await self.async_set_unique_id(mac)
        
        # If this stick is already configured but on a different port, update it and abort
        self._abort_if_unique_id_configured(updates={CONF_PORT: discovery_info.device})

        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        self._discovery_info = discovery_info
        return await self.async_step_discovery_confirm()


    async def async_step_discovery_confirm(self, user_input=None):
        """Confirm discovery from USB."""
        if user_input is not None:
            return self.async_create_entry(
                title="Becker Centronic Plus",
                data={CONF_PORT: self._discovery_info.device},
            )
        #self._set_confirm_only()
        return self.async_show_form(
            step_id="discovery_confirm",
            description_placeholders={"port": self._discovery_info.device},
        )
    

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        # Ensure only one instance of the integration can be configured
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        errors = {}
        description_placeholders = {}
        if user_input is not None:
            # Validate connection and read MAC address for unique_id
            try:
                mac = await self._validate_serial_port(user_input[CONF_PORT])
            except Exception as err:
                _LOGGER.debug("Failed to connect to Becker stick at %s: %s", user_input[CONF_PORT], err)
                errors["base"] = "cannot_connect"
                description_placeholders["error_detail"] = str(err)
            else:
                await self.async_set_unique_id(mac)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title="Becker Centronic Plus",
                    data=user_input
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(
                    CONF_PORT, 
                    default="/dev/serial/by-id/usb-Becker-Antriebe_GmbH_CentronicPlus_Stick-if00"
                ): str,
            }),
            errors=errors,
            description_placeholders=description_placeholders,
        )
