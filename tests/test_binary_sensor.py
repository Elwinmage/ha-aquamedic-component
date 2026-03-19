"""Tests for binary_sensor.py (fault indicators)."""

from __future__ import annotations

import pytest

from custom_components.aquamedic.binary_sensor import (
    AquaMedicFaultEntity,
    AquaMedicFaultDescription,
    FAULT_DESCRIPTIONS,
)
from custom_components.aquamedic.coordinator import AquaMedicDeviceData
from tests.conftest import MOCK_DID, MOCK_DEVICE_ONLINE, MOCK_DEVICE_OFFLINE, MOCK_LATEST


def _get_desc(key: str) -> AquaMedicFaultDescription:
    for d in FAULT_DESCRIPTIONS:
        if d.key == key:
            return d
    raise KeyError(key)


@pytest.fixture
def fault_overcurrent(coordinator):
    return AquaMedicFaultEntity(coordinator, MOCK_DID, _get_desc("fault_overcurrent"))


@pytest.fixture
def fault_overtemp(coordinator):
    return AquaMedicFaultEntity(coordinator, MOCK_DID, _get_desc("fault_overtemp"))


def test_seven_fault_sensors():
    assert len(FAULT_DESCRIPTIONS) == 7


def test_all_fault_keys():
    keys = {d.key for d in FAULT_DESCRIPTIONS}
    assert "fault_overcurrent"  in keys
    assert "fault_overvoltage"  in keys
    assert "fault_overtemp"     in keys
    assert "fault_undervoltage" in keys
    assert "fault_lockedrotor"  in keys
    assert "fault_no_liveload"  in keys
    assert "fault_uart"         in keys


def test_fault_is_off_normal(fault_overcurrent):
    # MOCK_ATTRS has all faults = 0
    assert fault_overcurrent.is_on is False


def test_fault_is_on_when_active(coordinator):
    attrs = {**MOCK_LATEST["attr"], "Fault_Overcurrent": 1}
    coordinator.data = {MOCK_DID: AquaMedicDeviceData(MOCK_DEVICE_ONLINE, {"attr": attrs})}
    sensor = AquaMedicFaultEntity(coordinator, MOCK_DID, _get_desc("fault_overcurrent"))
    assert sensor.is_on is True


def test_fault_is_none_when_missing(coordinator):
    attrs = {k: v for k, v in MOCK_LATEST["attr"].items() if k != "Fault_OverTemp"}
    coordinator.data = {MOCK_DID: AquaMedicDeviceData(MOCK_DEVICE_ONLINE, {"attr": attrs})}
    sensor = AquaMedicFaultEntity(coordinator, MOCK_DID, _get_desc("fault_overtemp"))
    assert sensor.is_on is None


def test_fault_available_online(fault_overcurrent):
    assert fault_overcurrent.available is True


def test_fault_unavailable_offline(coordinator):
    coordinator.data = {MOCK_DID: AquaMedicDeviceData(MOCK_DEVICE_OFFLINE, MOCK_LATEST)}
    sensor = AquaMedicFaultEntity(coordinator, MOCK_DID, _get_desc("fault_overcurrent"))
    assert sensor.available is False


def test_all_faults_have_diagnostic_category():
    from homeassistant.const import EntityCategory
    for d in FAULT_DESCRIPTIONS:
        assert d.entity_category == EntityCategory.DIAGNOSTIC
