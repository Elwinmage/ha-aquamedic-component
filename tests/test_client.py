"""Tests for client.py."""

from __future__ import annotations

import json
import time
from unittest.mock import AsyncMock, MagicMock

import aiohttp
import pytest

from custom_components.aquamedic.client import (
    API_MODE_AEP,
    API_MODE_LEGACY,
    AquaMedicAuthError,
    AquaMedicClient,
    AquaMedicConnectionError,
)
from custom_components.aquamedic.const import (
    GIZWITS_APP_KEY,
    GIZWITS_LEGACY_APP_ID,
    DEVICE_LIST_BINDINGS,
    DEVICE_LIST_SMART_HOME,
)

from tests.conftest import MOCK_DID, MOCK_PASSWORD, MOCK_TOKEN, MOCK_USERNAME

MOCK_AEP_LOGIN = {
    "code": 200,
    "data": {
        "uid": "uid123",
        "jwtAuthenticationDto": {"token": MOCK_TOKEN},
        "refreshToken": "refresh-abc",
        "createdAt": 1700000000,
        "expiredAt": 1700086400,
    },
}


def _make_response(status: int, body: dict):
    """Build a fake aiohttp response as an async context manager."""
    resp = MagicMock()
    resp.status = status
    resp.text = AsyncMock(return_value=json.dumps(body))
    resp.json = AsyncMock(return_value=body)
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=resp)
    cm.__aexit__ = AsyncMock(return_value=False)
    return cm


@pytest.fixture
def session():
    return MagicMock(spec=aiohttp.ClientSession)


@pytest.fixture
def client(session):
    return AquaMedicClient(session, MOCK_USERNAME, MOCK_PASSWORD, region="eu")


@pytest.fixture
def legacy_client(client):
    """Client forced into legacy mode (Open API)."""
    client._api_mode = API_MODE_LEGACY
    client._token = MOCK_TOKEN
    return client


# ── Headers ───────────────────────────────────────────────────────────────────

def test_aep_headers(client):
    client._jwt = MOCK_TOKEN
    h = client._aep_headers()
    assert h["X-Gizwits-Application-Id"] == GIZWITS_APP_KEY
    assert h["Authorization"] == MOCK_TOKEN
    assert h["Version"] == "1.0"


def test_legacy_headers_no_token(client):
    h = client._legacy_headers(authenticated=False)
    assert h["X-Gizwits-Application-Id"] == GIZWITS_LEGACY_APP_ID
    assert "X-Gizwits-User-token" not in h


def test_legacy_headers_with_token(legacy_client):
    h = legacy_client._legacy_headers(authenticated=True)
    assert h["X-Gizwits-User-token"] == MOCK_TOKEN


def test_gateway_headers(client):
    client._jwt = MOCK_TOKEN
    h = client._gateway_headers()
    assert h["X-Gizwits-Api-Key"]
    assert h["Authorization"] == MOCK_TOKEN


# ── Provision (legacy) ────────────────────────────────────────────────────────

async def test_provision_success(legacy_client, session):
    session.request = MagicMock(return_value=_make_response(200, {}))
    await legacy_client.provision()


async def test_provision_failure_nonfatal(legacy_client, session):
    session.request = MagicMock(return_value=_make_response(400, {"error": "bad"}))
    await legacy_client.provision()


# ── Authenticate ──────────────────────────────────────────────────────────────

async def test_authenticate_aep_success(client, session):
    session.request = MagicMock(return_value=_make_response(200, MOCK_AEP_LOGIN))
    await client.authenticate()
    assert client.api_mode == API_MODE_AEP
    assert client._jwt == MOCK_TOKEN
    assert client.refresh_token == "refresh-abc"


async def test_authenticate_fallback_legacy(client, session):
    """AEP login fails → legacy login succeeds."""

    def _side_effect(method, url, **kwargs):
        if "login/pwd" in url:
            return _make_response(200, {"code": 1000033, "message": "bad"})
        if "/app/login" in url:
            return _make_response(200, {"token": MOCK_TOKEN, "uid": "uid123"})
        return _make_response(200, {})

    session.request = MagicMock(side_effect=_side_effect)
    await client.authenticate()
    assert client.api_mode == API_MODE_LEGACY
    assert client._token == MOCK_TOKEN


