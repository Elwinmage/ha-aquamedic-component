"""Tests for coordinator.py."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.aquamedic.client import AquaMedicConnectionError
from custom_components.aquamedic.coordinator import (
    AquaMedicCoordinator,
    AquaMedicDeviceData,
)
from custom_components.aquamedic.const import SMARTDRIFT_PRODUCT_KEY
from homeassistant.helpers.update_coordinator import UpdateFailed

from tests.conftest import (
    MOCK_ATTRS,
    MOCK_DID,
    MOCK_DEVICE_ONLINE,
    MOCK_DEVICE_OFFLINE,
    MOCK_LATEST,
)


# ── AquaMedicDeviceData ───────────────────────────────────────────────────────

def test_device_data_online(device_data_online):
    d = device_data_online
    assert d.did         == MOCK_DID
    assert d.product_key == SMARTDRIFT_PRODUCT_KEY
    assert d.name        == "SmartDrift Test"
    assert d.is_online   is True
    assert d.attrs       == MOCK_ATTRS
    assert d.updated_at  == 1700000000


def test_device_data_offline(device_data_offline):
    d = device_data_offline
    assert d.is_online is False
    assert d.attrs     == {}


def test_device_data_fallback_name():
    """Falls back to product_name when dev_alias is absent."""
    device = {**MOCK_DEVICE_ONLINE, "dev_alias": None}
    d = AquaMedicDeviceData(device, MOCK_LATEST)
    assert d.name == "Current_Pump"


def test_device_data_default_name():
    """Falls back to 'AquaMedic' when both alias and product_name are absent."""
    device = {**MOCK_DEVICE_ONLINE, "dev_alias": None, "product_name": None}
    d = AquaMedicDeviceData(device, MOCK_LATEST)
    assert d.name == "AquaMedic"


def test_device_data_get():
    d = AquaMedicDeviceData(MOCK_DEVICE_ONLINE, MOCK_LATEST)
    assert d.get("Flow")       == 75
    assert d.get("missing", 0) == 0


# ── AquaMedicCoordinator ──────────────────────────────────────────────────────

def test_coordinator_creation(hass, mock_client):
    coord = AquaMedicCoordinator(hass, mock_client, scan_interval=60)
    from datetime import timedelta
    assert coord.update_interval == timedelta(seconds=60)


async def test_coordinator_update_success(hass, mock_client):
    coord = AquaMedicCoordinator(hass, mock_client, scan_interval=30)
    data = await coord._async_update_data()
    assert MOCK_DID in data
    assert data[MOCK_DID].is_online is True
    assert data[MOCK_DID].attrs["Flow"] == 75


async def test_coordinator_skips_device_without_did(hass, mock_client):
    mock_client.get_devices = AsyncMock(return_value=[{"product_key": "abc"}])
    coord = AquaMedicCoordinator(hass, mock_client)
    data = await coord._async_update_data()
    assert len(data) == 0


async def test_coordinator_device_fetch_failure(hass, mock_client):
    """Device fetch failure is logged but does not crash the coordinator."""
    mock_client.get_device_data = AsyncMock(side_effect=AquaMedicConnectionError("fail"))
    coord = AquaMedicCoordinator(hass, mock_client)
    data = await coord._async_update_data()
    assert MOCK_DID in data
    assert data[MOCK_DID].attrs == {}


async def test_coordinator_raises_update_failed_on_bindings_error(hass, mock_client):
    mock_client.get_devices = AsyncMock(side_effect=AquaMedicConnectionError("fail"))
    coord = AquaMedicCoordinator(hass, mock_client)
    with pytest.raises(UpdateFailed):
        await coord._async_update_data()


# ── 0-10V local state ─────────────────────────────────────────────────────────

def test_control_0_10v_default(coordinator):
    assert coordinator.get_control_0_10v(MOCK_DID) is False


def test_control_0_10v_set_true(coordinator):
    coordinator.set_control_0_10v(MOCK_DID, True)
    assert coordinator.get_control_0_10v(MOCK_DID) is True


def test_control_0_10v_toggle(coordinator):
    coordinator.set_control_0_10v(MOCK_DID, True)
    coordinator.set_control_0_10v(MOCK_DID, False)
    assert coordinator.get_control_0_10v(MOCK_DID) is False


def test_control_0_10v_unknown_device(coordinator):
    assert coordinator.get_control_0_10v("unknown-did") is False
