"""Config flow for the Aqua Medic integration.

Steps:
  user     → username + password + region (pre-selected from HA language)
              + scan_interval
  sim_host → (only when region == "sim") simulator host URL

Options flow:
  init  → scan_interval
"""

from __future__ import annotations

import logging
import pathlib
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
    CONF_ACCESS_TOKEN,
    CONF_API_MODE,
    CONF_DEVICE_LIST_API,
    CONF_PASSWORD,
    CONF_REFRESH_TOKEN,
    CONF_REGION,
    CONF_SCAN_INTERVAL,
    CONF_SIM_HOST,
    CONF_TOKEN_CREATED_AT,
    CONF_TOKEN_EXPIRED_AT,
    CONF_USERNAME,
    DEFAULT_REGION,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    GIZWITS_REGIONS,
    LANGUAGE_TO_REGION,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
    SIM_DEFAULT_HOST,
)

_LOGGER = logging.getLogger(__name__)


# Local file that enables the simulator region in the config flow.
# Create it to enable, delete it to disable — git-ignored.
_SIM_FLAG = pathlib.Path(__file__).parent / ".simulator_enabled"


def _simulator_enabled() -> bool:
    """Return True if the local .simulator_enabled flag file exists."""
    return _SIM_FLAG.exists()


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
        # Three-state online: True/False/None (unknown for newly detected devices).
        raw_online = d.get("is_online")
        if raw_online is True:
            online = "ONLINE"
        elif raw_online is False:
            online = "OFFLINE"
        else:
            online = "UNKNOWN"
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


def _user_schema(default_region: str) -> vol.Schema:
    """Return the vol.Schema for the user step."""
    # Include "sim" only when the local flag file is present
    regions = {
        k: v for k, v in GIZWITS_REGIONS.items() if k != "sim" or _simulator_enabled()
    }
    region_options = [SelectOptionDict(value=k, label=v) for k, v in regions.items()]
    return vol.Schema(
        {
            vol.Required(CONF_USERNAME): TextSelector(
                TextSelectorConfig(type=TextSelectorType.EMAIL, autocomplete="email")
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


class AquaMedicConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the Aqua Medic config flow.

    Step 1 (user):    username, password, region, scan_interval
    Step 2 (sim_host): shown only when region == "sim"; collects the
                       simulator base URL (default: http://localhost:8080).
    """

    VERSION = 1

    def __init__(self) -> None:
        self._user_input: dict[str, Any] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        errors: dict[str, str] = {}

        ha_lang = self.hass.config.language or "en"
        default_region = _default_region(ha_lang)

        if user_input is not None:
            self._user_input = {
                CONF_USERNAME: user_input[CONF_USERNAME].strip(),
                CONF_PASSWORD: user_input[CONF_PASSWORD],
                CONF_REGION: user_input[CONF_REGION],
                CONF_SCAN_INTERVAL: int(
                    user_input.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
                ),
            }
            # Simulator region → ask for host before connecting
            if self._user_input[CONF_REGION] == "sim":
                return await self.async_step_sim_host()

            return await self._async_try_connect(errors)

        return self.async_show_form(
            step_id="user",
            data_schema=_user_schema(default_region),
            errors=errors,
        )

    async def async_step_sim_host(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Step 2 — collect simulator host URL (sim region only).

        Only reachable when the local .simulator_enabled flag file
        exists alongside this module.
        """
        if not _simulator_enabled():
            return self.async_abort(reason="simulator_disabled")
        errors: dict[str, str] = {}

        if user_input is not None:
            self._user_input[CONF_SIM_HOST] = user_input[CONF_SIM_HOST].rstrip("/")
            return await self._async_try_connect(errors)

        schema = vol.Schema(
            {
                vol.Required(CONF_SIM_HOST, default=SIM_DEFAULT_HOST): TextSelector(
                    TextSelectorConfig(type=TextSelectorType.URL)
                ),
            }
        )
        return self.async_show_form(
            step_id="sim_host",
            data_schema=schema,
            errors=errors,
        )

    async def _async_try_connect(
        self, errors: dict[str, str]
    ) -> config_entries.ConfigFlowResult:
        """Attempt authentication and, on success, create the config entry."""
        inp = self._user_input
        username = inp[CONF_USERNAME]
        password = inp[CONF_PASSWORD]
        region = inp[CONF_REGION]
        interval = inp[CONF_SCAN_INTERVAL]
        sim_host = inp.get(CONF_SIM_HOST)

        session = async_get_clientsession(self.hass)
        ha_lang = self.hass.config.language or "en"
        client = AquaMedicClient(
            session,
            username,
            password,
            region,
            sim_host=sim_host,
            lang=ha_lang,
        )

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

        if errors:
            # Return to the right step on error
            if region == "sim":
                schema = vol.Schema(
                    {
                        vol.Required(
                            CONF_SIM_HOST, default=sim_host or SIM_DEFAULT_HOST
                        ): TextSelector(TextSelectorConfig(type=TextSelectorType.URL)),
                    }
                )
                return self.async_show_form(
                    step_id="sim_host",
                    data_schema=schema,
                    errors=errors,
                )
            ha_lang = self.hass.config.language or "en"
            return self.async_show_form(
                step_id="user",
                data_schema=_user_schema(_default_region(ha_lang)),
                errors=errors,
            )

        unique_id = (
            f"{region}_{sim_host}_{username}"
            if region == "sim"
            else f"{region}_{username}"
        )
        await self.async_set_unique_id(unique_id)
        self._abort_if_unique_id_configured()

        entry_data: dict[str, Any] = {
            CONF_USERNAME: username,
            CONF_PASSWORD: password,
            CONF_REGION: region,
            CONF_SCAN_INTERVAL: interval,
        }
        if region == "sim" and sim_host:
            entry_data[CONF_SIM_HOST] = sim_host

        # Persist AEP tokens so the next HA startup can restore the session
        # without a full re-login (avoids unnecessary network round-trips).
        if isinstance(client.refresh_token, str) and client.refresh_token:
            entry_data[CONF_REFRESH_TOKEN] = client.refresh_token
            if isinstance(client.access_token, str) and client.access_token:
                entry_data[CONF_ACCESS_TOKEN] = client.access_token
            if client.token_created_at is not None:
                entry_data[CONF_TOKEN_CREATED_AT] = client.token_created_at
            if client.token_expired_at is not None:
                entry_data[CONF_TOKEN_EXPIRED_AT] = client.token_expired_at
        if isinstance(client.api_mode, str):
            entry_data[CONF_API_MODE] = client.api_mode
        if isinstance(client.device_list_api, str):
            entry_data[CONF_DEVICE_LIST_API] = client.device_list_api

        title = f"{username} (simulator)" if region == "sim" else username
        return self.async_create_entry(title=title, data=entry_data)

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
