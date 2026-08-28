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
    DEVICE_LIST_BINDINGS,
    DEVICE_LIST_SMART_HOME,
    GIZWITS_APP_KEY,
    GIZWITS_LEGACY_APP_ID,
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
                {
                    "devices": [
                        {"did": MOCK_DID, "product_key": "pk", "is_online": True}
                    ]
                },
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
    session.request = MagicMock(return_value=_make_response(200, {"devices": devices}))
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
            raise AssertionError(
                "smart_home WIFI must not call gateway before AEP devdata"
            )
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
            raise AssertionError(
                "gateway should not run when Open API devdata succeeds"
            )
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
# Discovery: smart_home accounts → POST euapi.gizwits.com/app/control/{did}
#            with JWT in X-Gizwits-User-token (not Authorization).
# Gateway /v2/devices-controller returns 405 for all methods.
# AEP host /app/control returns 404.


async def test_control_device_aep_smart_home_uses_open_api(client, session):
    """smart_home: POST to Legacy Open API host with JWT as X-Gizwits-User-token."""
    client._api_mode = API_MODE_AEP
    client._jwt = MOCK_TOKEN
    client._device_list_api = DEVICE_LIST_SMART_HOME
    session.request = MagicMock(return_value=_make_response(200, {}))
    await client.control_device(MOCK_DID, {"SwitchON": 1})
    call_args = session.request.call_args
    assert call_args[0][0] == "POST"
    url = call_args[0][1]
    assert "euapi.gizwits.com" in url, f"Expected Open API host, got: {url}"
    assert "/app/control/" in url
    # Body must be {"attrs": ...}, not AEP wrapper.
    body = call_args[1].get("json", {})
    assert body == {"attrs": {"SwitchON": 1}}, f"Wrong body: {body}"
    # JWT must be in X-Gizwits-User-token, not Authorization.
    headers = call_args[1].get("headers", {})
    assert headers.get("X-Gizwits-User-token") == MOCK_TOKEN, (
        f"JWT must be in X-Gizwits-User-token, got headers: {headers}"
    )
    assert "Authorization" not in headers, (
        "Authorization header must not be set for Open API control"
    )


async def test_control_device_aep_bindings_uses_aep_host(client, session):
    """Bindings accounts → POST /app/control on AEP host (euaepapp.gizwits.com)."""
    client._api_mode = API_MODE_AEP
    client._jwt = MOCK_TOKEN
    client._device_list_api = DEVICE_LIST_BINDINGS
    session.request = MagicMock(return_value=_make_response(200, {"code": 200}))
    await client.control_device(MOCK_DID, {"SwitchON": 1})
    call_args = session.request.call_args
    assert call_args[0][0] == "POST"
    url = call_args[0][1]
    assert "euaepapp.gizwits.com" in url, f"Expected AEP host, got: {url}"
    assert "/app/control/" in url
    body = call_args[1].get("json", {})
    assert body == {"attrs": {"SwitchON": 1}}, f"Wrong body: {body}"
    assert "appKey" not in body, "No AEP envelope in control body"


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
    assert AquaMedicClient.resolve_is_online({}, {"attr": {"Flow": 50}}) is True
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


# ── _aep_code_int error path ──────────────────────────────────────────────────


def test_aep_code_int_non_castable_string():
    """L47-48: non-integer string → None (TypeError/ValueError path)."""
    from custom_components.aquamedic.client import _aep_code_int

    assert _aep_code_int("abc") is None
    assert _aep_code_int("") is None
    assert _aep_code_int(None) is None


# ── Client properties ─────────────────────────────────────────────────────────


def test_client_token_properties(client):
    """L147, 157, 162: access_token, token_expired_at, token_created_at properties."""
    client._jwt = "jwt-token"
    client._token_expired_at = 1700086400
    client._token_created_at = 1700000000
    assert client.access_token == "jwt-token"
    assert client.token_expired_at == 1700086400
    assert client.token_created_at == 1700000000


# ── _request_json ssl kwarg ───────────────────────────────────────────────────


