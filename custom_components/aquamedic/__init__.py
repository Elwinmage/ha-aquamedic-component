"""The Aqua Medic integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

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
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from .coordinator import AquaMedicCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[str] = ["switch", "select", "number", "binary_sensor", "button"]


def _persist_client_tokens(
    hass: HomeAssistant, entry: ConfigEntry, client: AquaMedicClient
) -> None:
    """Store AEP tokens in the config entry after successful auth (HA encrypts data)."""
    if not isinstance(client.refresh_token, str) or not client.refresh_token:
        return
    new_data = dict(entry.data)
    new_data[CONF_REFRESH_TOKEN] = client.refresh_token
    if isinstance(client.access_token, str) and client.access_token:
        new_data[CONF_ACCESS_TOKEN] = client.access_token
    if client.token_created_at is not None:
        new_data[CONF_TOKEN_CREATED_AT] = client.token_created_at
    if client.token_expired_at is not None:
        new_data[CONF_TOKEN_EXPIRED_AT] = client.token_expired_at
    if isinstance(client.api_mode, str):
        new_data[CONF_API_MODE] = client.api_mode
    if isinstance(client.device_list_api, str):
        new_data[CONF_DEVICE_LIST_API] = client.device_list_api
    hass.config_entries.async_update_entry(entry, data=new_data)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Aqua Medic from a config entry."""
    username = entry.data[CONF_USERNAME]
    password = entry.data[CONF_PASSWORD]
    region = entry.data[CONF_REGION]
    interval = entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    sim_host = entry.data.get(CONF_SIM_HOST)

    session = async_get_clientsession(hass)
    ha_lang = hass.config.language or "en"

    # Restore persisted AEP session tokens to skip a full re-login when possible.
    client = AquaMedicClient(
        session,
        username,
        password,
        region,
        sim_host=sim_host,
        lang=ha_lang,
        access_token=entry.data.get(CONF_ACCESS_TOKEN),
        refresh_token=entry.data.get(CONF_REFRESH_TOKEN),
        token_created_at=entry.data.get(CONF_TOKEN_CREATED_AT),
        token_expired_at=entry.data.get(CONF_TOKEN_EXPIRED_AT),
        device_list_api=entry.data.get(CONF_DEVICE_LIST_API),
    )

    try:
        await client.authenticate()
    except AquaMedicAuthError as exc:
        _LOGGER.error("Authentication failed for %s: %s", username, exc)
        from homeassistant.exceptions import ConfigEntryAuthFailed

        raise ConfigEntryAuthFailed from exc
    except AquaMedicConnectionError as exc:
        _LOGGER.error("Cannot connect to Gizwits API: %s", exc)
        raise ConfigEntryNotReady from exc

    # Persist refreshed tokens back into the config entry.
    _persist_client_tokens(hass, entry, client)

    _LOGGER.info(
        "[Aqua Medic] Using %s API stack (region=%s, device_list=%s).",
        client.api_mode,
        region,
        client.device_list_api or "auto",
    )

    coordinator = AquaMedicCoordinator(hass, client, scan_interval=interval)
    await coordinator.async_config_entry_first_refresh()

    if coordinator.data:
        _LOGGER.info(
            "[Aqua Medic] %d device(s) for '%s' | interval=%ds",
            len(coordinator.data),
            username,
            interval,
        )
        for did, dev in coordinator.data.items():
            _LOGGER.info(
                "  • %-30s | did=%-24s | pk=%-32s | %s",
                dev.name,
                did,
                dev.product_key,
                (
                    "ONLINE"
                    if dev.is_online is True
                    else ("OFFLINE" if dev.is_online is False else "UNKNOWN")
                ),
            )

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
