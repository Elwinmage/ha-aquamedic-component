"""Tests for async_setup_entry in each platform module.

These tests cover the platform registration functions (lines uncovered by
the entity-level unit tests which bypass the setup machinery).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.config_entries import ConfigEntry

from custom_components.aquamedic.const import DOMAIN, SMARTDRIFT_PRODUCT_KEY
from custom_components.aquamedic.coordinator import AquaMedicDeviceData
from tests.conftest import MOCK_DID, MOCK_DEVICE_ONLINE, MOCK_LATEST


# ── Shared helpers ────────────────────────────────────────────────────────────


def _make_entry(hass, coordinator) -> MagicMock:
    """Build a fake ConfigEntry whose entry_id is in hass.data[DOMAIN]."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test-entry-id"
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    return entry


def _unknown_device(coordinator):
    """Add a device with an unknown product_key to coordinator.data."""
    unknown = AquaMedicDeviceData(
        {**MOCK_DEVICE_ONLINE, "product_key": "unknown-pk"},
        MOCK_LATEST,
    )
    coordinator.data["unknown-did"] = unknown


# ── binary_sensor.async_setup_entry ──────────────────────────────────────────


async def test_binary_sensor_setup_entry_creates_entities(hass, coordinator):
    from custom_components.aquamedic.binary_sensor import async_setup_entry

    entry = _make_entry(hass, coordinator)
    added: list = []
    await async_setup_entry(hass, entry, lambda entities, **kw: added.extend(entities))

    # 7 fault sensors per device
    assert len(added) == 7


async def test_binary_sensor_setup_entry_skips_unknown_product_key(hass, coordinator):
    from custom_components.aquamedic.binary_sensor import async_setup_entry

    _unknown_device(coordinator)
    entry = _make_entry(hass, coordinator)
    added: list = []
    await async_setup_entry(hass, entry, lambda entities, **kw: added.extend(entities))

    # Only the SmartDrift device → still 7
    assert len(added) == 7


async def test_binary_sensor_setup_entry_empty_coordinator(hass, coordinator):
    from custom_components.aquamedic.binary_sensor import async_setup_entry

    coordinator.data = {}
    entry = _make_entry(hass, coordinator)
    added: list = []
    await async_setup_entry(hass, entry, lambda entities, **kw: added.extend(entities))
    assert len(added) == 0


# ── button.async_setup_entry ──────────────────────────────────────────────────


async def test_button_setup_entry_creates_one_per_device(hass, coordinator):
    from custom_components.aquamedic.button import async_setup_entry

    entry = _make_entry(hass, coordinator)
    added: list = []
    await async_setup_entry(hass, entry, lambda entities, **kw: added.extend(entities))

    # 1 refresh button + 3 SmartDrift maintenance tasks
    assert len(added) == 4


async def test_button_setup_entry_skips_unknown_product_key(hass, coordinator):
    from custom_components.aquamedic.button import async_setup_entry

    _unknown_device(coordinator)
    entry = _make_entry(hass, coordinator)
    added: list = []
    await async_setup_entry(hass, entry, lambda entities, **kw: added.extend(entities))

    assert len(added) == 4  # only the SmartDrift device


async def test_button_setup_entry_empty_coordinator(hass, coordinator):
    from custom_components.aquamedic.button import async_setup_entry

    coordinator.data = {}
    entry = _make_entry(hass, coordinator)
    added: list = []
    await async_setup_entry(hass, entry, lambda entities, **kw: added.extend(entities))
    assert len(added) == 0


# ── number.async_setup_entry ──────────────────────────────────────────────────


async def test_number_setup_entry_creates_entities(hass, coordinator):
    from custom_components.aquamedic.number import async_setup_entry

    entry = _make_entry(hass, coordinator)
    added: list = []
    await async_setup_entry(hass, entry, lambda entities, **kw: added.extend(entities))

    # 3 number entities (flow, frequency, feed_time) + 3 maintenance intervals
    assert len(added) == 6


async def test_number_setup_entry_skips_unknown_product_key(hass, coordinator):
    from custom_components.aquamedic.number import async_setup_entry

    _unknown_device(coordinator)
    entry = _make_entry(hass, coordinator)
    added: list = []
    await async_setup_entry(hass, entry, lambda entities, **kw: added.extend(entities))

    assert len(added) == 6  # only SmartDrift


