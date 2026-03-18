"""The Aqua Medic integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .client import AquaMedicAuthError, AquaMedicClient, AquaMedicConnectionError
from .const import CONF_PASSWORD, CONF_REGION, CONF_USERNAME, DOMAIN
from .coordinator import AquaMedicCoordinator

_LOGGER = logging.getLogger(__name__)

# Platforms to load — extend this list as entity files are added
PLATFORMS: list[str] = []


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Aqua Medic from a config entry.

    1. Build the API client from stored credentials.
    2. Re-authenticate (token is not persisted).
    3. Create the coordinator and do a first refresh.
    4. Store everything in hass.data for platform use.
    """
    username = entry.data[CONF_USERNAME]
    password = entry.data[CONF_PASSWORD]
    region = entry.data[CONF_REGION]

    session = async_get_clientsession(hass)
    client = AquaMedicClient(session, username, password, region)

    try:
        await client.authenticate()
    except AquaMedicAuthError as exc:
        _LOGGER.error("Authentication failed for %s: %s", username, exc)
        # Permanent error — user must fix credentials → raise ConfigEntryAuthFailed
        # instead of NotReady so HA shows the re-auth notification.
        from homeassistant.exceptions import ConfigEntryAuthFailed

        raise ConfigEntryAuthFailed from exc
    except AquaMedicConnectionError as exc:
        _LOGGER.error("Cannot connect to Gizwits API: %s", exc)
        raise ConfigEntryNotReady from exc

    coordinator = AquaMedicCoordinator(hass, client)

    # First data fetch — raises ConfigEntryNotReady if it fails
    await coordinator.async_config_entry_first_refresh()

    # Log every discovered device at startup
    if coordinator.data:
        _LOGGER.info(
            "[Aqua Medic] %d device(s) loaded for account '%s':",
            len(coordinator.data),
            username,
        )
        for did, dev in coordinator.data.items():
            _LOGGER.info(
                "  • %-30s | did=%-24s | pk=%-32s | %s",
                dev.name,
                did,
                dev.product_key,
                "ONLINE" if dev.is_online else "OFFLINE",
            )
            if dev.attrs:
                for attr, val in dev.attrs.items():
                    _LOGGER.debug("      %s = %s", attr, val)

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    # Forward to platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
