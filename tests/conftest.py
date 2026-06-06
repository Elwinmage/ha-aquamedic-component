"""Shared pytest fixtures for Aquamedic tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant import loader
from homeassistant.config_entries import HANDLERS

from custom_components.aquamedic.config_flow import AquaMedicConfigFlow
from custom_components.aquamedic.const import (
    CONF_PASSWORD,
    CONF_REGION,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    SMARTDRIFT_PRODUCT_KEY,
)
from custom_components.aquamedic.coordinator import (
    AquaMedicCoordinator,
    AquaMedicDeviceData,
)

# ── Shared test data ──────────────────────────────────────────────────────────

MOCK_USERNAME = "test@example.com"
MOCK_PASSWORD = "secret"
MOCK_REGION   = "eu"
MOCK_DID      = "hy9Evqpl5SbzhoViqGBEE7"
MOCK_TOKEN    = "mock-token-abc123"

MOCK_DEVICE_ONLINE = {
    "did":          MOCK_DID,
    "product_key":  SMARTDRIFT_PRODUCT_KEY,
    "dev_alias":    "SmartDrift Test",
    "product_name": "Current_Pump",
    "is_online":    True,
}

MOCK_DEVICE_OFFLINE = {**MOCK_DEVICE_ONLINE, "is_online": False}

MOCK_ATTRS = {
    "SwitchON": 1, "PulseTide": 0, "FeedSwitch": 0, "TimerON": 0,
    "Mode": 1, "Linkage": 0, "Flow": 75, "Frequency": 50, "FeedTime": 10,
    "Fault_Overcurrent": 0, "Fault_Overvoltage": 0, "Fault_OverTemp": 0,
    "Fault_Undervoltage": 0, "Fault_Lockedrotor": 0,
    "Fault_no_liveload": 0, "Fault_UART": 0,
}

MOCK_LATEST = {"attr": MOCK_ATTRS, "updated_at": 1700000000}

MOCK_CONFIG_ENTRY_DATA = {
    CONF_USERNAME:      MOCK_USERNAME,
    CONF_PASSWORD:      MOCK_PASSWORD,
    CONF_REGION:        MOCK_REGION,
    CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
}

# ── Core fixtures ─────────────────────────────────────────────────────────────

@pytest.fixture
def domain():
    return DOMAIN


@pytest.fixture
def mock_client():
    """Return a mocked AquaMedicClient."""
    client = MagicMock()
    client.authenticate = AsyncMock(return_value=None)
    client.get_devices = AsyncMock(return_value=[MOCK_DEVICE_ONLINE])
    client.get_device_data = AsyncMock(return_value=MOCK_LATEST)
    client.control_device = AsyncMock(return_value=None)
    client.api_mode = "aep"
    client.refresh_token = None
    client.token_created_at = None
    client.token_expired_at = None
    return client


@pytest.fixture
def device_data_online():
    return AquaMedicDeviceData(MOCK_DEVICE_ONLINE, MOCK_LATEST)


@pytest.fixture
def device_data_offline():
    return AquaMedicDeviceData(MOCK_DEVICE_OFFLINE, {})


@pytest.fixture
def coordinator(hass, mock_client):
    """Coordinator pre-loaded with one online SmartDrift device."""
    coord = AquaMedicCoordinator(hass, mock_client, scan_interval=30)
    coord.data = {MOCK_DID: AquaMedicDeviceData(MOCK_DEVICE_ONLINE, MOCK_LATEST)}
    return coord


@pytest.fixture(autouse=True)
def mock_coordinator_refresh(coordinator):
    """Prevent HA debouncer lingering timers in control tests."""
    coordinator.async_request_refresh = AsyncMock()
    coordinator.async_update_listeners = MagicMock()


# ── Config flow registration fixture ─────────────────────────────────────────

@pytest.fixture
async def register_config_flow(hass):
    """Register the AquaMedic config flow handler with the HA flow engine.

    Required for any test that calls hass.config_entries.flow.async_init().
    Usage: add `register_config_flow` to the test's fixture arguments.
    """
    HANDLERS.register(DOMAIN)(AquaMedicConfigFlow)
    hass.data.setdefault(loader.DATA_COMPONENTS, {})[
        f"{DOMAIN}.config_flow"
    ] = MagicMock()
    yield
    HANDLERS.pop(DOMAIN, None)
    hass.data.get(loader.DATA_COMPONENTS, {}).pop(f"{DOMAIN}.config_flow", None)