async def test_number_setup_entry_empty_coordinator(hass, coordinator):
    from custom_components.aquamedic.number import async_setup_entry

    coordinator.data = {}
    entry = _make_entry(hass, coordinator)
    added: list = []
    await async_setup_entry(hass, entry, lambda entities, **kw: added.extend(entities))
    assert len(added) == 0


# ── select.async_setup_entry ──────────────────────────────────────────────────


async def test_select_setup_entry_creates_entities(hass, coordinator):
    from custom_components.aquamedic.select import async_setup_entry

    entry = _make_entry(hass, coordinator)
    added: list = []
    await async_setup_entry(hass, entry, lambda entities, **kw: added.extend(entities))

    # 2 selects (mode, linkage)
    assert len(added) == 2


async def test_select_setup_entry_skips_unknown_product_key(hass, coordinator):
    from custom_components.aquamedic.select import async_setup_entry

    _unknown_device(coordinator)
    entry = _make_entry(hass, coordinator)
    added: list = []
    await async_setup_entry(hass, entry, lambda entities, **kw: added.extend(entities))

    assert len(added) == 2


async def test_select_setup_entry_empty_coordinator(hass, coordinator):
    from custom_components.aquamedic.select import async_setup_entry

    coordinator.data = {}
    entry = _make_entry(hass, coordinator)
    added: list = []
    await async_setup_entry(hass, entry, lambda entities, **kw: added.extend(entities))
    assert len(added) == 0


# ── switch.async_setup_entry ──────────────────────────────────────────────────


async def test_switch_setup_entry_creates_entities(hass, coordinator):
    from custom_components.aquamedic.switch import async_setup_entry

    entry = _make_entry(hass, coordinator)
    added: list = []
    await async_setup_entry(hass, entry, lambda entities, **kw: added.extend(entities))

    # 4 gizwits switches + 1 local switch + 3 maintenance notify switches = 8
    assert len(added) == 8


async def test_switch_setup_entry_skips_unknown_product_key(hass, coordinator):
    from custom_components.aquamedic.switch import async_setup_entry

    _unknown_device(coordinator)
    entry = _make_entry(hass, coordinator)
    added: list = []
    await async_setup_entry(hass, entry, lambda entities, **kw: added.extend(entities))

    assert len(added) == 8  # only SmartDrift


async def test_switch_setup_entry_empty_coordinator(hass, coordinator):
    from custom_components.aquamedic.switch import async_setup_entry

    coordinator.data = {}
    entry = _make_entry(hass, coordinator)
    added: list = []
    await async_setup_entry(hass, entry, lambda entities, **kw: added.extend(entities))
    assert len(added) == 0


# ── DC Runner (return pump) & DC Skimmer fixtures ─────────────────────────────

DC_RUNNER_DID = "dc_runner_test_did"
DC_SKIMMER_DID = "dc_skimmer_test_did"


def _add_dc_runner(coordinator):
    """Add a DC Runner return pump to coordinator.data."""
    from custom_components.aquamedic.const import DC_RUNNER_PRODUCT_KEY
    from custom_components.aquamedic.coordinator import AquaMedicDeviceData

    dc_device = {
        **MOCK_DEVICE_ONLINE,
        "did": DC_RUNNER_DID,
        "product_key": DC_RUNNER_PRODUCT_KEY,
        "dev_alias": "DC Runner Test",
    }
    coordinator.data[DC_RUNNER_DID] = AquaMedicDeviceData(dc_device, MOCK_LATEST)


def _add_dc_skimmer(coordinator):
    """Add a DC Skimmer to coordinator.data."""
    from custom_components.aquamedic.const import DC_SKIMMER_PRODUCT_KEY
    from custom_components.aquamedic.coordinator import AquaMedicDeviceData

    dc_device = {
        **MOCK_DEVICE_ONLINE,
        "did": DC_SKIMMER_DID,
        "product_key": DC_SKIMMER_PRODUCT_KEY,
        "dev_alias": "DC Skimmer Test",
    }
    coordinator.data[DC_SKIMMER_DID] = AquaMedicDeviceData(dc_device, MOCK_LATEST)


# ── switch ────────────────────────────────────────────────────────────────────


