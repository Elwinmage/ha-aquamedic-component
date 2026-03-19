"""Config flow for the Aqua Medic integration.

Steps:
  user  → username + password + region (pre-selected from HA language)
          + scan_interval

Options flow:
  init  → scan_interval
"""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
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
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
    DEFAULT_REGION,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    GIZWITS_REGIONS,
    LANGUAGE_TO_REGION,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)


def _default_region(hass_language: str) -> str:
    lang = hass_language.lower()
    if lang in LANGUAGE_TO_REGION:
        return LANGUAGE_TO_REGION[lang]
    return LANGUAGE_TO_REGION.get(lang.split("-")[0], DEFAULT_REGION)


def _log_devices(devices: list[dict]) -> None:
    if not devices:
        _LOGGER.info("[Aqua Medic] No devices found on this account.")
        return
    _LOGGER.info("[Aqua Medic] %d device(s) found:", len(devices))
    for d in devices:
        name = d.get("dev_alias") or d.get("product_name") or "Unknown"
        did = d.get("did", "?")
        pk = d.get("product_key", "?")
        online = "ONLINE" if d.get("is_online") else "OFFLINE"
        _LOGGER.info("  • %-30s | did=%-24s | pk=%-32s | %s", name, did, pk, online)


def _interval_selector() -> NumberSelector:
    return NumberSelector(
        NumberSelectorConfig(
            min=MIN_SCAN_INTERVAL,
            max=MAX_SCAN_INTERVAL,
            step=5,
            unit_of_measurement="s",
            mode=NumberSelectorMode.BOX,
        )
    )


class AquaMedicConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the Aqua Medic config flow."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        errors: dict[str, str] = {}

        ha_lang = self.hass.config.language or "en"
        default_region = _default_region(ha_lang)

        if user_input is not None:
            username = user_input[CONF_USERNAME].strip()
            password = user_input[CONF_PASSWORD]
            region = user_input[CONF_REGION]
            interval = int(user_input.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL))

            session = async_get_clientsession(self.hass)
            client = AquaMedicClient(session, username, password, region)

            try:
                await client.authenticate()
                devices = await client.get_devices()
                _log_devices(devices)
            except AquaMedicAuthError:
                errors["base"] = "invalid_auth"
            except AquaMedicConnectionError:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected error during Aqua Medic setup")
                errors["base"] = "unknown"

            if not errors:
                await self.async_set_unique_id(f"{region}_{username}")
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=username,
                    data={
                        CONF_USERNAME: username,
                        CONF_PASSWORD: password,
                        CONF_REGION: region,
                        CONF_SCAN_INTERVAL: interval,
                    },
                )

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
                vol.Required(CONF_REGION, default=default_region): SelectSelector(
                    SelectSelectorConfig(
                        options=region_options, mode=SelectSelectorMode.LIST
                    )
                ),
                vol.Required(
                    CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL
                ): _interval_selector(),
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> config_entries.OptionsFlow:
        return AquaMedicOptionsFlow(config_entry)


class AquaMedicOptionsFlow(config_entries.OptionsFlow):
    """Handle Aqua Medic options (scan interval only)."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        if user_input is not None:
            new_data = dict(self._config_entry.data)
            new_data[CONF_SCAN_INTERVAL] = int(user_input[CONF_SCAN_INTERVAL])
            self.hass.config_entries.async_update_entry(
                self._config_entry, data=new_data
            )
            self.hass.config_entries.async_schedule_reload(self._config_entry.entry_id)
            return self.async_create_entry(data=new_data)

        current_interval = self._config_entry.data.get(
            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
        )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SCAN_INTERVAL, default=current_interval
                    ): _interval_selector(),
                }
            ),
        )