async def test_request_json_explicit_ssl_kwarg(client, session):
    """L249: explicit ssl kwarg forwarded to session.request."""
    session.request = MagicMock(return_value=_make_response(200, {}))
    await client._request_json(
        "GET", "https://example.com/test", headers=client._aep_headers(), ssl=True
    )
    call_kwargs = session.request.call_args[1]
    assert call_kwargs.get("ssl") is True


# ── _parse_aep_envelope error branches ───────────────────────────────────────


def test_parse_aep_envelope_connection_error_for_non_auth_code(client):
    """L277: non-auth AEP error code → AquaMedicConnectionError."""
    body = {"code": "999999", "message": "Server error"}
    with pytest.raises(AquaMedicConnectionError, match="AEP error 999999"):
        client._parse_aep_envelope(body)


# ── ensure_valid_token ────────────────────────────────────────────────────────


async def test_ensure_valid_token_skips_when_not_aep(client):
    """L292: legacy mode → immediate return, no refresh attempted."""
    client._api_mode = API_MODE_LEGACY
    client._jwt = MOCK_TOKEN
    await client.ensure_valid_token()  # must not raise


async def test_ensure_valid_token_skips_when_no_jwt(client):
    """L292: AEP mode but no JWT → immediate return."""
    client._api_mode = API_MODE_AEP
    client._jwt = None
    await client.ensure_valid_token()


async def test_ensure_valid_token_skips_when_no_timestamps(client):
    """L298: no token_expired_at → return before time check."""
    client._api_mode = API_MODE_AEP
    client._jwt = MOCK_TOKEN
    client._token_expired_at = None
    client._token_created_at = None
    await client.ensure_valid_token()


async def test_ensure_valid_token_skips_when_token_still_fresh(client):
    """L302: now < mid-lifetime threshold → no refresh triggered."""
    now = int(time.time())
    client._api_mode = API_MODE_AEP
    client._jwt = MOCK_TOKEN
    client._token_created_at = now - 100  # just started
    client._token_expired_at = now + 86300  # lifetime=86400, mid=43200 → fresh
    client._refresh_token = "rt"
    await client.ensure_valid_token()  # no session call expected


async def test_ensure_valid_token_skips_when_no_refresh_token(client):
    """L304-305: past mid-lifetime but no refresh_token → return."""
    now = int(time.time())
    client._api_mode = API_MODE_AEP
    client._jwt = MOCK_TOKEN
    client._token_created_at = now - 50000
    client._token_expired_at = now + 100  # past mid-lifetime
    client._refresh_token = None
    await client.ensure_valid_token()  # no refresh, no raise


async def test_ensure_valid_token_triggers_refresh(client, session):
    """L306-307: past mid-lifetime + refresh_token → _refresh_aep_token called."""
    now = int(time.time())
    client._api_mode = API_MODE_AEP
    client._jwt = MOCK_TOKEN
    client._refresh_token = "rt-old"
    client._token_created_at = now - 50000
    client._token_expired_at = now + 100  # past mid-lifetime
    refresh_body = {
        "code": 200,
        "data": {"token": "jwt-refreshed", "refresh_token": "rt-new"},
    }
    session.request = MagicMock(return_value=_make_response(200, refresh_body))
    await client.ensure_valid_token()
    assert client._jwt == "jwt-refreshed"


# ── _update_aep_tokens edge cases ────────────────────────────────────────────


async def test_update_aep_tokens_defaults_created_at_to_now(client, session):
    """L322: createdAt absent from response → defaults to int(time.time())."""
    before = int(time.time())
    login_body = {
        "code": 200,
        "data": {
            "uid": "u1",
            "jwtAuthenticationDto": {"token": MOCK_TOKEN},
            "refreshToken": "rt",
            # No createdAt / expiredAt
        },
    }
    session.request = MagicMock(return_value=_make_response(200, login_body))
    await client._authenticate_aep()
    assert client._token_created_at is not None
    assert client._token_created_at >= before