async def test_switch_setup_entry_dc_runner(hass, coordinator):
    """DC Runner return pump: power + feed_switch + control_0_10v = 3."""
    from custom_components.aquamedic.switch import async_setup_entry

    coordinator.data = {}
    _add_dc_runner(coordinator)
    entry = _make_entry(hass, coordinator)
    added: list = []
    await async_setup_entry(hass, entry, lambda entities, **kw: added.extend(entities))

    assert len(added) == 3


async def test_switch_setup_entry_dc_skimmer(hass, coordinator):
    """DC Skimmer: power + feed_switch + timer_on + control_0_10v = 4."""
    from custom_components.aquamedic.switch import async_setup_entry

    coordinator.data = {}
    _add_dc_skimmer(coordinator)
    entry = _make_entry(hass, coordinator)
    added: list = []
    await async_setup_entry(hass, entry, lambda entities, **kw: added.extend(entities))

    assert len(added) == 4


async def test_switch_setup_entry_all_device_types(hass, coordinator):
    """SmartDrift 8 + DC Runner 3 + DC Skimmer 4 = 15.

    Both DC devices default to the "unknown" pump role, so they carry no
    maintenance switch yet.
    """
    from custom_components.aquamedic.switch import async_setup_entry

    _add_dc_runner(coordinator)
    _add_dc_skimmer(coordinator)
    entry = _make_entry(hass, coordinator)
    added: list = []
    await async_setup_entry(hass, entry, lambda entities, **kw: added.extend(entities))

    assert len(added) == 15


# ── number ────────────────────────────────────────────────────────────────────


async def test_number_setup_entry_dc_runner(hass, coordinator):
    """DC Runner return pump: single flow control = 1."""
    from custom_components.aquamedic.number import async_setup_entry

    coordinator.data = {}
    _add_dc_runner(coordinator)
    entry = _make_entry(hass, coordinator)
    added: list = []
    await async_setup_entry(hass, entry, lambda entities, **kw: added.extend(entities))

    assert len(added) == 1
    assert added[0].native_min_value == 30


async def test_number_setup_entry_dc_skimmer(hass, coordinator):
    """DC Skimmer: Motor_Speed + FeedTime + AutoGears + AutoFeedTime = 4."""
    from custom_components.aquamedic.number import async_setup_entry

    coordinator.data = {}
    _add_dc_skimmer(coordinator)
    entry = _make_entry(hass, coordinator)
    added: list = []
    await async_setup_entry(hass, entry, lambda entities, **kw: added.extend(entities))

    assert len(added) == 4
    # motor_speed is first and enforces min=30
    assert added[0].entity_description.key == "motor_speed"
    assert added[0].native_min_value == 30


async def test_number_setup_entry_all_device_types(hass, coordinator):
    """SmartDrift 6 + DC Runner 1 + DC Skimmer 4 = 11."""
    from custom_components.aquamedic.number import async_setup_entry

    _add_dc_runner(coordinator)
    _add_dc_skimmer(coordinator)
    entry = _make_entry(hass, coordinator)
    added: list = []
    await async_setup_entry(hass, entry, lambda entities, **kw: added.extend(entities))

    assert len(added) == 11


# ── select / binary_sensor / button (DC Skimmer only) ─────────────────────────


async def test_select_setup_entry_dc_runner_role_only(hass, coordinator):
    """DC Runner exposes no Gizwits select, only the pump role one."""
    from custom_components.aquamedic.select import async_setup_entry

    coordinator.data = {}
    _add_dc_runner(coordinator)
    entry = _make_entry(hass, coordinator)
    added: list = []
    await async_setup_entry(hass, entry, lambda entities, **kw: added.extend(entities))

    assert len(added) == 1
    assert added[0]._attr_translation_key == "pump_role"


async def test_select_setup_entry_dc_skimmer(hass, coordinator):
    """DC Skimmer creates the auto_mode select plus the pump role one."""
    from custom_components.aquamedic.select import async_setup_entry

    coordinator.data = {}
    _add_dc_skimmer(coordinator)
    entry = _make_entry(hass, coordinator)
    added: list = []
    await async_setup_entry(hass, entry, lambda entities, **kw: added.extend(entities))

    assert len(added) == 2
    assert added[0].entity_description.key == "auto_mode"
    assert added[1]._attr_translation_key == "pump_role"