async def test_authenticate_aep_bad_credentials(client, session):
    session.request = MagicMock(
        return_value=_make_response(200, {"code": 1000033, "message": "wrong"})
    )

    def _legacy_fail(method, url, **kwargs):
        if "/app/login" in url:
            return _make_response(200, {"error_code": 9004})
        return _make_response(200, {})

    session.request = MagicMock(side_effect=_legacy_fail)
    with pytest.raises(AquaMedicAuthError):
        await client.authenticate()


async def test_authenticate_network_error(client, session):
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(side_effect=aiohttp.ClientError("down"))
    cm.__aexit__ = AsyncMock(return_value=False)
    session.request = MagicMock(return_value=cm)
    with pytest.raises(AquaMedicConnectionError):
        await client.authenticate()


async def test_authenticate_restores_stored_session(client, session):
    """Valid JWT + refresh token in config → device list probe, no password login."""
    client._jwt = MOCK_TOKEN
    client._refresh_token = "refresh-abc"
    client._token_created_at = int(time.time()) - 100
    client._token_expired_at = int(time.time()) + 3600
    session.request = MagicMock(
        return_value=_make_response(
            200,
            {"code": 200, "data": [{"did": MOCK_DID, "productKey": "pk"}]},
        )
    )
    await client.authenticate()
    assert client.api_mode == API_MODE_AEP
    assert "login/pwd" not in str(session.request.call_args_list)


async def test_aep_request_retries_after_refresh(client, session):
    client._api_mode = API_MODE_AEP
    client._jwt = MOCK_TOKEN
    client._refresh_token = "refresh-abc"
    client._device_list_api = DEVICE_LIST_SMART_HOME
    calls = {"n": 0}

    def _side_effect(method, url, **kwargs):
        calls["n"] += 1
        if "refresh_token" in url:
            return _make_response(
                200,
                {
                    "code": 200,
                    "data": {
                        "token": "new-jwt",
                        "refresh_token": "refresh-abc",
                        "created_at": int(time.time()),
                        "expired_at": int(time.time()) + 3600,
                    },
                },
            )
        if calls["n"] == 1:
            return _make_response(200, {"code": 526, "message": "token expired"})
        return _make_response(
            200,
            {"code": 200, "data": [{"did": MOCK_DID, "productKey": "pk"}]},
        )

    session.request = MagicMock(side_effect=_side_effect)
    devices = await client.get_devices()
    assert devices[0]["did"] == MOCK_DID
    assert devices[0]["product_key"] == "pk"
    assert client._jwt == "new-jwt"


# ── get_devices ───────────────────────────────────────────────────────────────

async def test_get_devices_aep(client, session):
    client._api_mode = API_MODE_AEP
    client._jwt = MOCK_TOKEN
    client._device_list_api = DEVICE_LIST_SMART_HOME
    session.request = MagicMock(
        return_value=_make_response(
            200,
            {
                "code": 200,
                "data": [
                    {
                        "did": MOCK_DID,
                        "productKey": "pk",
                        "name": "SmartDrift",
                        "isOnline": True,
                    }
                ],
            },
        )
    )
    result = await client.get_devices()
    assert result[0]["did"] == MOCK_DID
    assert result[0]["product_key"] == "pk"
    assert result[0]["is_online"] is True


async def test_detect_device_list_smart_home_when_bindings_404(client, session):
    client._api_mode = API_MODE_AEP
    client._jwt = MOCK_TOKEN

    def _side_effect(method, url, **kwargs):
        if "smartHome/v2/users/devices" in url:
            return _make_response(
                200,
                {"code": 200, "data": [{"did": MOCK_DID, "productKey": "pk"}]},
            )
        if "/app/bindings" in url:
            return _make_response(404, {})
        raise AssertionError(f"unexpected url {url}")

    session.request = MagicMock(side_effect=_side_effect)
    result = await client.get_devices()
    assert client.device_list_api == DEVICE_LIST_SMART_HOME
    assert client.legacy_available is False
    assert result[0]["did"] == MOCK_DID


