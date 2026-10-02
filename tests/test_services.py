"""Tests for services.py — aquamedic.set_schedule."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
import voluptuous as vol
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.aquamedic.client import AquaMedicConnectionError
from custom_components.aquamedic.const import (
    DC_RUNNER_PRODUCT_KEY,
    DC_RUNNER_SERIES_PRODUCT_KEY,
    DOMAIN,
)
from custom_components.aquamedic.coordinator import AquaMedicDeviceData
from custom_components.aquamedic.schedule import SLOT_COUNT, slot_attr
from custom_components.aquamedic.services import (
    SERVICE_SET_SCHEDULE,
    async_register_services,
    async_unregister_services,
)
from tests.conftest import MOCK_ATTRS, MOCK_DEVICE_ONLINE, MOCK_DID

RUNNER_DID = "runner-did"
LEGACY_DID = "legacy-did"
SLOTS = [{"start": "08:00", "end": "12:30", "mode": "auto", "value": 60}]
DRIFT_SLOTS = [{"start": "08:00", "end": "12:30", "mode": "sine_wave", "value": 60}]


def _blank(slot_len: int) -> dict[str, str]:
    return {slot_attr(i): "00" * slot_len for i in range(SLOT_COUNT)}


@pytest.fixture
def loaded(hass, coordinator):
    """One loaded entry: a SmartDrift, a DC Runner series pump, a legacy one."""
    entry = MockConfigEntry(domain=DOMAIN, data={})
    entry.add_to_hass(hass)
    coordinator.data = {
        MOCK_DID: AquaMedicDeviceData(
            MOCK_DEVICE_ONLINE, {"attr": {**MOCK_ATTRS, **_blank(8)}}
        ),
        RUNNER_DID: AquaMedicDeviceData(
            {
                **MOCK_DEVICE_ONLINE,
                "did": RUNNER_DID,
                "dev_alias": "Skimmer",
                "product_key": DC_RUNNER_SERIES_PRODUCT_KEY,
            },
            {"attr": _blank(6)},
        ),
        LEGACY_DID: AquaMedicDeviceData(
            {
                **MOCK_DEVICE_ONLINE,
                "did": LEGACY_DID,
                "dev_alias": "Legacy",
                "product_key": DC_RUNNER_PRODUCT_KEY,
            },
            {},
        ),
    }
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    async_register_services(hass)

    ent_reg = er.async_get(hass)
    dev_reg = dr.async_get(hass)
    ids: dict[str, str] = {}
    for did in (MOCK_DID, RUNNER_DID, LEGACY_DID):
        device = dev_reg.async_get_or_create(
            config_entry_id=entry.entry_id, identifiers={(DOMAIN, did)}
        )
        ids[f"device:{did}"] = device.id
        ids[f"entity:{did}"] = ent_reg.async_get_or_create(
            "sensor",
            DOMAIN,
            f"{did}_schedule",
            config_entry=entry,
            device_id=device.id,
        ).entity_id
    # An entity of ours that is not a schedule sensor, and a foreign device.
    ids["entity:power"] = ent_reg.async_get_or_create(
        "switch", DOMAIN, f"{MOCK_DID}_power", config_entry=entry
    ).entity_id
    ids["device:foreign"] = dev_reg.async_get_or_create(
        config_entry_id=entry.entry_id, identifiers={("other", "x")}
    ).id
    return ids


async def _call(hass, **data):
    await hass.services.async_call(DOMAIN, SERVICE_SET_SCHEDULE, data, blocking=True)


# ── Registration ──────────────────────────────────────────────────────────────


async def test_register_is_idempotent_and_unregister_removes(hass):
    async_register_services(hass)
    async_register_services(hass)
    assert hass.services.has_service(DOMAIN, SERVICE_SET_SCHEDULE)
    async_unregister_services(hass)
    assert not hass.services.has_service(DOMAIN, SERVICE_SET_SCHEDULE)
    # Removing twice is harmless.
    async_unregister_services(hass)


# ── Happy paths ───────────────────────────────────────────────────────────────


async def test_set_schedule_by_entity(hass, coordinator, loaded):
    await _call(hass, entity_id=loaded[f"entity:{RUNNER_DID}"], slots=SLOTS)

    coordinator._client.control_device.assert_awaited_once_with(
        RUNNER_DID, {"AutoTime00": "08000c1e013c"}
    )
    coordinator.async_request_refresh.assert_awaited_once()


async def test_set_schedule_by_device(hass, coordinator, loaded):
    await _call(hass, device_id=loaded[f"device:{MOCK_DID}"], slots=DRIFT_SLOTS)

    coordinator._client.control_device.assert_awaited_once_with(
        MOCK_DID, {"AutoTime00": "08000c1e023c0000"}
    )


async def test_same_pump_named_twice_is_written_once(hass, coordinator, loaded):
    await _call(
        hass,
        entity_id=loaded[f"entity:{RUNNER_DID}"],
        device_id=loaded[f"device:{RUNNER_DID}"],
        slots=SLOTS,
    )
    assert coordinator._client.control_device.await_count == 1


async def test_unchanged_program_sends_nothing(hass, coordinator, loaded):
    await _call(hass, entity_id=loaded[f"entity:{RUNNER_DID}"], slots=[])
    coordinator._client.control_device.assert_not_awaited()
    coordinator.async_request_refresh.assert_not_awaited()


async def test_slot_index_from_the_sensor_attribute_is_accepted(
    hass, coordinator, loaded
):
    """A program read back from the sensor carries "slot": it must round-trip."""
    await _call(
        hass,
        entity_id=loaded[f"entity:{RUNNER_DID}"],
        slots=[{"slot": 7, "start": 480, "end": 750, "mode": "auto", "value": 60}],
    )
    coordinator._client.control_device.assert_awaited_once_with(
        RUNNER_DID, {"AutoTime00": "08000c1e013c"}
    )


# ── Validation ────────────────────────────────────────────────────────────────


async def test_target_is_required(hass, loaded):
    with pytest.raises(vol.Invalid):
        await _call(hass, slots=SLOTS)


@pytest.mark.parametrize("key", ["entity:power", "entity:missing"])
async def test_rejects_entities_that_are_not_schedule_sensors(hass, loaded, key):
    entity_id = loaded.get(key, "sensor.does_not_exist")
    with pytest.raises(ServiceValidationError, match="not an Aqua Medic schedule"):
        await _call(hass, entity_id=entity_id, slots=SLOTS)


@pytest.mark.parametrize("key", ["device:foreign", "device:missing"])
async def test_rejects_devices_that_are_not_ours(hass, loaded, key):
    device_id = loaded.get(key, "no-such-device")
    with pytest.raises(ServiceValidationError, match="not an Aqua Medic device"):
        await _call(hass, device_id=device_id, slots=SLOTS)


async def test_rejects_a_pump_without_scheduler(hass, coordinator, loaded):
    with pytest.raises(ServiceValidationError, match="no time-slot scheduler"):
        await _call(hass, device_id=loaded[f"device:{LEGACY_DID}"], slots=SLOTS)


async def test_rejects_an_invalid_program_before_sending_anything(
    hass, coordinator, loaded
):
    """sine_wave is valid for the SmartDrift but not for the DC Runner."""
    with pytest.raises(ServiceValidationError, match="unknown mode"):
        await _call(
            hass,
            device_id=[loaded[f"device:{MOCK_DID}"], loaded[f"device:{RUNNER_DID}"]],
            slots=DRIFT_SLOTS,
        )
    coordinator._client.control_device.assert_not_awaited()


async def test_rejects_a_device_whose_entry_is_not_loaded(hass, coordinator, loaded):
    del coordinator.data[RUNNER_DID]
    with pytest.raises(ServiceValidationError, match="not loaded"):
        await _call(hass, entity_id=loaded[f"entity:{RUNNER_DID}"], slots=SLOTS)


async def test_ignores_coordinators_of_other_entries(hass, coordinator, loaded):
    """A did is only looked up in the config entry that owns the target."""
    other = AsyncMock()
    other.data = {RUNNER_DID: coordinator.data[RUNNER_DID]}
    hass.data[DOMAIN] = {"other-entry": other, **hass.data[DOMAIN]}

    await _call(hass, entity_id=loaded[f"entity:{RUNNER_DID}"], slots=SLOTS)

    other._client.control_device.assert_not_awaited()
    coordinator._client.control_device.assert_awaited_once()


async def test_entity_without_config_entry_searches_every_coordinator(
    hass, coordinator, loaded
):
    orphan = er.async_get(hass).async_get_or_create(
        "sensor", DOMAIN, f"{RUNNER_DID}x_schedule"
    )
    coordinator.data[f"{RUNNER_DID}x"] = coordinator.data[RUNNER_DID]
    await _call(hass, entity_id=orphan.entity_id, slots=SLOTS)
    coordinator._client.control_device.assert_awaited_once()


# ── Cloud errors ──────────────────────────────────────────────────────────────


async def test_cloud_error_is_reported(hass, coordinator, loaded):
    coordinator._client.control_device.side_effect = AquaMedicConnectionError("boom")
    with pytest.raises(HomeAssistantError, match="Could not write the schedule"):
        await _call(hass, entity_id=loaded[f"entity:{RUNNER_DID}"], slots=SLOTS)
    coordinator.async_request_refresh.assert_not_awaited()