async def test_update_aep_tokens_defaults_expired_at_to_plus_one_day(client, session):
    """L324: expiredAt absent → defaults to created_at + 86400."""
    login_body = {
        "code": 200,
        "data": {
            "uid": "u1",
            "jwtAuthenticationDto": {"token": MOCK_TOKEN},
            "refreshToken": "rt",
        },
    }
    session.request = MagicMock(return_value=_make_response(200, login_body))
    await client._authenticate_aep()
    assert client._token_expired_at == client._token_created_at + 86400


# ── _control_headers_aep ─────────────────────────────────────────────────────


def test_control_headers_aep_contains_jwt_as_user_token(client):
    """New method: JWT placed in X-Gizwits-User-token, not Authorization."""
    client._jwt = MOCK_TOKEN
    headers = client._control_headers_aep()
    assert headers["X-Gizwits-User-token"] == MOCK_TOKEN
    assert "Authorization" not in headers
    assert headers["X-Gizwits-Application-Id"] == GIZWITS_APP_KEY


# ── _fetch_devdata_open_api ───────────────────────────────────────────────────


async def test_fetch_devdata_open_api_success(client, session):
    """L633-634: Open API fallback GET returns attrs."""
    client._jwt = MOCK_TOKEN
    body = {"attr": {"Flow": 60}, "is_online": True}
    session.request = MagicMock(return_value=_make_response(200, body))
    result = await client._fetch_devdata_open_api(MOCK_DID)
    assert result.get("attr", {}).get("Flow") == 60


async def test_fetch_devdata_open_api_error_code_raises(client, session):
    """L658-660: Open API error code → AquaMedicConnectionError."""
    client._jwt = MOCK_TOKEN
    body = {"code": "404", "message": "Not found"}
    session.request = MagicMock(return_value=_make_response(200, body))
    with pytest.raises(AquaMedicConnectionError, match="Open API devdata error"):
        await client._fetch_devdata_open_api(MOCK_DID)


# ── _fetch_device_data_with_fallbacks ────────────────────────────────────────


async def test_fetch_device_data_all_fetchers_fail(client):
    """L681-682: all fetchers fail → AquaMedicConnectionError with combined msg."""

    async def _fail1(did):
        raise AquaMedicConnectionError("err1")

    async def _fail2(did):
        raise AquaMedicConnectionError("err2")

    with pytest.raises(AquaMedicConnectionError, match="err1"):
        await client._fetch_device_data_with_fallbacks(
            MOCK_DID,
            fetchers=(_fail1, _fail2),
            label="test",
        )


# ── _normalize_bindings paths ─────────────────────────────────────────────────


def test_normalize_bindings_data_devices_path(client):
    """L819-821: data.devices format (AEP envelope variant)."""
    raw = {"data": {"devices": [{"did": "d1"}, {"did": "d2"}]}}
    result = client._normalize_bindings(raw)
    assert len(result) == 2
    assert result[0]["did"] == "d1"


def test_normalize_bindings_data_devices_not_list(client):
    """L821: data.devices not a list → empty list."""
    raw = {"data": {"devices": "bad"}}
    result = client._normalize_bindings(raw)
    assert result == []


def test_normalize_bindings_top_level_devices_not_list(client):
    """L816: top-level devices not a list → empty list."""
    raw = {"devices": 42}
    result = client._normalize_bindings(raw)
    assert result == []


# ── resolve_is_online additional branches ────────────────────────────────────


def test_normalize_device_record_isOnline_fallback():
    """L790: isOnline key used when is_online absent from device record."""
    raw = {"did": "x", "productKey": "pk", "name": "Pump", "isOnline": True}
    out = AquaMedicClient._normalize_device_record(raw)
    assert out["is_online"] is True


def test_normalize_device_record_online_fallback():
    """L792: 'online' key used when is_online and isOnline both absent."""
    raw = {"did": "x", "productKey": "pk", "name": "Pump", "online": False}
    out = AquaMedicClient._normalize_device_record(raw)
    assert out["is_online"] is False


def test_resolve_is_online_none_when_attr_empty():
    """None when both device and latest have no online hint."""
    assert AquaMedicClient.resolve_is_online({}, None) is None


# ── _normalize_gateway_query branches ────────────────────────────────────────


