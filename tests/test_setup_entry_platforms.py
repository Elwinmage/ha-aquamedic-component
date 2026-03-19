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

    assert len(added) == 1


async def test_button_setup_entry_skips_unknown_product_key(hass, coordinator):
    from custom_components.aquamedic.button import async_setup_entry

    _unknown_device(coordinator)
    entry = _make_entry(hass, coordinator)
    added: list = []
    await async_setup_entry(hass, entry, lambda entities, **kw: added.extend(entities))

    assert len(added) == 1   # only the SmartDrift device


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

    # 3 number entities (flow, frequency, feed_time)
    assert len(added) == 3


async def test_number_setup_entry_skips_unknown_product_key(hass, coordinator):
    from custom_components.aquamedic.number import async_setup_entry

    _unknown_device(coordinator)
    entry = _make_entry(hass, coordinator)
    added: list = []
    await async_setup_entry(hass, entry, lambda entities, **kw: added.extend(entities))

    assert len(added) == 3   # only SmartDrift


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

    # 4 gizwits switches + 1 local switch = 5
    assert len(added) == 5


async def test_switch_setup_entry_skips_unknown_product_key(hass, coordinator):
    from custom_components.aquamedic.switch import async_setup_entry

    _unknown_device(coordinator)
    entry = _make_entry(hass, coordinator)
    added: list = []
    await async_setup_entry(hass, entry, lambda entities, **kw: added.extend(entities))

    assert len(added) == 5   # only SmartDrift


async def test_switch_setup_entry_empty_coordinator(hass, coordinator):
    from custom_components.aquamedic.switch import async_setup_entry

    coordinator.data = {}
    entry = _make_entry(hass, coordinator)
    added: list = []
    await async_setup_entry(hass, entry, lambda entities, **kw: added.extend(entities))
    assert len(added) == 0


# ── DC Runner device fixture ──────────────────────────────────────────────────

DC_RUNNER_DID = "dc_runner_test_did"

def _add_dc_runner(coordinator):
    """Add a DC Runner device to coordinator.data."""
    from custom_components.aquamedic.const import DC_RUNNER_PRODUCT_KEY
    from custom_components.aquamedic.coordinator import AquaMedicDeviceData
    dc_device = {
        **MOCK_DEVICE_ONLINE,
        "did": DC_RUNNER_DID,
        "product_key": DC_RUNNER_PRODUCT_KEY,
        "dev_alias": "DC Runner Test",
    }
    coordinator.data[DC_RUNNER_DID] = AquaMedicDeviceData(dc_device, MOCK_LATEST)


# ── switch: DC Runner branch ──────────────────────────────────────────────────

async def test_switch_setup_entry_dc_runner(hass, coordinator):
    """DC Runner branch creates 2 gizwits switches + 1 local switch = 3."""
    from custom_components.aquamedic.switch import async_setup_entry

    coordinator.data = {}
    _add_dc_runner(coordinator)
    entry = _make_entry(hass, coordinator)
    added: list = []
    await async_setup_entry(hass, entry, lambda entities, **kw: added.extend(entities))

    # DC Runner: SwitchON + FeedSwitch + control_0_10v = 3
    assert len(added) == 3


async def test_switch_setup_entry_dc_runner_and_smartdrift(hass, coordinator):
    """Both device types together yield 5 + 3 = 8 entities."""
    from custom_components.aquamedic.switch import async_setup_entry

    _add_dc_runner(coordinator)
    entry = _make_entry(hass, coordinator)
    added: list = []
    await async_setup_entry(hass, entry, lambda entities, **kw: added.extend(entities))

    # SmartDrift: 5, DC Runner: 3
    assert len(added) == 8


# ── number: DC Runner branch ──────────────────────────────────────────────────

async def test_number_setup_entry_dc_runner(hass, coordinator):
    """DC Runner branch creates 1 number entity (flow 30-100%)."""
    from custom_components.aquamedic.number import async_setup_entry

    coordinator.data = {}
    _add_dc_runner(coordinator)
    entry = _make_entry(hass, coordinator)
    added: list = []
    await async_setup_entry(hass, entry, lambda entities, **kw: added.extend(entities))

    assert len(added) == 1


async def test_number_setup_entry_dc_runner_min_value(hass, coordinator):
    """DC Runner flow entity has min=30."""
    from custom_components.aquamedic.number import async_setup_entry

    coordinator.data = {}
    _add_dc_runner(coordinator)
    entry = _make_entry(hass, coordinator)
    added: list = []
    await async_setup_entry(hass, entry, lambda entities, **kw: added.extend(entities))

    assert added[0].native_min_value == 30


async def test_number_setup_entry_dc_runner_and_smartdrift(hass, coordinator):
    """Both device types together: 3 SmartDrift + 1 DC Runner = 4."""
    from custom_components.aquamedic.number import async_setup_entry

    _add_dc_runner(coordinator)
    entry = _make_entry(hass, coordinator)
    added: list = []
    await async_setup_entry(hass, entry, lambda entities, **kw: added.extend(entities))

    assert len(added) == 4
