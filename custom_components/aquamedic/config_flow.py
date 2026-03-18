"""Config flow for the Aqua Medic integration.

Steps:
  user  →  username + password + region selector
            (region pre-selected from HA language)
  On success: authenticates against Gizwits, logs discovered devices,
              creates the config entry.
"""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .client import AquaMedicAuthError, AquaMedicClient, AquaMedicConnectionError
from .const import (
    CONF_PASSWORD,
    CONF_REGION,
    CONF_USERNAME,
    DEFAULT_REGION,
    DOMAIN,
    GIZWITS_REGIONS,
    LANGUAGE_TO_REGION,
)

_LOGGER = logging.getLogger(__name__)


def _default_region(hass_language: str) -> str:
    """Derive the most likely Gizwits region from the HA language code.

    HA language codes are ISO 639-1 (e.g. 'fr', 'de', 'zh-Hans').
    We try the full code first, then the 2-letter prefix.
    """
    lang = hass_language.lower()
    if lang in LANGUAGE_TO_REGION:
        return LANGUAGE_TO_REGION[lang]
    short = lang.split("-")[0]
    return LANGUAGE_TO_REGION.get(short, DEFAULT_REGION)


def _log_devices(devices: list[dict]) -> None:
    """Log discovered devices at INFO level (visible in HA logs)."""
    if not devices:
        _LOGGER.info("[Aqua Medic] No devices found on this account.")
        return
    _LOGGER.info("[Aqua Medic] %d device(s) found on this account:", len(devices))
    for d in devices:
        name = d.get("dev_alias") or d.get("product_name") or "Unknown"
        did = d.get("did", "?")
        pk = d.get("product_key", "?")
        online = "ONLINE" if d.get("is_online") else "OFFLINE"
        _LOGGER.info(
            "  • %-30s | did=%-24s | pk=%-32s | %s",
            name,
            did,
            pk,
            online,
        )


class AquaMedicConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the Aqua Medic config flow."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle initial setup form."""
        errors: dict[str, str] = {}

        # Determine default region from HA language
        ha_lang = self.hass.config.language or "en"
        suggested_region = _default_region(ha_lang)

        if user_input is not None:
            username = user_input[CONF_USERNAME].strip()
            password = user_input[CONF_PASSWORD]
            region = user_input[CONF_REGION]

            session = async_get_clientsession(self.hass)
            client = AquaMedicClient(session, username, password, region)

            try:
                # Authenticate against Gizwits
                await client.authenticate()

                # Fetch and log devices (useful for debugging / first setup)
                devices = await client.get_devices()
                _log_devices(devices)

            except AquaMedicAuthError:
                _LOGGER.warning(
                    "Authentication failed for user '%s' on region '%s'",
                    username,
                    region,
                )
                errors["base"] = "invalid_auth"

            except AquaMedicConnectionError:
                _LOGGER.exception(
                    "Connection error while authenticating '%s'", username
                )
                errors["base"] = "cannot_connect"

            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected error during Aqua Medic setup")
                errors["base"] = "unknown"

            if not errors:
                # Use username as unique ID to prevent duplicate entries
                await self.async_set_unique_id(f"{region}_{username}")
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=username,
                    data={
                        CONF_USERNAME: username,
                        CONF_PASSWORD: password,
                        CONF_REGION: region,
                    },
                )

        # Build region selector options from GIZWITS_REGIONS dict
        region_options = [
            SelectOptionDict(value=k, label=v) for k, v in GIZWITS_REGIONS.items()
        ]

        schema = vol.Schema(
            {
                vol.Required(CONF_USERNAME): TextSelector(
                    TextSelectorConfig(
                        type=TextSelectorType.EMAIL, autocomplete="email"
                    )
                ),
                vol.Required(CONF_PASSWORD): TextSelector(
                    TextSelectorConfig(
                        type=TextSelectorType.PASSWORD,
                        autocomplete="current-password",
                    )
                ),
                vol.Required(CONF_REGION, default=suggested_region): SelectSelector(
                    SelectSelectorConfig(
                        options=region_options,
                        mode=SelectSelectorMode.LIST,
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )
