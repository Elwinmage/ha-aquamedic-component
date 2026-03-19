"""Tests for __init__.py (integration setup / teardown)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.aquamedic import async_setup_entry, async_unload_entry
from custom_components.aquamedic.client import (
    AquaMedicAuthError,
    AquaMedicConnectionError,
)
from custom_components.aquamedic.const import DOMAIN
from tests.conftest import MOCK_CONFIG_ENTRY_DATA, MOCK_DID


# ── PLATFORMS ─────────────────────────────────────────────────────────────────

def test_platforms_list():
    from custom_components.aquamedic import PLATFORMS
    assert set(PLATFORMS) == {"switch", "select", "number", "binary_sensor", "button"}


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def entry(hass):
    e = MockConfigEntry(
        domain=DOMAIN,
        data=MOCK_CONFIG_ENTRY_DATA,
        unique_id="eu_test@example.com",
    )
    e.add_to_hass(hass)
    return e


@pytest.fixture
def coord_mock():
    c = MagicMock()
    c.data = {}
    c.async_config_entry_first_refresh = AsyncMock()
    return c


# ── async_setup_entry ─────────────────────────────────────────────────────────

async def test_setup_entry_success(hass, entry, coord_mock):
    with (
        patch("custom_components.aquamedic.AquaMedicClient") as MockClient,
        patch("custom_components.aquamedic.async_get_clientsession", return_value=MagicMock()),
        patch("custom_components.aquamedic.AquaMedicCoordinator", return_value=coord_mock),
        patch("homeassistant.config_entries.ConfigEntries.async_forward_entry_setups", new_callable=AsyncMock),
    ):
        MockClient.return_value.authenticate = AsyncMock()
        result = await async_setup_entry(hass, entry)

    assert result is True


async def test_setup_entry_stores_coordinator(hass, entry, coord_mock):
    with (
        patch("custom_components.aquamedic.AquaMedicClient") as MockClient,
        patch("custom_components.aquamedic.async_get_clientsession", return_value=MagicMock()),
        patch("custom_components.aquamedic.AquaMedicCoordinator", return_value=coord_mock),
        patch("homeassistant.config_entries.ConfigEntries.async_forward_entry_setups", new_callable=AsyncMock),
    ):
        MockClient.return_value.authenticate = AsyncMock()
        await async_setup_entry(hass, entry)

    assert hass.data[DOMAIN][entry.entry_id] is coord_mock


async def test_setup_entry_creates_client_with_correct_region(hass, entry, coord_mock):
    with (
        patch("custom_components.aquamedic.AquaMedicClient") as MockClient,
        patch("custom_components.aquamedic.async_get_clientsession", return_value=MagicMock()),
        patch("custom_components.aquamedic.AquaMedicCoordinator", return_value=coord_mock),
        patch("homeassistant.config_entries.ConfigEntries.async_forward_entry_setups", new_callable=AsyncMock),
    ):
        MockClient.return_value.authenticate = AsyncMock()
        await async_setup_entry(hass, entry)
        # Client constructed with username, password, region
        args = MockClient.call_args
        assert args[0][3] == "eu"   # region is 4th positional arg (after session, username, password)


async def test_setup_entry_calls_authenticate(hass, entry, coord_mock):
    with (
        patch("custom_components.aquamedic.AquaMedicClient") as MockClient,
        patch("custom_components.aquamedic.async_get_clientsession", return_value=MagicMock()),
        patch("custom_components.aquamedic.AquaMedicCoordinator", return_value=coord_mock),
        patch("homeassistant.config_entries.ConfigEntries.async_forward_entry_setups", new_callable=AsyncMock),
    ):
        MockClient.return_value.authenticate = AsyncMock()
        await async_setup_entry(hass, entry)
        MockClient.return_value.authenticate.assert_called_once()


async def test_setup_entry_calls_first_refresh(hass, entry, coord_mock):
    with (
        patch("custom_components.aquamedic.AquaMedicClient") as MockClient,
        patch("custom_components.aquamedic.async_get_clientsession", return_value=MagicMock()),
        patch("custom_components.aquamedic.AquaMedicCoordinator", return_value=coord_mock),
        patch("homeassistant.config_entries.ConfigEntries.async_forward_entry_setups", new_callable=AsyncMock),
    ):
        MockClient.return_value.authenticate = AsyncMock()
        await async_setup_entry(hass, entry)
        coord_mock.async_config_entry_first_refresh.assert_called_once()


async def test_setup_entry_logs_devices(hass, entry, coord_mock):
    """When coordinator.data is populated, setup logs device info."""
    coord_mock.data = {
        MOCK_DID: MagicMock(name="Pump", product_key="pk", is_online=True, attrs={})
    }
    with (
        patch("custom_components.aquamedic.AquaMedicClient") as MockClient,
        patch("custom_components.aquamedic.async_get_clientsession", return_value=MagicMock()),
        patch("custom_components.aquamedic.AquaMedicCoordinator", return_value=coord_mock),
        patch("homeassistant.config_entries.ConfigEntries.async_forward_entry_setups", new_callable=AsyncMock),
    ):
        MockClient.return_value.authenticate = AsyncMock()
        result = await async_setup_entry(hass, entry)

    assert result is True


# ── Auth and connection errors ────────────────────────────────────────────────

async def test_setup_entry_auth_error_raises(hass, entry):
    with (
        patch("custom_components.aquamedic.AquaMedicClient") as MockClient,
        patch("custom_components.aquamedic.async_get_clientsession", return_value=MagicMock()),
    ):
        MockClient.return_value.authenticate = AsyncMock(
            side_effect=AquaMedicAuthError("bad creds")
        )
        with pytest.raises(ConfigEntryAuthFailed):
            await async_setup_entry(hass, entry)


async def test_setup_entry_connection_error_raises(hass, entry):
    with (
        patch("custom_components.aquamedic.AquaMedicClient") as MockClient,
        patch("custom_components.aquamedic.async_get_clientsession", return_value=MagicMock()),
    ):
        MockClient.return_value.authenticate = AsyncMock(
            side_effect=AquaMedicConnectionError("unreachable")
        )
        with pytest.raises(ConfigEntryNotReady):
            await async_setup_entry(hass, entry)


# ── async_unload_entry ────────────────────────────────────────────────────────

async def test_unload_entry_returns_true(hass, entry):
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = MagicMock()

    with patch(
        "homeassistant.config_entries.ConfigEntries.async_unload_platforms",
        new_callable=AsyncMock,
        return_value=True,
    ):
        result = await async_unload_entry(hass, entry)

    assert result is True


async def test_unload_entry_removes_from_hass_data(hass, entry):
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = MagicMock()

    with patch(
        "homeassistant.config_entries.ConfigEntries.async_unload_platforms",
        new_callable=AsyncMock,
        return_value=True,
    ):
        await async_unload_entry(hass, entry)

    assert entry.entry_id not in hass.data.get(DOMAIN, {})


async def test_unload_entry_keeps_data_on_failure(hass, entry):
    sentinel = object()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = sentinel

    with patch(
        "homeassistant.config_entries.ConfigEntries.async_unload_platforms",
        new_callable=AsyncMock,
        return_value=False,
    ):
        result = await async_unload_entry(hass, entry)

    assert result is False
    assert hass.data[DOMAIN][entry.entry_id] is sentinel


async def test_unload_entry_returns_false_on_platform_failure(hass, entry):
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = MagicMock()

    with patch(
        "homeassistant.config_entries.ConfigEntries.async_unload_platforms",
        new_callable=AsyncMock,
        return_value=False,
    ):
        result = await async_unload_entry(hass, entry)

    assert result is False