def test_normalize_gateway_query_isOnline_key():
    """L790: isOnline (camelCase) key used when is_online absent."""
    raw = {"data": {"data": {"attrs": {"Flow": 5}, "isOnline": False}}}
    result = AquaMedicClient._normalize_gateway_query(raw)
    assert result["is_online"] is False


def test_normalize_gateway_query_flat_attrs():
    """L856: inner dict with attrs (no nested data.data)."""
    raw = {"attrs": {"Flow": 10}, "is_online": True}
    result = AquaMedicClient._normalize_gateway_query(raw)
    assert result["attr"]["Flow"] == 10


# ── _should_fallback_to_legacy ────────────────────────────────────────────────


def test_should_fallback_to_legacy_returns_false_for_404():
    exc = AquaMedicAuthError("HTTP 404 from server: {}")
    assert AquaMedicClient._should_fallback_to_legacy(exc) is False


def test_should_fallback_to_legacy_returns_true_for_9004():
    exc = AquaMedicAuthError("token invalid 9004")
    assert AquaMedicClient._should_fallback_to_legacy(exc) is True


def test_should_fallback_to_legacy_returns_false_for_other_error():
    exc = AquaMedicAuthError("HTTP 500 server error")
    assert AquaMedicClient._should_fallback_to_legacy(exc) is False


# ── authenticate with stored valid JWT ───────────────────────────────────────


async def test_authenticate_restores_valid_stored_jwt(client, session):
    """L764-765: valid JWT + refresh_token → probe session, skip re-login."""
    now = int(time.time())
    client._jwt = MOCK_TOKEN
    client._refresh_token = "rt"
    client._token_expired_at = now + 3600  # still valid
    client._device_list_api = DEVICE_LIST_SMART_HOME
    # _probe_aep_session will call _fetch_user_devices_aep → GET request
    devices_body = {"code": 200, "data": {"devices": [{"did": MOCK_DID}]}}
    session.request = MagicMock(return_value=_make_response(200, devices_body))
    await client.authenticate()
    assert client._api_mode == API_MODE_AEP


# ── get_devices fallback to legacy ───────────────────────────────────────────


async def test_get_devices_aep_falls_back_to_legacy_on_505(client, session):
    """L914: AEP auth error with legacy-fallback code (505 ∈ _AEP_AUTH_CODES) → switch."""
    # code 505 is in _AEP_AUTH_CODES → raises AquaMedicAuthError
    # "505" also matches _should_fallback_to_legacy → True
    # No refresh_token → no refresh attempt, raises directly
    aep_error = _make_response(200, {"code": "505", "message": "user not migrated"})
    provision = _make_response(200, {})
    legacy_login = _make_response(200, {"token": "legacy-tok"})
    bindings = _make_response(
        200, {"devices": [{"did": MOCK_DID, "product_key": "pk"}]}
    )
    session.request = MagicMock(
        side_effect=[aep_error, provision, legacy_login, bindings]
    )
    client._api_mode = API_MODE_AEP
    client._jwt = MOCK_TOKEN
    client._refresh_token = None  # no refresh → code-error raises directly
    client._device_list_api = DEVICE_LIST_BINDINGS
    result = await client.get_devices()
    assert len(result) >= 1


# ── get_device_data public method ────────────────────────────────────────────


async def test_get_device_data_aep_path(client, session):
    """L926-930: AEP get_device_data → _get_device_data_aep."""
    client._api_mode = API_MODE_AEP
    client._jwt = MOCK_TOKEN
    client._device_list_api = DEVICE_LIST_SMART_HOME
    # AEP devdata → 404 (not on AEP host)
    aep_404 = _make_response(404, {})
    # Open API fallback → success
    oa_body = {"attr": {"Flow": 55}, "is_online": True}
    gw_404 = _make_response(500, {"code": "404", "message": "Page Not Found"})
    session.request = MagicMock(
        side_effect=[aep_404, gw_404, _make_response(200, oa_body)]
    )
    result = await client.get_device_data(MOCK_DID)
    assert result.get("attr", {}).get("Flow") == 55
