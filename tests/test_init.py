"""Tests for __init__.py — setup/teardown and token persistence."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from custom_components.aquamedic.__init__ import _persist_client_tokens
from custom_components.aquamedic.const import (
    CONF_ACCESS_TOKEN,
    CONF_API_MODE,
    CONF_DEVICE_LIST_API,
    CONF_REFRESH_TOKEN,
    CONF_TOKEN_CREATED_AT,
    CONF_TOKEN_EXPIRED_AT,
)


def _mock_client(**kwargs):
    c = MagicMock()
    c.refresh_token    = kwargs.get("refresh_token", None)
    c.access_token     = kwargs.get("access_token", None)
    c.token_created_at = kwargs.get("token_created_at", None)
    c.token_expired_at = kwargs.get("token_expired_at", None)
    c.api_mode         = kwargs.get("api_mode", "aep")
    c.device_list_api  = kwargs.get("device_list_api", "smart_home")
    return c


def _mock_entry(data: dict | None = None):
    entry = MagicMock()
    entry.data = data or {}
    return entry


# ── _persist_client_tokens ────────────────────────────────────────────────────

def test_persist_skipped_when_no_refresh_token():
    """Early return (L40) when refresh_token is None."""
    hass = MagicMock()
    entry = _mock_entry()
    client = _mock_client(refresh_token=None)
    _persist_client_tokens(hass, entry, client)
    hass.config_entries.async_update_entry.assert_not_called()


def test_persist_skipped_when_refresh_token_empty_string():
    """Early return when refresh_token is an empty string."""
    hass = MagicMock()
    entry = _mock_entry()
    client = _mock_client(refresh_token="")
    _persist_client_tokens(hass, entry, client)
    hass.config_entries.async_update_entry.assert_not_called()


def test_persist_saves_all_tokens():
    """Lines 41-53: all token fields written when refresh_token is present."""
    hass = MagicMock()
    entry = _mock_entry({"username": "user@test.com"})
    client = _mock_client(
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
    # Original entry data must be preserved
    assert saved["username"] == "user@test.com"


def test_persist_skips_none_access_token():
    """access_token key must not be written when client.access_token is None."""
    hass = MagicMock()
    entry = _mock_entry()
    client = _mock_client(refresh_token="rt", access_token=None)
    _persist_client_tokens(hass, entry, client)
    _, call_kwargs = hass.config_entries.async_update_entry.call_args
    saved = call_kwargs["data"]
    assert CONF_ACCESS_TOKEN not in saved
    assert CONF_REFRESH_TOKEN in saved


def test_persist_skips_none_timestamps():
    """token_created_at / token_expired_at must not be written when None."""
    hass = MagicMock()
    entry = _mock_entry()
    client = _mock_client(
        refresh_token="rt",
        access_token="jwt",
        token_created_at=None,
        token_expired_at=None,
    )
    _persist_client_tokens(hass, entry, client)
    _, call_kwargs = hass.config_entries.async_update_entry.call_args
    saved = call_kwargs["data"]
    assert CONF_TOKEN_CREATED_AT not in saved
    assert CONF_TOKEN_EXPIRED_AT not in saved
