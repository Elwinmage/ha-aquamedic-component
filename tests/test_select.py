"""Tests for select.py."""

from __future__ import annotations

import pytest

from custom_components.aquamedic.coordinator import AquaMedicDeviceData
from custom_components.aquamedic.select import (
    LINKAGE_OPTIONS,
    LINKAGE_RAW_MAP,
    MODE_OPTIONS,
    MODE_RAW_MAP,
    SELECT_DESCRIPTIONS,
    AquaMedicSelectDescription,
    AquaMedicSelectEntity,
)
from tests.conftest import (
    MOCK_DEVICE_OFFLINE,
    MOCK_DEVICE_ONLINE,
    MOCK_DID,
    MOCK_LATEST,
)


def _get_desc(key: str) -> AquaMedicSelectDescription:
    for d in SELECT_DESCRIPTIONS:
        if d.key == key:
            return d
    raise KeyError(key)


@pytest.fixture
def select_mode(coordinator):
    return AquaMedicSelectEntity(coordinator, MOCK_DID, _get_desc("mode"))


@pytest.fixture
def select_linkage(coordinator):
    return AquaMedicSelectEntity(coordinator, MOCK_DID, _get_desc("linkage"))


# ── Descriptions ──────────────────────────────────────────────────────────────


def test_mode_options():
    assert MODE_OPTIONS == ["classic_wave", "sine_wave", "random_wave", "constant_flow"]


def test_linkage_options():
    assert LINKAGE_OPTIONS == ["independent", "master", "slave"]


def test_raw_maps_complete():
    assert len(MODE_RAW_MAP) == 4
    assert len(LINKAGE_RAW_MAP) == 3


# ── current_option via integer index ──────────────────────────────────────────


def test_mode_current_option_by_index(select_mode):
    # MOCK_ATTRS has Mode=1 → sine_wave
    assert select_mode.current_option == "sine_wave"


def test_linkage_current_option_by_index(select_linkage):
    # MOCK_ATTRS has Linkage=0 → independent
    assert select_linkage.current_option == "independent"


# ── current_option via raw Chinese string ─────────────────────────────────────


def test_mode_current_option_raw_string(coordinator):
    attrs = {**MOCK_LATEST["attr"], "Mode": "随机造浪"}
    coordinator.data = {
        MOCK_DID: AquaMedicDeviceData(MOCK_DEVICE_ONLINE, {"attr": attrs})
    }
    sel = AquaMedicSelectEntity(coordinator, MOCK_DID, _get_desc("mode"))
    assert sel.current_option == "random_wave"


def test_linkage_current_option_raw_string(coordinator):
    attrs = {**MOCK_LATEST["attr"], "Linkage": "主机"}
    coordinator.data = {
        MOCK_DID: AquaMedicDeviceData(MOCK_DEVICE_ONLINE, {"attr": attrs})
    }
    sel = AquaMedicSelectEntity(coordinator, MOCK_DID, _get_desc("linkage"))
    assert sel.current_option == "master"


def test_mode_unknown_value_returns_none(coordinator):
    attrs = {**MOCK_LATEST["attr"], "Mode": 99}
    coordinator.data = {
        MOCK_DID: AquaMedicDeviceData(MOCK_DEVICE_ONLINE, {"attr": attrs})
    }
    sel = AquaMedicSelectEntity(coordinator, MOCK_DID, _get_desc("mode"))
    assert sel.current_option is None


def test_mode_none_value(coordinator):
    attrs = {k: v for k, v in MOCK_LATEST["attr"].items() if k != "Mode"}
    coordinator.data = {
        MOCK_DID: AquaMedicDeviceData(MOCK_DEVICE_ONLINE, {"attr": attrs})
    }
    sel = AquaMedicSelectEntity(coordinator, MOCK_DID, _get_desc("mode"))
    assert sel.current_option is None


# ── availability ──────────────────────────────────────────────────────────────


def test_select_available_online(select_mode):
    assert select_mode.available is True


def test_select_unavailable_offline(coordinator):
    coordinator.data = {MOCK_DID: AquaMedicDeviceData(MOCK_DEVICE_OFFLINE, MOCK_LATEST)}
    sel = AquaMedicSelectEntity(coordinator, MOCK_DID, _get_desc("mode"))
    assert sel.available is False


# ── control ───────────────────────────────────────────────────────────────────


async def test_select_mode_option(select_mode, mock_client):
    await select_mode.async_select_option("random_wave")
    mock_client.control_device.assert_called_once_with(MOCK_DID, {"Mode": 2})


async def test_select_linkage_option(select_linkage, mock_client):
    await select_linkage.async_select_option("slave")
    mock_client.control_device.assert_called_once_with(MOCK_DID, {"Linkage": 2})


async def test_select_invalid_option_no_call(select_mode, mock_client):
    await select_mode.async_select_option("invalid_option")
    mock_client.control_device.assert_not_called()