async def test_detect_device_list_bindings_when_smart_home_404(client, session):
    client._api_mode = API_MODE_AEP
    client._jwt = MOCK_TOKEN

    def _side_effect(method, url, **kwargs):
        if "smartHome/v2/users/devices" in url:
            return _make_response(404, {})
        if "/app/bindings" in url:
            return _make_response(
                200,
                {"devices": [{"did": MOCK_DID, "product_key": "pk", "is_online": True}]},
            )
        raise AssertionError(f"unexpected url {url}")

    session.request = MagicMock(side_effect=_side_effect)
    result = await client.get_devices()
    assert client.device_list_api == DEVICE_LIST_BINDINGS
    assert result[0]["did"] == MOCK_DID


async def test_switch_to_legacy_blocked_when_migrated(client):
    client._legacy_available = False
    with pytest.raises(AquaMedicAuthError, match="migrated"):
        await client._switch_to_legacy()


async def test_get_devices_legacy(legacy_client, session):
    devices = [{"did": MOCK_DID, "is_online": True}]
    session.request = MagicMock(
        return_value=_make_response(200, {"devices": devices})
    )
    result = await legacy_client.get_devices()
    assert result[0]["did"] == MOCK_DID
    assert result[0]["is_online"] is True


async def test_get_devices_http_error(legacy_client, session):
    session.request = MagicMock(return_value=_make_response(500, {"error": "server"}))
    with pytest.raises(AquaMedicConnectionError):
        await legacy_client.get_devices()


# ── get_device_data ───────────────────────────────────────────────────────────

async def test_get_device_data_aep(client, session):
    client._api_mode = API_MODE_AEP
    client._jwt = MOCK_TOKEN
    client._device_list_api = DEVICE_LIST_BINDINGS
    payload = {"attr": {"Flow": 80}, "updated_at": 123}
    session.request = MagicMock(return_value=_make_response(200, payload))
    result = await client.get_device_data(MOCK_DID)
    assert result["attr"]["Flow"] == 80


async def test_get_device_data_smart_home_prefers_aep_devdata(client, session):
    """SmartDrift/WIFI: app uses deviceLatestData (AEP devdata), not gateway first."""
    client._api_mode = API_MODE_AEP
    client._jwt = MOCK_TOKEN
    client._device_list_api = DEVICE_LIST_SMART_HOME
    client._legacy_available = False
    payload = {"attr": {"Flow": 55}, "is_online": True, "updated_at": 99}

    def _side_effect(method, url, **kwargs):
        if "devdata" in url and "euaepapp" in url:
            return _make_response(200, payload)
        if "devices-manager" in url:
            raise AssertionError("smart_home WIFI must not call gateway before AEP devdata")
        return _make_response(200, {})

    session.request = MagicMock(side_effect=_side_effect)
    result = await client.get_device_data(MOCK_DID)
    assert result["attr"]["Flow"] == 55
    assert result["is_online"] is True


async def test_get_device_data_smart_home_gateway_fallback(client, session):
    """When AEP/Open API devdata fail, gateway is tried last."""
    client._api_mode = API_MODE_AEP
    client._jwt = MOCK_TOKEN
    client._device_list_api = DEVICE_LIST_SMART_HOME
    client._legacy_available = False

    def _side_effect(method, url, **kwargs):
        if "devdata" in url:
            return _make_response(404, {"code": 404, "message": "not found"})
        if "devices-manager" in url:
            assert kwargs.get("ssl") is False
            return _make_response(
                200,
                {
                    "data": {
                        "data": {
                            "attrs": {"Flow": 55},
                            "is_online": True,
                            "updated_at": 99,
                        }
                    }
                },
            )
        return _make_response(200, {})

    session.request = MagicMock(side_effect=_side_effect)
    result = await client.get_device_data(MOCK_DID)
    assert result["attr"]["Flow"] == 55
    assert result["is_online"] is True


async def test_get_device_data_smart_home_gateway_fallback_open_api(client, session):
    """Open API devdata is tried when AEP devdata fails."""
    client._api_mode = API_MODE_AEP
    client._jwt = MOCK_TOKEN
    client._device_list_api = DEVICE_LIST_SMART_HOME
    client._legacy_available = False

    def _side_effect(method, url, **kwargs):
        if "devdata" in url and "euaepapp" in url:
            return _make_response(404, {"code": 404, "message": "not found"})
        if "devdata" in url and "gizwits.com" in url and "gizwitsapi.com" not in url:
            return _make_response(
                200,
                {"attr": {"Flow": 42}, "is_online": True, "updated_at": 1},
            )
        if "devices-manager" in url:
            raise AssertionError("gateway should not run when Open API devdata succeeds")
        return _make_response(200, {})

    session.request = MagicMock(side_effect=_side_effect)
    result = await client.get_device_data(MOCK_DID)
    assert result["attr"]["Flow"] == 42
    assert result["is_online"] is True