async def test_binary_sensor_setup_entry_dc_runner_none(hass, coordinator):
    """DC Runner return pump exposes no fault sensors."""
    from custom_components.aquamedic.binary_sensor import async_setup_entry

    coordinator.data = {}
    _add_dc_runner(coordinator)
    entry = _make_entry(hass, coordinator)
    added: list = []
    await async_setup_entry(hass, entry, lambda entities, **kw: added.extend(entities))

    assert len(added) == 0


async def test_binary_sensor_setup_entry_dc_skimmer(hass, coordinator):
    """DC Skimmer exposes the same 7 fault sensors as SmartDrift."""
    from custom_components.aquamedic.binary_sensor import async_setup_entry

    coordinator.data = {}
    _add_dc_skimmer(coordinator)
    entry = _make_entry(hass, coordinator)
    added: list = []
    await async_setup_entry(hass, entry, lambda entities, **kw: added.extend(entities))

    assert len(added) == 7


async def test_button_setup_entry_dc_runner_none(hass, coordinator):
    """DC Runner gets no refresh button, and no task until its role is set."""
    from custom_components.aquamedic.button import async_setup_entry

    coordinator.data = {}
    _add_dc_runner(coordinator)
    entry = _make_entry(hass, coordinator)
    added: list = []
    await async_setup_entry(hass, entry, lambda entities, **kw: added.extend(entities))

    assert len(added) == 0


async def test_button_setup_entry_dc_skimmer(hass, coordinator):
    """DC Skimmer gets a refresh button."""
    from custom_components.aquamedic.button import async_setup_entry

    coordinator.data = {}
    _add_dc_skimmer(coordinator)
    entry = _make_entry(hass, coordinator)
    added: list = []
    await async_setup_entry(hass, entry, lambda entities, **kw: added.extend(entities))

    assert len(added) == 1


# ── Maintenance entities driven by the declared pump role ────────────────────


async def _store_for(hass, coordinator, did: str, role: str):
    """Attach a loaded store declaring `role` for `did`, as setup_entry does."""
    from custom_components.aquamedic.maintenance import MaintenanceStore

    store = MaintenanceStore(hass, f"role-{role}")
    await store.async_load()
    if role != "unknown":
        await store.async_set_role(did, role)
    coordinator.maintenance = store
    return store


@pytest.mark.parametrize(
    ("platform", "role", "expected"),
    [
        # DC Runner series, declared as a return pump: 3 tasks.
        ("button", "return", 1 + 3),
        ("number", "return", 4 + 3),
        ("switch", "return", 4 + 3),
        # …declared as a skimmer: 5 tasks.
        ("button", "skimmer", 1 + 5),
        ("number", "skimmer", 4 + 5),
        ("switch", "skimmer", 4 + 5),
        # …still undeclared: no maintenance entity at all.
        ("button", "unknown", 1),
        ("number", "unknown", 4),
        ("switch", "unknown", 4),
    ],
)
async def test_maintenance_entities_follow_the_pump_role(
    hass, coordinator, platform, role, expected
):
    import importlib

    module = importlib.import_module(f"custom_components.aquamedic.{platform}")

    coordinator.data = {}
    _add_dc_skimmer(coordinator)
    await _store_for(hass, coordinator, DC_SKIMMER_DID, role)

    entry = _make_entry(hass, coordinator)
    added: list = []
    await module.async_setup_entry(
        hass, entry, lambda entities, **kw: added.extend(entities)
    )

    assert len(added) == expected


async def test_smartdrift_tasks_do_not_depend_on_any_role(hass, coordinator):
    """A SmartDrift is unambiguous: its 3 tasks exist without any declaration."""
    from custom_components.aquamedic.button import async_setup_entry

    await _store_for(hass, coordinator, MOCK_DID, "unknown")
    entry = _make_entry(hass, coordinator)
    added: list = []
    await async_setup_entry(hass, entry, lambda entities, **kw: added.extend(entities))

    roles = [
        getattr(e, "_attr_translation_key", None)
        for e in added
        if getattr(e, "_attr_translation_key", "").startswith("maint_")
    ]
    assert roles == [
        "maint_drift_rotor_clean",
        "maint_drift_descale",
        "maint_drift_impeller_replace",
    ]
