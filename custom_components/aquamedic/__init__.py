"""The Aqua Medic integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.typing import ConfigType

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
from .maintenance import MaintenanceStore
from .services import async_register_services, async_unregister_services

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[str] = [
    "switch",
    "select",
    "number",
    "binary_sensor",
    "button",
    "sensor",
]

# The integration is set up from the UI only; this tells hassfest so, now
# that async_setup() exists to register the services.
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register the integration services."""
    async_register_services(hass)
    return True


def _device_dids(device: dr.DeviceEntry) -> set[str]:
    """Gizwits device ids carried by a device registry entry."""
    return {ident[1] for ident in device.identifiers if ident[0] == DOMAIN}


@callback
def _async_remove_stale_devices(
    hass: HomeAssistant, entry: ConfigEntry, known_dids: set[str]
) -> int:
    """Detach from this entry the devices the account no longer reports.

    Nothing else ever removes a device: a pump unbound from the account, or
    one whose Gizwits ``did`` changed (the cloud issues a new one when a pump
    is reset and bound again, and so did the local simulator on every start),
    stayed in the registry next to its replacement. Each occurrence added one
    more copy of every pump, with entity ids suffixed ``_2``, ``_3``...

    Callers must only pass a list that really came from the cloud: an empty
    one is not acted upon, so a transient empty answer cannot wipe the
    registry (and with it every entity customisation).
    """
    if not known_dids:
        return 0
    dev_reg = dr.async_get(hass)
    removed = 0
    for device in dr.async_entries_for_config_entry(dev_reg, entry.entry_id):
        dids = _device_dids(device)
        if not dids or dids & known_dids:
            continue
        _LOGGER.info(
            "[Aqua Medic] Removing stale device '%s' (did=%s): no longer "
            "reported by the account",
            device.name,
            ", ".join(sorted(dids)),
        )
        dev_reg.async_update_device(device.id, remove_config_entry_id=entry.entry_id)
        removed += 1
    return removed


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

    coordinator = AquaMedicCoordinator(
        hass, client, scan_interval=interval, entry_id=entry.entry_id
    )

    # Maintenance state must be loaded before the platforms are forwarded:
    # the task list of a DC Runner depends on the pump role stored here.
    maintenance = MaintenanceStore(hass, entry.entry_id)
    await maintenance.async_load()
    coordinator.maintenance = maintenance

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

    # Drop the registry devices this account no longer owns before the
    # platforms run, so their entities go with them.
    _async_remove_stale_devices(hass, entry, set(coordinator.data or {}))

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    # Also done in async_setup(); kept here so the services exist whichever
    # way the entry was set up.
    async_register_services(hass)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
        if not hass.data[DOMAIN]:
            async_unregister_services(hass)
    return unload_ok


async def async_remove_config_entry_device(
    hass: HomeAssistant, entry: ConfigEntry, device: dr.DeviceEntry
) -> bool:
    """Allow deleting a device from the UI once the account no longer has it."""
    coordinator: AquaMedicCoordinator | None = hass.data.get(DOMAIN, {}).get(
        entry.entry_id
    )
    known = set(coordinator.data or {}) if coordinator else set()
    return not (_device_dids(device) & known)
