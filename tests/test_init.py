"""Tests for __init__.py — setup/teardown and token persistence."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from homeassistant.config_entries import ConfigEntry
from homeassistant.exceptions import ConfigEntryNotReady

# Correct import — NOT `from ... __init__ import`, but `from ... import`
from custom_components.aquamedic import _persist_client_tokens, async_setup_entry, async_unload_entry
from custom_components.aquamedic.client import AquaMedicAuthError, AquaMedicConnectionError
from custom_components.aquamedic.const import (
    CONF_ACCESS_TOKEN,
    CONF_API_MODE,
    CONF_DEVICE_LIST_API,
    CONF_PASSWORD,
    CONF_REFRESH_TOKEN,
    CONF_REGION,
    CONF_SCAN_INTERVAL,
    CONF_TOKEN_CREATED_AT,
    CONF_TOKEN_EXPIRED_AT,
    CONF_USERNAME,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from tests.conftest import MOCK_DID, MOCK_DEVICE_ONLINE, MOCK_LATEST


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_mock_entry() -> MagicMock:
    """Lightweight mock entry for _persist_client_tokens unit tests (no HA registry)."""
    entry = MagicMock(spec=ConfigEntry)
    entry.data = {
        CONF_USERNAME:      "user@test.com",
        CONF_PASSWORD:      "secret",
        CONF_REGION:        "eu",
        CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
    }
    entry.entry_id = "test-entry-id"
    return entry


def _make_real_entry(hass):
    """Real MockConfigEntry registered in HA for async_setup_entry tests."""
    from pytest_homeassistant_custom_component.common import MockConfigEntry
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_USERNAME:      "user@test.com",
            CONF_PASSWORD:      "secret",
            CONF_REGION:        "eu",
            CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
        },
        entry_id="test-entry-id",
    )
    entry.add_to_hass(hass)
    return entry


def _make_mock_client(**kwargs) -> MagicMock:
    c = MagicMock()
    c.authenticate       = AsyncMock()
    c.refresh_token      = kwargs.get("refresh_token", None)
    c.access_token       = kwargs.get("access_token",  None)
    c.token_created_at   = kwargs.get("token_created_at", None)
    c.token_expired_at   = kwargs.get("token_expired_at", None)
    c.api_mode           = kwargs.get("api_mode", "aep")
    c.device_list_api    = kwargs.get("device_list_api", "smart_home")
    return c


def _make_mock_coordinator(data: dict | None = None) -> MagicMock:
    coord = MagicMock()
    coord.async_config_entry_first_refresh = AsyncMock()
    coord.data = data or {}
    return coord


# ── _persist_client_tokens ────────────────────────────────────────────────────

def test_persist_skipped_when_no_refresh_token():
    """Early return when refresh_token is None."""
    hass = MagicMock()
    entry = _make_mock_entry()
    client = _make_mock_client(refresh_token=None)
    _persist_client_tokens(hass, entry, client)
    hass.config_entries.async_update_entry.assert_not_called()


def test_persist_skipped_when_refresh_token_empty_string():
    """Early return when refresh_token is an empty string."""
    hass = MagicMock()
    entry = _make_mock_entry()
    client = _make_mock_client(refresh_token="")
    _persist_client_tokens(hass, entry, client)
    hass.config_entries.async_update_entry.assert_not_called()


def test_persist_saves_all_tokens():
    """Lines 41-53: all token fields written when refresh_token is valid."""
    hass = MagicMock()
    entry = _make_mock_entry()
    client = _make_mock_client(
        refresh_token="rt-abc",
        access_token="jwt-xyz",
        token_created_at=1700000000,
        token_expired_at=1700086400,
        api_mode="aep",
        device_list_api="smart_home",
    )
    _persist_client_tokens(hass, entry, client)
    hass.config_entries.async_update_entry.assert_called_once()
    _, call_kwargs = hass.config_entries.async_update_entry.call_args
    saved = call_kwargs["data"]
    assert saved[CONF_REFRESH_TOKEN]    == "rt-abc"
    assert saved[CONF_ACCESS_TOKEN]     == "jwt-xyz"
    assert saved[CONF_TOKEN_CREATED_AT] == 1700000000
    assert saved[CONF_TOKEN_EXPIRED_AT] == 1700086400
    assert saved[CONF_API_MODE]         == "aep"
    assert saved[CONF_DEVICE_LIST_API]  == "smart_home"


def test_persist_skips_none_access_token():
    """access_token key must not be written when None."""
    hass = MagicMock()
    entry = _make_mock_entry()
    client = _make_mock_client(refresh_token="rt", access_token=None)
    _persist_client_tokens(hass, entry, client)
    _, call_kwargs = hass.config_entries.async_update_entry.call_args
    saved = call_kwargs["data"]
    assert CONF_ACCESS_TOKEN not in saved


def test_persist_skips_none_timestamps():
    """token_created_at / token_expired_at must not be written when None."""
    hass = MagicMock()
    entry = _make_mock_entry()
    client = _make_mock_client(refresh_token="rt", token_created_at=None, token_expired_at=None)
    _persist_client_tokens(hass, entry, client)
    _, call_kwargs = hass.config_entries.async_update_entry.call_args
    saved = call_kwargs["data"]
    assert CONF_TOKEN_CREATED_AT not in saved
    assert CONF_TOKEN_EXPIRED_AT not in saved


# ── async_setup_entry ─────────────────────────────────────────────────────────

async def test_async_setup_entry_success(hass):
    """Lines 58-128: successful setup stores coordinator in hass.data."""
    entry = _make_mock_entry()
    mock_client = _make_mock_client(
        refresh_token="rt", access_token="jwt",
        token_created_at=1000, token_expired_at=2000,
    )
    mock_coord = _make_mock_coordinator(
        data={MOCK_DID: MagicMock(
            name="SmartDrift",
            product_key="pk",
            is_online=True,
        )}
    )

    with (
        patch("custom_components.aquamedic.AquaMedicClient", return_value=mock_client),
        patch("custom_components.aquamedic.AquaMedicCoordinator", return_value=mock_coord),
        patch("custom_components.aquamedic.async_get_clientsession", return_value=MagicMock()),
        # Patch token persistence: tested separately; avoids UnknownEntry on mock entry.
        patch("custom_components.aquamedic._persist_client_tokens"),
        patch("homeassistant.config_entries.ConfigEntries.async_forward_entry_setups",
              new_callable=AsyncMock),
    ):
        result = await async_setup_entry(hass, entry)

    assert result is True


async def test_async_setup_entry_success_empty_coordinator(hass):
    """Lines 58-128: setup with empty coordinator data (no device loop)."""
    entry = _make_mock_entry()
    mock_client = _make_mock_client()
    mock_coord  = _make_mock_coordinator(data={})

    with (
        patch("custom_components.aquamedic.AquaMedicClient", return_value=mock_client),
        patch("custom_components.aquamedic.AquaMedicCoordinator", return_value=mock_coord),
        patch("custom_components.aquamedic.async_get_clientsession", return_value=MagicMock()),
        patch("homeassistant.config_entries.ConfigEntries.async_forward_entry_setups",
              new_callable=AsyncMock),
    ):
        result = await async_setup_entry(hass, entry)

    assert result is True


async def test_async_setup_entry_auth_error_raises(hass):
    """Lines 83-86: AquaMedicAuthError → ConfigEntryAuthFailed."""
    from homeassistant.exceptions import ConfigEntryAuthFailed

    entry = _make_mock_entry()
    mock_client = _make_mock_client()
    mock_client.authenticate.side_effect = AquaMedicAuthError("bad credentials")

    with (
        patch("custom_components.aquamedic.AquaMedicClient", return_value=mock_client),
        patch("custom_components.aquamedic.async_get_clientsession", return_value=MagicMock()),
    ):
        with pytest.raises(ConfigEntryAuthFailed):
            await async_setup_entry(hass, entry)


async def test_async_setup_entry_connection_error_raises(hass):
    """Lines 88-89: AquaMedicConnectionError → ConfigEntryNotReady."""
    entry = _make_mock_entry()
    mock_client = _make_mock_client()
    mock_client.authenticate.side_effect = AquaMedicConnectionError("network down")

    with (
        patch("custom_components.aquamedic.AquaMedicClient", return_value=mock_client),
        patch("custom_components.aquamedic.async_get_clientsession", return_value=MagicMock()),
    ):
        with pytest.raises(ConfigEntryNotReady):
            await async_setup_entry(hass, entry)


async def test_async_setup_entry_device_offline_status(hass):
    """Lines 103-128: device loop with offline and unknown online states."""
    entry = _make_mock_entry()
    mock_client = _make_mock_client(refresh_token="rt")
    offline_dev = MagicMock(name="Pump", product_key="pk", is_online=False)
    unknown_dev = MagicMock(name="Pump2", product_key="pk2", is_online=None)
    mock_coord  = _make_mock_coordinator(
        data={"did1": offline_dev, "did2": unknown_dev}
    )

    with (
        patch("custom_components.aquamedic.AquaMedicClient", return_value=mock_client),
        patch("custom_components.aquamedic.AquaMedicCoordinator", return_value=mock_coord),
        patch("custom_components.aquamedic.async_get_clientsession", return_value=MagicMock()),
        patch("custom_components.aquamedic._persist_client_tokens"),
        patch("homeassistant.config_entries.ConfigEntries.async_forward_entry_setups",
              new_callable=AsyncMock),
    ):
        result = await async_setup_entry(hass, entry)

    assert result is True


# ── async_unload_entry ────────────────────────────────────────────────────────

async def test_async_unload_entry_success(hass):
    """Lines 133-136: unload removes coordinator from hass.data."""
    entry = _make_mock_entry()
    mock_coord = _make_mock_coordinator()
    hass.data.setdefault(DOMAIN, {})["test-entry-id"] = mock_coord

    with patch(
        "homeassistant.config_entries.ConfigEntries.async_unload_platforms",
        new_callable=AsyncMock,
        return_value=True,
    ):
        result = await async_unload_entry(hass, entry)

    assert result is True
    assert "test-entry-id" not in hass.data.get(DOMAIN, {})


async def test_async_unload_entry_failure_keeps_coordinator(hass):
    """Lines 133-136: failed unload keeps coordinator in hass.data."""
    entry = _make_mock_entry()
    mock_coord = _make_mock_coordinator()
    hass.data.setdefault(DOMAIN, {})["test-entry-id"] = mock_coord

    with patch(
        "homeassistant.config_entries.ConfigEntries.async_unload_platforms",
        new_callable=AsyncMock,
        return_value=False,
    ):
        result = await async_unload_entry(hass, entry)

    assert result is False
    assert "test-entry-id" in hass.data.get(DOMAIN, {})