async def test_get_device_data_legacy(legacy_client, session):
    payload = {"attr": {"Flow": 80}, "updated_at": 123}
    session.request = MagicMock(return_value=_make_response(200, payload))
    result = await legacy_client.get_device_data(MOCK_DID)
    assert result["attr"]["Flow"] == 80


async def test_get_device_data_empty_devdata(client, session):
    """Empty AEP devdata on bindings accounts falls back to gateway."""
    client._api_mode = API_MODE_AEP
    client._jwt = MOCK_TOKEN
    client._device_list_api = DEVICE_LIST_BINDINGS

    def _side_effect(method, url, **kwargs):
        if "devdata" in url:
            return _make_response(200, {"data": {}})
        if "devices-manager" in url:
            return _make_response(
                200, {"data": {"attrs": {"Flow": 42}, "updated_at": 99}}
            )
        return _make_response(200, {})

    session.request = MagicMock(side_effect=_side_effect)
    result = await client.get_device_data(MOCK_DID)
    assert result["attr"]["Flow"] == 42


# ── control_device ────────────────────────────────────────────────────────────

async def test_control_device_aep_smart_home_uses_gateway_first(client, session):
    """smart_home accounts must hit the Gateway controller first."""
    client._api_mode = API_MODE_AEP
    client._jwt = MOCK_TOKEN
    client._device_list_api = DEVICE_LIST_SMART_HOME
    session.request = MagicMock(return_value=_make_response(200, {"success": True}))
    await client.control_device(MOCK_DID, {"SwitchON": 1})
    call_args = session.request.call_args
    url = call_args[0][1]
    # Should hit the Gateway controller, not AEP /app/control.
    assert "devices-controller" in url, f"Expected gateway controller, got: {url}"
    assert "gizwitsapi.com" in url, f"Expected gateway host, got: {url}"
    # session.request(method, url, **kwargs) → body is in kwargs["json"].
    body = call_args[1].get("json", {})
    assert "datas" in body, f"Expected Gateway body format, got: {body}"
    assert body["datas"][0]["attrs"] == {"SwitchON": 1}


async def test_control_device_aep_smart_home_fallback_to_aep(client, session):
    """Gateway failure for smart_home falls back to AEP /app/control."""
    client._api_mode = API_MODE_AEP
    client._jwt = MOCK_TOKEN
    client._device_list_api = DEVICE_LIST_SMART_HOME
    responses = [
        _make_response(503, {"error": "gateway unavailable"}),  # Gateway fails
        _make_response(200, {"code": 200}),                     # AEP succeeds
    ]
    session.request = MagicMock(side_effect=responses)
    await client.control_device(MOCK_DID, {"SwitchON": 1})
    assert session.request.call_count == 2
    # Second call must go to AEP /app/control with {"attrs": ...} body.
    second_call = session.request.call_args_list[1]
    second_url = second_call[0][1]
    assert "/app/control/" in second_url
    assert "euaepapp.gizwits.com" in second_url
    second_body = second_call[1].get("json", {})
    assert second_body == {"attrs": {"SwitchON": 1}}


async def test_control_device_aep_bindings_body_format(client, session):
    """Bindings accounts send {"attrs": …} to AEP /app/control (not _wrap_aep envelope)."""
    client._api_mode = API_MODE_AEP
    client._jwt = MOCK_TOKEN
    client._device_list_api = DEVICE_LIST_BINDINGS
    session.request = MagicMock(return_value=_make_response(200, {"code": 200}))
    await client.control_device(MOCK_DID, {"SwitchON": 1})
    call_args = session.request.call_args
    url = call_args[0][1]
    assert "/app/control/" in url
    assert "euaepapp.gizwits.com" in url
    body = call_args[1].get("json", {})
    # Must NOT use AEP wrapper; must use plain {"attrs": …} like legacy.
    assert body == {"attrs": {"SwitchON": 1}}, f"Wrong body: {body}"
    assert "appKey" not in body, "Control body must not contain AEP envelope wrapper"


