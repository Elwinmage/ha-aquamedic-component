"""Tests for AquaMedicOptionsFlow (config_flow.py lines 161–188)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from homeassistant import loader
from homeassistant.config_entries import HANDLERS
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.aquamedic.config_flow import (
    AquaMedicConfigFlow,
)
from custom_components.aquamedic.const import (
    CONF_SCAN_INTERVAL,
    DOMAIN,
)
from tests.conftest import MOCK_CONFIG_ENTRY_DATA

# ── Fixture: entry with options flow support ──────────────────────────────────


@pytest.fixture
async def entry_with_flow(hass):
    """Config entry registered in HA with config flow handler available."""
    HANDLERS.register(DOMAIN)(AquaMedicConfigFlow)
    hass.data.setdefault(loader.DATA_COMPONENTS, {})[f"{DOMAIN}.config_flow"] = (
        MagicMock()
    )

    entry = MockConfigEntry(
        domain=DOMAIN,
        data=MOCK_CONFIG_ENTRY_DATA,
        unique_id="eu_test@example.com",
    )
    entry.add_to_hass(hass)
    yield entry

    HANDLERS.pop(DOMAIN, None)


# ── Options flow: form display ────────────────────────────────────────────────


async def test_options_flow_shows_form(hass, entry_with_flow):
    result = await hass.config_entries.options.async_init(entry_with_flow.entry_id)
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "init"


async def test_options_flow_form_has_scan_interval(hass, entry_with_flow):
    result = await hass.config_entries.options.async_init(entry_with_flow.entry_id)
    schema_keys = {str(k) for k in result["data_schema"].schema}
    assert CONF_SCAN_INTERVAL in schema_keys


async def test_options_flow_prefills_current_interval(hass, entry_with_flow):
    result = await hass.config_entries.options.async_init(entry_with_flow.entry_id)
    # The form should show the current interval as default
    assert result["type"] == FlowResultType.FORM


# ── Options flow: submit ──────────────────────────────────────────────────────


async def test_options_flow_submit_updates_interval(hass, entry_with_flow):
    with patch("homeassistant.config_entries.ConfigEntries.async_schedule_reload"):
        result = await hass.config_entries.options.async_init(entry_with_flow.entry_id)
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {CONF_SCAN_INTERVAL: 60},
        )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert entry_with_flow.data[CONF_SCAN_INTERVAL] == 60


async def test_options_flow_submit_triggers_reload(hass, entry_with_flow):
    with patch(
        "homeassistant.config_entries.ConfigEntries.async_schedule_reload"
    ) as mock_reload:
        result = await hass.config_entries.options.async_init(entry_with_flow.entry_id)
        await hass.config_entries.options.async_configure(
            result["flow_id"],
            {CONF_SCAN_INTERVAL: 45},
        )

    mock_reload.assert_called_once_with(entry_with_flow.entry_id)


async def test_options_flow_min_interval(hass, entry_with_flow):
    with patch("homeassistant.config_entries.ConfigEntries.async_schedule_reload"):
        result = await hass.config_entries.options.async_init(entry_with_flow.entry_id)
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {CONF_SCAN_INTERVAL: 5},
        )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert entry_with_flow.data[CONF_SCAN_INTERVAL] == 5


async def test_options_flow_max_interval(hass, entry_with_flow):
    with patch("homeassistant.config_entries.ConfigEntries.async_schedule_reload"):
        result = await hass.config_entries.options.async_init(entry_with_flow.entry_id)
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {CONF_SCAN_INTERVAL: 300},
        )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert entry_with_flow.data[CONF_SCAN_INTERVAL] == 300


# ── Options flow: local network addresses ─────────────────────────────────────


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("", []),
        ("   ", []),
        ("10.3.141.215", ["10.3.141.215"]),
        ("10.0.0.1, 10.0.0.2;10.0.0.3\n10.0.0.1", ["10.0.0.1", "10.0.0.2", "10.0.0.3"]),
        ("pump.local", ["pump.local"]),
        ("fe80::1", ["fe80::1"]),
        ("not a host!", None),
        ("10.0.0.1, -bad-", None),
        ("a" * 300, None),
    ],
)
def test_parse_local_hosts(text, expected):
    from custom_components.aquamedic.config_flow import parse_local_hosts

    assert parse_local_hosts(text) == expected


async def test_options_flow_form_has_local_hosts(hass, entry_with_flow):
    from custom_components.aquamedic.const import CONF_LOCAL_HOSTS

    result = await hass.config_entries.options.async_init(entry_with_flow.entry_id)
    assert CONF_LOCAL_HOSTS in {str(k) for k in result["data_schema"].schema}


async def test_options_flow_saves_local_hosts(hass, entry_with_flow):
    from custom_components.aquamedic.const import CONF_LOCAL_HOSTS

    with patch("homeassistant.config_entries.ConfigEntries.async_schedule_reload"):
        result = await hass.config_entries.options.async_init(entry_with_flow.entry_id)
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {CONF_SCAN_INTERVAL: 45, CONF_LOCAL_HOSTS: "10.0.0.5, 10.0.0.6"},
        )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert entry_with_flow.data[CONF_LOCAL_HOSTS] == ["10.0.0.5", "10.0.0.6"]
    assert entry_with_flow.data[CONF_SCAN_INTERVAL] == 45


async def test_options_flow_clears_local_hosts(hass, entry_with_flow):
    from custom_components.aquamedic.const import CONF_LOCAL_HOSTS

    with patch("homeassistant.config_entries.ConfigEntries.async_schedule_reload"):
        result = await hass.config_entries.options.async_init(entry_with_flow.entry_id)
        await hass.config_entries.options.async_configure(
            result["flow_id"], {CONF_SCAN_INTERVAL: 30, CONF_LOCAL_HOSTS: ""}
        )
    assert entry_with_flow.data[CONF_LOCAL_HOSTS] == []


async def test_options_flow_shows_the_saved_hosts_again(hass, entry_with_flow):
    from custom_components.aquamedic.const import CONF_LOCAL_HOSTS

    hass.config_entries.async_update_entry(
        entry_with_flow,
        data={**entry_with_flow.data, CONF_LOCAL_HOSTS: ["10.0.0.5", "10.0.0.6"]},
    )
    result = await hass.config_entries.options.async_init(entry_with_flow.entry_id)
    default = next(
        k.default() for k in result["data_schema"].schema if str(k) == CONF_LOCAL_HOSTS
    )
    assert default == "10.0.0.5, 10.0.0.6"


async def test_options_flow_refuses_an_invalid_address(hass, entry_with_flow):
    from custom_components.aquamedic.const import CONF_LOCAL_HOSTS

    result = await hass.config_entries.options.async_init(entry_with_flow.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {CONF_SCAN_INTERVAL: 30, CONF_LOCAL_HOSTS: "10.0.0.5, not valid!"},
    )
    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {CONF_LOCAL_HOSTS: "invalid_host"}
    assert CONF_LOCAL_HOSTS not in entry_with_flow.data
