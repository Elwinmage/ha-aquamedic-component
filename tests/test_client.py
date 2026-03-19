"""Tests for client.py."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
import json

import pytest
import aiohttp

from custom_components.aquamedic.client import (
    AquaMedicAuthError,
    AquaMedicClient,
    AquaMedicConnectionError,
)
from custom_components.aquamedic.const import GIZWITS_APP_ID

from tests.conftest import MOCK_DID, MOCK_PASSWORD, MOCK_TOKEN, MOCK_USERNAME


def _make_response(status: int, body: dict):
    """Build a fake aiohttp response as an async context manager."""
    resp = MagicMock()
    resp.status = status
    resp.text   = AsyncMock(return_value=json.dumps(body))
    resp.json   = AsyncMock(return_value=body)
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=resp)
    cm.__aexit__  = AsyncMock(return_value=False)
    return cm


@pytest.fixture
def session():
    return MagicMock(spec=aiohttp.ClientSession)


@pytest.fixture
def client(session):
    return AquaMedicClient(session, MOCK_USERNAME, MOCK_PASSWORD, region="eu")


# ── Headers ───────────────────────────────────────────────────────────────────

def test_headers_no_token(client):
    h = client._headers(authenticated=False)
    assert h["X-Gizwits-Application-Id"] == GIZWITS_APP_ID
    assert "X-Gizwits-User-token" not in h


def test_headers_with_token(client):
    client._token = MOCK_TOKEN
    h = client._headers(authenticated=True)
    assert h["X-Gizwits-User-token"] == MOCK_TOKEN


# ── Provision ─────────────────────────────────────────────────────────────────

async def test_provision_success(client, session):
    session.post = MagicMock(return_value=_make_response(200, {}))
    await client.provision()   # should not raise


async def test_provision_failure_nonfatal(client, session):
    session.post = MagicMock(return_value=_make_response(400, {"error": "bad"}))
    await client.provision()   # non-fatal: still should not raise


async def test_provision_network_error(client, session):
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(side_effect=aiohttp.ClientError("down"))
    cm.__aexit__  = AsyncMock(return_value=False)
    session.post = MagicMock(return_value=cm)
    await client.provision()   # swallowed


# ── Authenticate ──────────────────────────────────────────────────────────────

async def test_authenticate_success(client, session):
    session.post = MagicMock(return_value=_make_response(
        200, {"token": MOCK_TOKEN, "uid": "uid123"}
    ))
    await client.authenticate()
    assert client._token == MOCK_TOKEN


async def test_authenticate_bad_credentials(client, session):
    session.post = MagicMock(return_value=_make_response(
        200, {"error_code": 9004, "detail": "wrong password"}
    ))
    with pytest.raises(AquaMedicAuthError):
        await client.authenticate()


async def test_authenticate_http_error(client, session):
    session.post = MagicMock(return_value=_make_response(401, {"detail": "unauthorized"}))
    with pytest.raises(AquaMedicAuthError):
        await client.authenticate()


async def test_authenticate_network_error(client, session):
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(side_effect=aiohttp.ClientError("down"))
    cm.__aexit__  = AsyncMock(return_value=False)
    session.post = MagicMock(return_value=cm)
    with pytest.raises(AquaMedicConnectionError):
        await client.authenticate()


async def test_authenticate_invalid_json(client, session):
    resp = MagicMock()
    resp.status = 200
    resp.text   = AsyncMock(return_value="not-json{{{")
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=resp)
    cm.__aexit__  = AsyncMock(return_value=False)
    session.post = MagicMock(return_value=cm)
    with pytest.raises(AquaMedicConnectionError):
        await client.authenticate()


# ── get_devices ───────────────────────────────────────────────────────────────

async def test_get_devices_success(client, session):
    client._token = MOCK_TOKEN
    devices = [{"did": MOCK_DID, "is_online": True}]
    session.get = MagicMock(return_value=_make_response(200, {"devices": devices}))
    result = await client.get_devices()
    assert result == devices


async def test_get_devices_http_error(client, session):
    client._token = MOCK_TOKEN
    session.get = MagicMock(return_value=_make_response(500, {"error": "server"}))
    with pytest.raises(AquaMedicConnectionError):
        await client.get_devices()


# ── get_device_data ───────────────────────────────────────────────────────────

async def test_get_device_data(client, session):
    client._token = MOCK_TOKEN
    payload = {"attr": {"Flow": 80}, "updated_at": 123}
    session.get = MagicMock(return_value=_make_response(200, payload))
    result = await client.get_device_data(MOCK_DID)
    assert result["attr"]["Flow"] == 80


# ── control_device ────────────────────────────────────────────────────────────

async def test_control_device_success(client, session):
    client._token = MOCK_TOKEN
    session.post = MagicMock(return_value=_make_response(200, {}))
    await client.control_device(MOCK_DID, {"SwitchON": 1})


async def test_control_device_error(client, session):
    client._token = MOCK_TOKEN
    session.post = MagicMock(return_value=_make_response(400, {"error": "bad"}))
    with pytest.raises((AquaMedicAuthError, AquaMedicConnectionError)):
        await client.control_device(MOCK_DID, {"SwitchON": 1})


# ── get_datapoints ────────────────────────────────────────────────────────────

async def test_get_datapoints(client, session):
    client._token = MOCK_TOKEN
    payload = {"entities": [{"attrs": [{"name": "SwitchON"}]}]}
    session.get = MagicMock(return_value=_make_response(200, payload))
    result = await client.get_datapoints("some-product-key")
    assert "entities" in result


# ── _get GET error path (client.py lines 96-97, 106) ─────────────────────────

async def test_get_invalid_json(client, session):
    """_get raises AquaMedicConnectionError on invalid JSON."""
    resp = MagicMock()
    resp.status = 200
    resp.text   = AsyncMock(return_value="not-json{{{{")
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=resp)
    cm.__aexit__  = AsyncMock(return_value=False)
    session.get = MagicMock(return_value=cm)
    client._token = MOCK_TOKEN
    with pytest.raises(AquaMedicConnectionError):
        await client.get_devices()


async def test_get_network_error(client, session):
    """_get raises AquaMedicConnectionError on aiohttp.ClientError."""
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(side_effect=aiohttp.ClientError("network"))
    cm.__aexit__  = AsyncMock(return_value=False)
    session.get = MagicMock(return_value=cm)
    client._token = MOCK_TOKEN
    with pytest.raises(AquaMedicConnectionError):
        await client.get_devices()
