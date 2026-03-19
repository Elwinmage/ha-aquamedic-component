"""The Aqua Medic integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .client import AquaMedicAuthError, AquaMedicClient, AquaMedicConnectionError
from .const import (
    CONF_PASSWORD,
    CONF_REGION,
    CONF_SCAN_INTERVAL,
    CONF_SIM_HOST,
    CONF_USERNAME,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from .coordinator import AquaMedicCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[str] = ["switch", "select", "number", "binary_sensor", "button"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Aqua Medic from a config entry."""
    username = entry.data[CONF_USERNAME]
    password = entry.data[CONF_PASSWORD]
    region = entry.data[CONF_REGION]
    interval = entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    sim_host = entry.data.get(CONF_SIM_HOST)

    session = async_get_clientsession(hass)
    client = AquaMedicClient(session, username, password, region, sim_host=sim_host)

    try:
        await client.authenticate()
    except AquaMedicAuthError as exc:
        _LOGGER.error("Authentication failed for %s: %s", username, exc)
        from homeassistant.exceptions import ConfigEntryAuthFailed

        raise ConfigEntryAuthFailed from exc
    except AquaMedicConnectionError as exc:
        _LOGGER.error("Cannot connect to Gizwits API: %s", exc)
        raise ConfigEntryNotReady from exc

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
                "ONLINE" if dev.is_online else "OFFLINE",
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
