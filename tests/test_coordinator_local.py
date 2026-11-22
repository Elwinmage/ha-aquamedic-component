"""Tests for the local network path of the coordinator."""

from __future__ import annotations

import json
import logging
import pathlib
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.aquamedic.client import (
    AquaMedicAuthError,
    AquaMedicConnectionError,
)
from custom_components.aquamedic.const import SMARTDRIFT_PRODUCT_KEY
from custom_components.aquamedic.coordinator import AquaMedicCoordinator
from custom_components.aquamedic.local import LocalError, LocalPump
from tests.conftest import MOCK_DEVICE_ONLINE, MOCK_DID

CAPTURE = next(
    pathlib.Path(__file__).parent.parent.glob(
        f"scripts/devices_datapoints/*_{SMARTDRIFT_PRODUCT_KEY}.json"
    )
)
HOST = "10.0.0.5"
LOCAL_VALUES = {"Flow": 33, "Frequency": 44, "TimerON": False}


class FakeLocalPump:
    """Stands for LocalPump: the protocol itself is tested in test_local.py."""

    can_write = staticmethod(LocalPump.can_write)

    def __init__(self, host: str, schema: Any) -> None:
        self.host = host
        self.schema = schema
        self.async_read = AsyncMock(return_value=dict(LOCAL_VALUES))
        self.async_write = AsyncMock(return_value=dict(LOCAL_VALUES))


def _info(did: str = MOCK_DID) -> dict[str, str]:
    return {
        "ip": HOST,
        "did": did,
        "mac": "aa",
        "firmware": "1",
        "product_key": SMARTDRIFT_PRODUCT_KEY,
    }


@pytest.fixture
def client(mock_client):
    mock_client.get_datapoints = AsyncMock(
        return_value=json.loads(CAPTURE.read_text(encoding="utf-8"))["datapoints"]
    )
    return mock_client


@pytest.fixture
def discovery():
    with patch(
        "custom_components.aquamedic.coordinator.async_discover",
        new=AsyncMock(return_value=_info()),
    ) as found:
        yield found


@pytest.fixture(autouse=True)
def fake_pump():
    with patch("custom_components.aquamedic.coordinator.LocalPump", FakeLocalPump):
        yield


def _coordinator(hass, client, hosts=(HOST,)) -> AquaMedicCoordinator:
    return AquaMedicCoordinator(hass, client, local_hosts=list(hosts))


async def test_without_local_hosts_nothing_is_discovered(hass, client, discovery):
    coord = AquaMedicCoordinator(hass, client)
    data = await coord._async_update_data()
    discovery.assert_not_awaited()
    assert data[MOCK_DID].local is False


async def test_a_local_pump_provides_its_values(hass, client, discovery):
    coord = _coordinator(hass, client)
    data = await coord._async_update_data()
    device = data[MOCK_DID]
    assert device.local is True
    assert device.is_online is True
    assert device.attrs["Flow"] == 33
    assert device.attrs["Frequency"] == 44
    # Cloud values the pump does not report are kept.
    assert device.attrs["SwitchON"] == 1


async def test_a_local_pump_is_online_even_when_the_cloud_says_otherwise(
    hass, client, discovery
):
    client.get_devices = AsyncMock(
        return_value=[{**MOCK_DEVICE_ONLINE, "is_online": False}]
    )
    coord = _coordinator(hass, client)
    data = await coord._async_update_data()
    assert data[MOCK_DID].is_online is True


async def test_the_pump_is_identified_once(hass, client, discovery):
    coord = _coordinator(hass, client)
    await coord._async_update_data()
    await coord._async_update_data()
    assert discovery.await_count == 1
    client.get_datapoints.assert_awaited_once_with(SMARTDRIFT_PRODUCT_KEY)


async def test_a_silent_address_is_tried_again_on_the_next_poll(
    hass, client, discovery
):
    discovery.return_value = None
    coord = _coordinator(hass, client)
    data = await coord._async_update_data()
    assert data[MOCK_DID].local is False
    discovery.return_value = _info()
    data = await coord._async_update_data()
    assert data[MOCK_DID].local is True


async def test_a_pump_of_another_account_is_ignored(hass, client, discovery, caplog):
    discovery.return_value = _info("someone-else")
    coord = _coordinator(hass, client)
    with caplog.at_level(logging.WARNING):
        data = await coord._async_update_data()
        await coord._async_update_data()
    assert data[MOCK_DID].local is False
    assert "not on this account" in caplog.text
    assert discovery.await_count == 1


@pytest.mark.parametrize(
    "error",
    [AquaMedicConnectionError("down"), AquaMedicAuthError("no"), LocalError("bad")],
)
async def test_no_datapoint_layout_means_no_local_access(
    hass, client, discovery, error
):
    client.get_datapoints = AsyncMock(side_effect=error)
    coord = _coordinator(hass, client)
    data = await coord._async_update_data()
    assert data[MOCK_DID].local is False
    assert data[MOCK_DID].attrs["Flow"] == 75


