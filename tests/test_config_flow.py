"""Tests for config_flow.py."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType

from custom_components.aquamedic.client import (
    AquaMedicAuthError,
    AquaMedicConnectionError,
)
from custom_components.aquamedic.config_flow import (
    AquaMedicConfigFlow,
    AquaMedicOptionsFlow,
    _default_region,
)
from custom_components.aquamedic.const import (
    CONF_PASSWORD,
    CONF_REGION,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
    DEFAULT_REGION,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from tests.conftest import MOCK_CONFIG_ENTRY_DATA, MOCK_DID, MOCK_PASSWORD, MOCK_USERNAME

# ── Shared input ──────────────────────────────────────────────────────────────

VALID_INPUT = {
    CONF_USERNAME:      MOCK_USERNAME,
    CONF_PASSWORD:      MOCK_PASSWORD,
    CONF_REGION:        "eu",
    CONF_SCAN_INTERVAL: 30,
}

# ── _default_region (pure unit — no HA needed) ────────────────────────────────

def test_default_region_french():
    assert _default_region("fr") == "eu"


def test_default_region_german():
    assert _default_region("de") == "eu"


def test_default_region_spanish():
    assert _default_region("es") == "eu"


def test_default_region_chinese_full():
    assert _default_region("zh-Hans") == "cn"


def test_default_region_chinese_short():
    assert _default_region("zh") == "cn"


def test_default_region_japanese():
    assert _default_region("ja") == "us"


def test_default_region_korean():
    assert _default_region("ko") == "us"


def test_default_region_unknown_falls_back_to_default():
    assert _default_region("xx") == DEFAULT_REGION


def test_default_region_english():
    assert _default_region("en") == "eu"


def test_default_region_prefix_fallback():
    # "fr-BE" → prefix "fr" → "eu"
    assert _default_region("fr-BE") == "eu"


def test_default_region_us_prefix():
    # "ko-KR" → prefix "ko" → "us"
    assert _default_region("ko-KR") == "us"


# ── ConfigFlow class (pure unit) ──────────────────────────────────────────────

def test_config_flow_version():
    assert AquaMedicConfigFlow.VERSION == 1


def test_options_flow_staticmethod_exists():
    assert callable(getattr(AquaMedicConfigFlow, "async_get_options_flow", None))


# ── AquaMedicOptionsFlow (unit — no HA flow engine) ──────────────────────────

def test_options_flow_stores_entry():
    entry = MagicMock()
    entry.data = MOCK_CONFIG_ENTRY_DATA
    flow = AquaMedicOptionsFlow(entry)
    assert flow._config_entry is entry


# ── Flow form display ─────────────────────────────────────────────────────────

async def test_flow_shows_form(hass, register_config_flow):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"


async def test_flow_form_has_region_field(hass, register_config_flow):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM
    # schema contains our 4 fields
    schema_keys = {str(k) for k in result["data_schema"].schema}
    assert CONF_USERNAME      in schema_keys
    assert CONF_PASSWORD      in schema_keys
    assert CONF_REGION        in schema_keys
    assert CONF_SCAN_INTERVAL in schema_keys


# ── Flow: successful authentication ──────────────────────────────────────────

async def test_flow_success_creates_entry(hass, register_config_flow):
    with (
        patch("custom_components.aquamedic.config_flow.AquaMedicClient") as MockClient,
        patch(
            "custom_components.aquamedic.config_flow.async_get_clientsession",
            return_value=MagicMock(),
        ),
    ):
        MockClient.return_value.authenticate = AsyncMock()
        MockClient.return_value.get_devices  = AsyncMock(return_value=[])

        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], VALID_INPUT
        )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"]                       == MOCK_USERNAME
    assert result["data"][CONF_USERNAME]          == MOCK_USERNAME
    assert result["data"][CONF_REGION]            == "eu"
    assert result["data"][CONF_SCAN_INTERVAL]     == 30


async def test_flow_success_calls_authenticate(hass, register_config_flow):
    with (
        patch("custom_components.aquamedic.config_flow.AquaMedicClient") as MockClient,
        patch(
            "custom_components.aquamedic.config_flow.async_get_clientsession",
            return_value=MagicMock(),
        ),
    ):
        MockClient.return_value.authenticate = AsyncMock()
        MockClient.return_value.get_devices  = AsyncMock(return_value=[])

        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        await hass.config_entries.flow.async_configure(
            result["flow_id"], VALID_INPUT
        )
        MockClient.return_value.authenticate.assert_called_once()


async def test_flow_success_calls_get_devices(hass, register_config_flow):
    with (
        patch("custom_components.aquamedic.config_flow.AquaMedicClient") as MockClient,
        patch(
            "custom_components.aquamedic.config_flow.async_get_clientsession",
            return_value=MagicMock(),
        ),
    ):
        MockClient.return_value.authenticate = AsyncMock()
        MockClient.return_value.get_devices  = AsyncMock(return_value=[])

        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        await hass.config_entries.flow.async_configure(
            result["flow_id"], VALID_INPUT
        )
        MockClient.return_value.get_devices.assert_called_once()


# ── Flow: error cases ─────────────────────────────────────────────────────────

async def test_flow_invalid_auth_shows_error(hass, register_config_flow):
    with (
        patch("custom_components.aquamedic.config_flow.AquaMedicClient") as MockClient,
        patch(
            "custom_components.aquamedic.config_flow.async_get_clientsession",
            return_value=MagicMock(),
        ),
    ):
        MockClient.return_value.authenticate = AsyncMock(
            side_effect=AquaMedicAuthError("bad creds")
        )
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], VALID_INPUT
        )

    assert result["type"]            == FlowResultType.FORM
    assert result["errors"]["base"]  == "invalid_auth"


async def test_flow_cannot_connect_shows_error(hass, register_config_flow):
    with (
        patch("custom_components.aquamedic.config_flow.AquaMedicClient") as MockClient,
        patch(
            "custom_components.aquamedic.config_flow.async_get_clientsession",
            return_value=MagicMock(),
        ),
    ):
        MockClient.return_value.authenticate = AsyncMock(
            side_effect=AquaMedicConnectionError("unreachable")
        )
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], VALID_INPUT
        )

    assert result["type"]            == FlowResultType.FORM
    assert result["errors"]["base"]  == "cannot_connect"


async def test_flow_unknown_exception_shows_error(hass, register_config_flow):
    with (
        patch("custom_components.aquamedic.config_flow.AquaMedicClient") as MockClient,
        patch(
            "custom_components.aquamedic.config_flow.async_get_clientsession",
            return_value=MagicMock(),
        ),
    ):
        MockClient.return_value.authenticate = AsyncMock(
            side_effect=RuntimeError("unexpected")
        )
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], VALID_INPUT
        )

    assert result["type"]            == FlowResultType.FORM
    assert result["errors"]["base"]  == "unknown"


async def test_flow_error_allows_retry(hass, register_config_flow):
    """After an error the form is shown again — user can retry."""
    call_count = 0

    async def auth_then_succeed(*a, **kw):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise AquaMedicAuthError("first attempt fails")

    with (
        patch("custom_components.aquamedic.config_flow.AquaMedicClient") as MockClient,
        patch(
            "custom_components.aquamedic.config_flow.async_get_clientsession",
            return_value=MagicMock(),
        ),
    ):
        MockClient.return_value.authenticate = AsyncMock(side_effect=auth_then_succeed)
        MockClient.return_value.get_devices  = AsyncMock(return_value=[])

        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        # First attempt → error
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], VALID_INPUT
        )
        assert result["type"] == FlowResultType.FORM

        # Second attempt → success
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], VALID_INPUT
        )

    assert result["type"] == FlowResultType.CREATE_ENTRY


# ── _log_devices (config_flow.py lines 63-69) ────────────────────────────────

def test_log_devices_empty(caplog):
    from custom_components.aquamedic.config_flow import _log_devices
    import logging
    with caplog.at_level(logging.INFO):
        _log_devices([])
    assert "No devices found" in caplog.text


def test_log_devices_with_devices(caplog):
    from custom_components.aquamedic.config_flow import _log_devices
    import logging
    devices = [
        {"dev_alias": "Pump1", "did": "abc", "product_key": "pk1", "is_online": True},
        {"dev_alias": None, "product_name": "Pump2", "did": "def", "product_key": "pk2", "is_online": False},
    ]
    with caplog.at_level(logging.INFO):
        _log_devices(devices)
    assert "2 device(s)" in caplog.text
    assert "Pump1" in caplog.text
    assert "ONLINE" in caplog.text
    assert "OFFLINE" in caplog.text


def test_log_devices_fallback_unknown(caplog):
    from custom_components.aquamedic.config_flow import _log_devices
    import logging
    devices = [{"dev_alias": None, "product_name": None, "did": "x", "product_key": "pk", "is_online": False}]
    with caplog.at_level(logging.INFO):
        _log_devices(devices)
    assert "Unknown" in caplog.text


# ── _interval_selector (config_flow.py lines 72-73) ──────────────────────────

def test_interval_selector_returns_selector():
    from custom_components.aquamedic.config_flow import _interval_selector
    from homeassistant.helpers.selector import NumberSelector
    sel = _interval_selector()
    assert isinstance(sel, NumberSelector)
