"""Tests for coordinator.py."""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.aquamedic.client import AquaMedicConnectionError
from custom_components.aquamedic.const import SMARTDRIFT_PRODUCT_KEY
from custom_components.aquamedic.coordinator import (
    OPTIMISTIC_HOLD_SECONDS,
    AquaMedicCoordinator,
    AquaMedicDeviceData,
    _same_value,
)
from tests.conftest import (
    MOCK_ATTRS,
    MOCK_DEVICE_OFFLINE,
    MOCK_DEVICE_ONLINE,
    MOCK_DID,
    MOCK_LATEST,
)

# ── AquaMedicDeviceData ───────────────────────────────────────────────────────


def test_device_data_online(device_data_online):
    d = device_data_online
    assert d.did == MOCK_DID
    assert d.product_key == SMARTDRIFT_PRODUCT_KEY
    assert d.name == "SmartDrift Test"
    assert d.is_online is True
    assert d.attrs == MOCK_ATTRS
    assert d.updated_at == 1700000000


def test_device_data_offline(device_data_offline):
    d = device_data_offline
    assert d.is_online is False
    assert d.attrs == {}


def test_device_data_unknown_online():
    """Missing online hints must not default to offline."""
    device = {k: v for k, v in MOCK_DEVICE_ONLINE.items() if k != "is_online"}
    d = AquaMedicDeviceData(device, {})
    assert d.is_online is None


def test_device_data_latest_overrides_offline():
    """Gateway query can supply is_online even when device list says offline."""
    device = {**MOCK_DEVICE_OFFLINE}
    latest = {"attr": MOCK_ATTRS, "is_online": True, "updated_at": 1700000000}
    d = AquaMedicDeviceData(device, latest)
    assert d.is_online is True


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
    assert d.get("Flow") == 75
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
    mock_client.get_device_data = AsyncMock(
        side_effect=AquaMedicConnectionError("fail")
    )
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


# ── Optimistic writes ─────────────────────────────────────────────────────────


def test_device_data_copies_its_attributes():
    """An optimistic write must not leak into the response it was read from."""
    latest = {"attr": {"SwitchON": 1}}
    data = AquaMedicDeviceData(MOCK_DEVICE_ONLINE, latest)
    data.attrs["SwitchON"] = 0
    assert latest["attr"]["SwitchON"] == 1


@pytest.mark.parametrize(
    ("left", "right", "expected"),
    [
        (1, 1, True),
        (1, True, True),
        (0, False, True),
        (True, "1", True),
        (1, False, False),
        (True, "on", False),  # not a number: cannot be the same boolean
        (True, None, False),
        ("08000C1E013C", "08000c1e013c", True),
        ("abc", "abd", False),
        (60, 60.0, True),
        (60, 61, False),
        (1, "经典造浪", False),
    ],
)
def test_same_value(left, right, expected):
    assert _same_value(left, right) is expected


async def test_control_shows_the_new_value_before_the_cloud_answers(coordinator):
    seen: list = []

    async def _control(did, attrs):
        # Called after the optimistic update: the entity already shows it.
        seen.append(coordinator.data[MOCK_DID].get("Flow"))

    coordinator._client.control_device = AsyncMock(side_effect=_control)

    await coordinator.async_control(MOCK_DID, {"Flow": 40})

    assert seen == [40]
    assert coordinator.data[MOCK_DID].get("Flow") == 40
    coordinator._client.control_device.assert_awaited_once_with(MOCK_DID, {"Flow": 40})
    assert coordinator.async_update_listeners.call_count == 1
    coordinator.async_request_refresh.assert_awaited_once()


async def test_control_restores_the_previous_values_when_the_cloud_refuses(
    coordinator,
):
    coordinator._client.control_device = AsyncMock(
        side_effect=AquaMedicConnectionError("boom")
    )
    before = coordinator.data[MOCK_DID].get("Flow")

    with pytest.raises(AquaMedicConnectionError):
        # AutoTime00 is not reported by this pump: it must disappear again.
        await coordinator.async_control(MOCK_DID, {"Flow": 40, "AutoTime00": "00"})

    assert coordinator.data[MOCK_DID].get("Flow") == before
    assert "AutoTime00" not in coordinator.data[MOCK_DID].attrs
    assert coordinator._pending.get(MOCK_DID) == {}
    # Shown, then taken back.
    assert coordinator.async_update_listeners.call_count == 2
    coordinator.async_request_refresh.assert_not_awaited()


async def test_control_of_an_unknown_device_is_only_forwarded(coordinator):
    await coordinator.async_control("other-did", {"Flow": 40})
    coordinator._client.control_device.assert_awaited_once_with(
        "other-did", {"Flow": 40}
    )
    coordinator.async_update_listeners.assert_not_called()

    coordinator._client.control_device = AsyncMock(
        side_effect=AquaMedicConnectionError("boom")
    )
    with pytest.raises(AquaMedicConnectionError):
        await coordinator.async_control("other-did", {"Flow": 40})
    coordinator.async_update_listeners.assert_not_called()


async def test_control_without_data_is_only_forwarded(coordinator):
    coordinator.data = None
    await coordinator.async_control(MOCK_DID, {"Flow": 40})
    coordinator._client.control_device.assert_awaited_once()


async def test_pending_value_survives_a_lagging_poll(hass, mock_client):
    """The refresh right after a write often still reads the old value."""
    coord = AquaMedicCoordinator(hass, mock_client, scan_interval=30)
    coord.data = await coord._async_update_data()
    assert coord.data[MOCK_DID].get("Flow") == 75

    with patch.object(coord, "async_request_refresh", AsyncMock()):
        await coord.async_control(MOCK_DID, {"Flow": 40})

    # The cloud still says 75: the written value is kept.
    lagging = await coord._async_update_data()
    assert lagging[MOCK_DID].get("Flow") == 40
    assert MOCK_DID in coord._pending


async def test_pending_value_is_dropped_once_the_cloud_confirms(hass, mock_client):
    coord = AquaMedicCoordinator(hass, mock_client, scan_interval=30)
    coord.data = await coord._async_update_data()
    with patch.object(coord, "async_request_refresh", AsyncMock()):
        await coord.async_control(MOCK_DID, {"Flow": 40})

    mock_client.get_device_data = AsyncMock(
        return_value={"attr": {**MOCK_ATTRS, "Flow": 40}}
    )
    confirmed = await coord._async_update_data()
    assert confirmed[MOCK_DID].get("Flow") == 40
    assert MOCK_DID not in coord._pending


async def test_pending_value_expires_and_the_cloud_wins_again(hass, mock_client):
    """A command the pump ignored must not stay on screen forever."""
    coord = AquaMedicCoordinator(hass, mock_client, scan_interval=30)
    coord.data = await coord._async_update_data()
    with patch.object(coord, "async_request_refresh", AsyncMock()):
        await coord.async_control(MOCK_DID, {"Flow": 40, "Frequency": 10})

    later = time.monotonic() + OPTIMISTIC_HOLD_SECONDS + 1
    with patch(
        "custom_components.aquamedic.coordinator.time.monotonic", return_value=later
    ):
        expired = await coord._async_update_data()
    assert expired[MOCK_DID].get("Flow") == 75
    assert expired[MOCK_DID].get("Frequency") == 50
    assert MOCK_DID not in coord._pending
