"""Config flow for Aquamedic."""
from __future__ import annotations
from homeassistant import config_entries
from .const import DOMAIN


class AquamedicConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Aquamedic."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        return self.async_abort(reason="not_implemented")
