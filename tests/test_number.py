"""Tests for number.py."""

from __future__ import annotations

import pytest

from custom_components.aquamedic.number import (
    AquaMedicNumberEntity,
    AquaMedicNumberDescription,
    NUMBER_DESCRIPTIONS,
)
from custom_components.aquamedic.coordinator import AquaMedicDeviceData
from tests.conftest import MOCK_DID, MOCK_DEVICE_ONLINE, MOCK_DEVICE_OFFLINE, MOCK_LATEST


def _get_desc(key: str) -> AquaMedicNumberDescription:
    for d in NUMBER_DESCRIPTIONS:
        if d.key == key:
            return d
    raise KeyError(key)


@pytest.fixture
def num_flow(coordinator):
    return AquaMedicNumberEntity(coordinator, MOCK_DID, _get_desc("flow"))


@pytest.fixture
def num_freq(coordinator):
    return AquaMedicNumberEntity(coordinator, MOCK_DID, _get_desc("frequency"))


@pytest.fixture
def num_feed(coordinator):
    return AquaMedicNumberEntity(coordinator, MOCK_DID, _get_desc("feed_time"))


# ── Descriptions ──────────────────────────────────────────────────────────────

def test_flow_description():
    d = _get_desc("flow")
    assert d.native_min_value == 0
    assert d.native_max_value == 100
    assert d.gated_by_0_10v is True


def test_frequency_description():
    d = _get_desc("frequency")
    assert d.gated_by_0_10v is False


def test_feed_time_description():
    d = _get_desc("feed_time")
    assert d.native_min_value == 1
    assert d.native_max_value == 60


# ── Values ────────────────────────────────────────────────────────────────────

def test_flow_native_value(num_flow):
    assert num_flow.native_value == 75.0


def test_frequency_native_value(num_freq):
    assert num_freq.native_value == 50.0


def test_feed_time_native_value(num_feed):
    assert num_feed.native_value == 10.0


def test_native_value_none_when_missing(coordinator):
    attrs = {k: v for k, v in MOCK_LATEST["attr"].items() if k != "Flow"}
    coordinator.data = {MOCK_DID: AquaMedicDeviceData(MOCK_DEVICE_ONLINE, {"attr": attrs})}
    num = AquaMedicNumberEntity(coordinator, MOCK_DID, _get_desc("flow"))
    assert num.native_value is None


# ── Availability ──────────────────────────────────────────────────────────────

def test_flow_available_online(num_flow, coordinator):
    assert num_flow.available is True


def test_flow_unavailable_offline(coordinator):
    coordinator.data = {MOCK_DID: AquaMedicDeviceData(MOCK_DEVICE_OFFLINE, MOCK_LATEST)}
    num = AquaMedicNumberEntity(coordinator, MOCK_DID, _get_desc("flow"))
    assert num.available is False


def test_flow_unavailable_when_0_10v_on(coordinator, num_flow):
    coordinator.set_control_0_10v(MOCK_DID, True)
    assert num_flow.available is False


def test_flow_available_when_0_10v_off(coordinator, num_flow):
    coordinator.set_control_0_10v(MOCK_DID, False)
    assert num_flow.available is True


def test_frequency_available_even_with_0_10v(coordinator, num_freq):
    coordinator.set_control_0_10v(MOCK_DID, True)
    assert num_freq.available is True


# ── Control ───────────────────────────────────────────────────────────────────

async def test_set_flow(num_flow, mock_client):
    await num_flow.async_set_native_value(80.0)
    mock_client.control_device.assert_called_once_with(MOCK_DID, {"Flow": 80})


async def test_set_frequency(num_freq, mock_client):
    await num_freq.async_set_native_value(60.0)
    mock_client.control_device.assert_called_once_with(MOCK_DID, {"Frequency": 60})


async def test_set_feed_time(num_feed, mock_client):
    await num_feed.async_set_native_value(15.0)
    mock_client.control_device.assert_called_once_with(MOCK_DID, {"FeedTime": 15})