async def test_control_device_legacy(legacy_client, session):
    session.request = MagicMock(return_value=_make_response(200, {}))
    await legacy_client.control_device(MOCK_DID, {"SwitchON": 1})


async def test_control_device_error(legacy_client, session):
    session.request = MagicMock(return_value=_make_response(400, {"error": "bad"}))
    with pytest.raises(AquaMedicAuthError):
        await legacy_client.control_device(MOCK_DID, {"SwitchON": 1})


# ── Normalization ─────────────────────────────────────────────────────────────

def test_resolve_is_online():
    assert AquaMedicClient.resolve_is_online({"is_online": True}, {}) is True
    assert AquaMedicClient.resolve_is_online({}, {"is_online": False}) is False
    assert AquaMedicClient.resolve_is_online({}, {}) is None
    assert (
        AquaMedicClient.resolve_is_online({}, {"attr": {"Flow": 50}}) is True
    )
    assert AquaMedicClient.resolve_is_online({}, {"attr": {}}) is None


def test_normalize_bindings_aep_envelope(client):
    raw = {"code": 200, "data": {"devices": [{"did": "x"}]}}
    data = client._parse_aep_envelope(raw)
    assert client._normalize_bindings(data) == [{"did": "x"}]


def test_parse_aep_envelope_string_code_200(client):
    """Real AEP API returns code as string '200' with Chinese success message."""
    raw = {
        "code": "200",
        "message": "本次请求成功",
        "data": {
            "uid": "u1",
            "jwtAuthenticationDto": {"token": MOCK_TOKEN},
            "refreshToken": "rt",
        },
    }
    data = client._parse_aep_envelope(raw)
    assert data["uid"] == "u1"
    assert data["jwtAuthenticationDto"]["token"] == MOCK_TOKEN


def test_normalize_device_record_smart_home():
    raw = {
        "did": "abc",
        "productKey": "pk1",
        "name": "Pump",
        "isOnline": True,
    }
    out = AquaMedicClient._normalize_device_record(raw)
    assert out["product_key"] == "pk1"
    assert out["dev_alias"] == "Pump"
    assert out["is_online"] is True


def test_normalize_gateway_query_is_online():
    raw = {"data": {"data": {"attrs": {"Flow": 1}, "is_online": True}}}
    result = AquaMedicClient._normalize_gateway_query(raw)
    assert result["attr"]["Flow"] == 1
    assert result["is_online"] is True


def test_normalize_devdata_nested():
    raw = {"data": {"attr": {"Flow": 50}}}
    assert AquaMedicClient._normalize_devdata(raw)["attr"]["Flow"] == 50


# ── get_datapoints ────────────────────────────────────────────────────────────

async def test_get_datapoints_aep_open_api_fallback(client, session):
    """AEP datapoint 404 → regional Open API host (euapi.gizwits.com)."""
    client._api_mode = API_MODE_AEP
    client._jwt = MOCK_TOKEN
    payload = {"entities": [{"attrs": [{"name": "SwitchON"}]}]}

    def _side_effect(method, url, **kwargs):
        if "euaepapp" in url and "/app/datapoint" in url:
            raise AquaMedicConnectionError("HTTP 404 from AEP datapoint")
        if "euapi.gizwits.com" in url and "/app/datapoint" in url:
            return _make_response(200, payload)
        return _make_response(200, {})

    session.request = MagicMock(side_effect=_side_effect)
    result = await client.get_datapoints("some-product-key")
    assert "entities" in result
    assert session.request.call_count == 2


async def test_get_datapoints(legacy_client, session):
    payload = {"entities": [{"attrs": [{"name": "SwitchON"}]}]}
    session.request = MagicMock(return_value=_make_response(200, payload))
    result = await legacy_client.get_datapoints("some-product-key")
    assert "entities" in result


async def test_get_invalid_json(legacy_client, session):
    resp = MagicMock()
    resp.status = 200
    resp.text = AsyncMock(return_value="not-json{{{{")
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=resp)
    cm.__aexit__ = AsyncMock(return_value=False)
    session.request = MagicMock(return_value=cm)
    with pytest.raises(AquaMedicConnectionError):
        await legacy_client.get_devices()
