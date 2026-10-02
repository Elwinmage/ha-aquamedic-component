"""Services of the Aqua Medic integration."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from .client import AquaMedicAuthError, AquaMedicConnectionError
from .compat import vol
from .const import DOMAIN
from .coordinator import AquaMedicCoordinator
from .schedule import ScheduleError, build_control_payload, layout_for

_LOGGER = logging.getLogger(__name__)

SERVICE_SET_SCHEDULE = "set_schedule"

ATTR_ENTITY_ID = "entity_id"
ATTR_DEVICE_ID = "device_id"
ATTR_SLOTS = "slots"

# Suffix of the schedule sensor unique_id ("<did>_schedule", see sensor.py).
_SCHEDULE_UNIQUE_SUFFIX = "_schedule"

_SLOT_SCHEMA = vol.Schema(
    {
        vol.Required("start"): vol.Any(int, cv.string),
        vol.Required("end"): vol.Any(int, cv.string),
        vol.Optional("mode"): cv.string,
        vol.Optional("value"): vol.Coerce(int),
        vol.Optional("frequency"): vol.Coerce(int),
        vol.Optional("tide"): cv.boolean,
    },
    # The schedule attribute carries a "slot" index: accept it back untouched
    # so a program read from the sensor can be sent as is.
    extra=vol.REMOVE_EXTRA,
)

SET_SCHEDULE_SCHEMA = vol.Schema(
    vol.All(
        {
            vol.Optional(ATTR_ENTITY_ID): cv.entity_ids,
            vol.Optional(ATTR_DEVICE_ID): vol.All(cv.ensure_list, [cv.string]),
            vol.Required(ATTR_SLOTS): vol.All(cv.ensure_list, [_SLOT_SCHEMA]),
        },
        cv.has_at_least_one_key(ATTR_ENTITY_ID, ATTR_DEVICE_ID),
    )
)


def _coordinators(hass: HomeAssistant) -> dict[str, AquaMedicCoordinator]:
    return hass.data.get(DOMAIN, {})


def _find_device(
    hass: HomeAssistant, did: str, entry_ids: set[str] | None = None
) -> tuple[AquaMedicCoordinator, str]:
    """Return the loaded coordinator holding the Gizwits device *did*."""
    for entry_id, coordinator in _coordinators(hass).items():
        if entry_ids is not None and entry_id not in entry_ids:
            continue
        if coordinator.data and did in coordinator.data:
            return coordinator, did
    raise ServiceValidationError(
        f"Aqua Medic device {did} is not loaded (integration unloaded or device gone)"
    )


def _did_of(device: dr.DeviceEntry) -> str | None:
    """Return the Gizwits device id carried by a device registry entry."""
    for ident in device.identifiers:
        if ident[0] == DOMAIN:
            return ident[1]
    return None


def _resolve_targets(
    hass: HomeAssistant, call: ServiceCall
) -> list[tuple[AquaMedicCoordinator, str]]:
    """Map the entity/device ids of a call to (coordinator, did) pairs."""
    targets: dict[str, tuple[AquaMedicCoordinator, str]] = {}

    ent_reg = er.async_get(hass)
    for entity_id in call.data.get(ATTR_ENTITY_ID, []):
        entry = ent_reg.async_get(entity_id)
        if (
            entry is None
            or entry.platform != DOMAIN
            or not entry.unique_id.endswith(_SCHEDULE_UNIQUE_SUFFIX)
        ):
            raise ServiceValidationError(
                f"{entity_id} is not an Aqua Medic schedule sensor"
            )
        did = entry.unique_id[: -len(_SCHEDULE_UNIQUE_SUFFIX)]
        entry_ids = {entry.config_entry_id} if entry.config_entry_id else None
        targets[did] = _find_device(hass, did, entry_ids)

    dev_reg = dr.async_get(hass)
    for device_id in call.data.get(ATTR_DEVICE_ID, []):
        device = dev_reg.async_get(device_id)
        # isinstance, not a None check: the registry may also hand back
        # entries that carry no identifiers of their own.
        did = _did_of(device) if isinstance(device, dr.DeviceEntry) else None
        if not isinstance(device, dr.DeviceEntry) or did is None:
            raise ServiceValidationError(f"{device_id} is not an Aqua Medic device")
        targets[did] = _find_device(hass, did, set(device.config_entries))

    return list(targets.values())


async def _async_set_schedule(hass: HomeAssistant, call: ServiceCall) -> None:
    """Replace the whole time-slot program of one or several pumps."""
    slots: list[dict[str, Any]] = call.data[ATTR_SLOTS]

    # Validate every target before sending anything: a call mixing a valid
    # and an invalid pump must not leave them half programmed.
    jobs: list[tuple[AquaMedicCoordinator, str, dict[str, str]]] = []
    for coordinator, did in _resolve_targets(hass, call):
        dev = coordinator.data[did]
        layout = layout_for(dev.product_key)
        if layout is None:
            raise ServiceValidationError(f"{dev.name} has no time-slot scheduler")
        try:
            payload = build_control_payload(slots, layout, dev.attrs)
        except ScheduleError as exc:
            raise ServiceValidationError(f"{dev.name}: {exc}") from exc
        jobs.append((coordinator, did, payload))

    for coordinator, did, payload in jobs:
        if not payload:
            _LOGGER.debug("Schedule of %s already up to date", did)
            continue
        try:
            await coordinator.async_control(did, payload)
        except (AquaMedicAuthError, AquaMedicConnectionError) as exc:
            raise HomeAssistantError(
                f"Could not write the schedule of {did}: {exc}"
            ) from exc
        _LOGGER.debug("Schedule written to %s (%d slot(s) changed)", did, len(payload))


@callback
def async_register_services(hass: HomeAssistant) -> None:
    """Register the integration services (idempotent)."""
    if hass.services.has_service(DOMAIN, SERVICE_SET_SCHEDULE):
        return

    async def _handle_set_schedule(call: ServiceCall) -> None:
        await _async_set_schedule(hass, call)

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_SCHEDULE,
        _handle_set_schedule,
        schema=SET_SCHEDULE_SCHEMA,
    )


@callback
def async_unregister_services(hass: HomeAssistant) -> None:
    """Remove the integration services once no config entry is left."""
    if hass.services.has_service(DOMAIN, SERVICE_SET_SCHEDULE):
        hass.services.async_remove(DOMAIN, SERVICE_SET_SCHEDULE)