async def test_an_unreachable_pump_falls_back_to_the_cloud(
    hass, client, discovery, caplog
):
    coord = _coordinator(hass, client)
    await coord._async_update_data()
    coord._local[MOCK_DID].async_read.side_effect = LocalError("timeout")
    with caplog.at_level(logging.WARNING):
        data = await coord._async_update_data()
        await coord._async_update_data()
    assert data[MOCK_DID].local is False
    assert data[MOCK_DID].attrs["Flow"] == 75
    # Said once, not at every poll.
    assert caplog.text.count("Local read") == 1


async def test_local_access_comes_back(hass, client, discovery, caplog):
    coord = _coordinator(hass, client)
    await coord._async_update_data()
    pump = coord._local[MOCK_DID]
    pump.async_read.side_effect = LocalError("timeout")
    await coord._async_update_data()
    pump.async_read.side_effect = None
    with caplog.at_level(logging.INFO):
        data = await coord._async_update_data()
    assert data[MOCK_DID].local is True
    assert "is back" in caplog.text


async def test_reading_a_device_without_a_local_pump_changes_nothing(hass, client):
    coord = _coordinator(hass, client)
    data = MagicMock()
    await coord._async_read_local(MOCK_DID, data)
    data.attrs.update.assert_not_called()


async def test_the_local_pump_keeps_working_without_the_cloud(hass, client, discovery):
    coord = _coordinator(hass, client)
    await coord._async_update_data()
    client.get_devices = AsyncMock(side_effect=AquaMedicConnectionError("down"))
    client.get_device_data = AsyncMock(side_effect=AquaMedicConnectionError("down"))
    data = await coord._async_update_data()
    assert data[MOCK_DID].local is True
    assert data[MOCK_DID].attrs["Flow"] == 33


async def test_the_cloud_being_down_is_still_an_error_without_a_local_pump(
    hass, client, discovery
):
    coord = _coordinator(hass, client)
    await coord._async_update_data()
    coord._local.clear()
    client.get_devices = AsyncMock(side_effect=AquaMedicConnectionError("down"))
    with pytest.raises(UpdateFailed):
        await coord._async_update_data()


# ── Writes ────────────────────────────────────────────────────────────────────


async def _bound(hass, client, discovery) -> AquaMedicCoordinator:
    coord = _coordinator(hass, client)
    coord.data = await coord._async_update_data()
    coord.async_request_refresh = AsyncMock()
    return coord


async def test_a_write_goes_to_the_local_pump_first(hass, client, discovery):
    coord = await _bound(hass, client, discovery)
    await coord.async_control(MOCK_DID, {"Flow": 40, "Frequency": 44})
    coord._local[MOCK_DID].async_write.assert_awaited_once_with(
        {"Flow": 40, "Frequency": 44}
    )
    client.control_device.assert_not_awaited()


async def test_a_refused_local_write_goes_through_the_cloud(
    hass, client, discovery, caplog
):
    coord = await _bound(hass, client, discovery)
    coord._local[MOCK_DID].async_write.side_effect = LocalError("not applied")
    with caplog.at_level(logging.WARNING):
        await coord.async_control(MOCK_DID, {"FeedTime": 12})
    client.control_device.assert_awaited_once_with(MOCK_DID, {"FeedTime": 12})
    assert "through the cloud" in caplog.text


async def test_a_control_not_known_locally_goes_through_the_cloud(
    hass, client, discovery
):
    coord = await _bound(hass, client, discovery)
    await coord.async_control(MOCK_DID, {"AutoTime00": "00"})
    coord._local[MOCK_DID].async_write.assert_not_awaited()
    client.control_device.assert_awaited_once_with(MOCK_DID, {"AutoTime00": "00"})


async def test_a_device_without_a_local_pump_is_written_through_the_cloud(hass, client):
    coord = _coordinator(hass, client, hosts=())
    coord.data = await coord._async_update_data()
    coord.async_request_refresh = AsyncMock()
    await coord.async_control(MOCK_DID, {"FeedTime": 12})
    client.control_device.assert_awaited_once_with(MOCK_DID, {"FeedTime": 12})


async def test_only_the_smartdrift_is_controlled_locally(hass, client, discovery):
    client.get_devices = AsyncMock(
        return_value=[{**MOCK_DEVICE_ONLINE, "product_key": "other-product"}]
    )
    coord = _coordinator(hass, client)
    coord.data = await coord._async_update_data()
    coord.async_request_refresh = AsyncMock()
    # It is read locally...
    assert coord.data[MOCK_DID].local is True
    # ...but its controls still go through the cloud.
    await coord.async_control(MOCK_DID, {"Flow": 40})
    coord._local[MOCK_DID].async_write.assert_not_awaited()
    client.control_device.assert_awaited_once_with(MOCK_DID, {"Flow": 40})


async def test_two_pumps_of_one_product_share_the_datapoint_layout(
    hass, client, discovery
):
    other = {**MOCK_DEVICE_ONLINE, "did": "second-pump"}
    client.get_devices = AsyncMock(return_value=[MOCK_DEVICE_ONLINE, other])
    discovery.side_effect = [_info(), _info("second-pump")]
    coord = _coordinator(hass, client, hosts=(HOST, "10.0.0.6"))
    data = await coord._async_update_data()
    assert data[MOCK_DID].local is True
    assert data["second-pump"].local is True
    client.get_datapoints.assert_awaited_once()
