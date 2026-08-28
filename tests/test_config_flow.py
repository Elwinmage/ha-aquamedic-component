"""Tests for config_flow.py."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

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
    CONF_SIM_HOST,
    CONF_USERNAME,
    DEFAULT_REGION,
    DOMAIN,
)
from tests.conftest import (
    MOCK_CONFIG_ENTRY_DATA,
    MOCK_PASSWORD,
    MOCK_USERNAME,
)

# ── Simulator flag fixture ────────────────────────────────────────────────────


@pytest.fixture
def simulator_flag():
    """Create the .simulator_enabled flag file for the duration of the test."""
    from custom_components.aquamedic.config_flow import _SIM_FLAG

    _SIM_FLAG.touch()
    yield
    _SIM_FLAG.unlink(missing_ok=True)


# ── Shared input ──────────────────────────────────────────────────────────────

VALID_INPUT = {
    CONF_USERNAME: MOCK_USERNAME,
    CONF_PASSWORD: MOCK_PASSWORD,
    CONF_REGION: "eu",
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
    assert CONF_USERNAME in schema_keys
    assert CONF_PASSWORD in schema_keys
    assert CONF_REGION in schema_keys
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
        MockClient.return_value.get_devices = AsyncMock(return_value=[])

        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], VALID_INPUT
        )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == MOCK_USERNAME
    assert result["data"][CONF_USERNAME] == MOCK_USERNAME
    assert result["data"][CONF_REGION] == "eu"
    assert result["data"][CONF_SCAN_INTERVAL] == 30


async def test_flow_success_calls_authenticate(hass, register_config_flow):
    with (
        patch("custom_components.aquamedic.config_flow.AquaMedicClient") as MockClient,
        patch(
            "custom_components.aquamedic.config_flow.async_get_clientsession",
            return_value=MagicMock(),
        ),
    ):
        MockClient.return_value.authenticate = AsyncMock()
        MockClient.return_value.get_devices = AsyncMock(return_value=[])

        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        await hass.config_entries.flow.async_configure(result["flow_id"], VALID_INPUT)
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
        MockClient.return_value.get_devices = AsyncMock(return_value=[])

        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        await hass.config_entries.flow.async_configure(result["flow_id"], VALID_INPUT)
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

    assert result["type"] == FlowResultType.FORM
    assert result["errors"]["base"] == "invalid_auth"


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

    assert result["type"] == FlowResultType.FORM
    assert result["errors"]["base"] == "cannot_connect"


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

    assert result["type"] == FlowResultType.FORM
    assert result["errors"]["base"] == "unknown"


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
        MockClient.return_value.get_devices = AsyncMock(return_value=[])

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
    import logging

    from custom_components.aquamedic.config_flow import _log_devices

    with caplog.at_level(logging.INFO):
        _log_devices([])
    assert "No devices found" in caplog.text


def test_log_devices_with_devices(caplog):
    import logging

    from custom_components.aquamedic.config_flow import _log_devices

    devices = [
        {"dev_alias": "Pump1", "did": "abc", "product_key": "pk1", "is_online": True},
        {
            "dev_alias": None,
            "product_name": "Pump2",
            "did": "def",
            "product_key": "pk2",
            "is_online": False,
        },
    ]
    with caplog.at_level(logging.INFO):
        _log_devices(devices)
    assert "2 device(s)" in caplog.text
    assert "Pump1" in caplog.text
    assert "ONLINE" in caplog.text
    assert "OFFLINE" in caplog.text


def test_log_devices_fallback_unknown(caplog):
    import logging

    from custom_components.aquamedic.config_flow import _log_devices

    devices = [
        {
            "dev_alias": None,
            "product_name": None,
            "did": "x",
            "product_key": "pk",
            "is_online": False,
        }
    ]
    with caplog.at_level(logging.INFO):
        _log_devices(devices)
    assert "Unknown" in caplog.text


def test_log_devices_unknown_online_state(caplog):
    """L95: else branch when is_online is None (state unknown)."""
    import logging

    from custom_components.aquamedic.config_flow import _log_devices

    devices = [
        {"dev_alias": "Pump", "did": "abc", "product_key": "pk", "is_online": None}
    ]
    with caplog.at_level(logging.INFO):
        _log_devices(devices)
    assert "UNKNOWN" in caplog.text


# ── _interval_selector (config_flow.py lines 72-73) ──────────────────────────


def test_interval_selector_returns_selector():
    from homeassistant.helpers.selector import NumberSelector

    from custom_components.aquamedic.config_flow import _interval_selector

    sel = _interval_selector()
    assert isinstance(sel, NumberSelector)


# ── Simulator region flow ─────────────────────────────────────────────────────

SIM_HOST = "http://192.168.100.10:8080"

SIM_INPUT_STEP1 = {
    CONF_USERNAME: MOCK_USERNAME,
    CONF_PASSWORD: MOCK_PASSWORD,
    CONF_REGION: "sim",
    CONF_SCAN_INTERVAL: 30,
}

SIM_INPUT_STEP2 = {CONF_SIM_HOST: SIM_HOST}


async def test_sim_flow_shows_sim_host_step(hass, register_config_flow, simulator_flag):
    """Choosing 'sim' region redirects to the sim_host step."""
    with (
        patch("custom_components.aquamedic.config_flow.AquaMedicClient"),
        patch(
            "custom_components.aquamedic.config_flow.async_get_clientsession",
            return_value=MagicMock(),
        ),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], SIM_INPUT_STEP1
        )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "sim_host"


async def test_sim_flow_default_host_in_schema(
    hass, register_config_flow, simulator_flag
):
    """sim_host step shows the default localhost URL."""
    from custom_components.aquamedic.const import SIM_DEFAULT_HOST

    with (
        patch("custom_components.aquamedic.config_flow.AquaMedicClient"),
        patch(
            "custom_components.aquamedic.config_flow.async_get_clientsession",
            return_value=MagicMock(),
        ),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], SIM_INPUT_STEP1
        )

    # The default value in the schema key should be SIM_DEFAULT_HOST
    keys = {str(k): k for k in result["data_schema"].schema}
    sim_key = keys.get(CONF_SIM_HOST)
    assert sim_key is not None
    assert sim_key.default() == SIM_DEFAULT_HOST


async def test_sim_flow_success_creates_entry(
    hass, register_config_flow, simulator_flag
):
    """Full sim flow creates an entry with sim_host stored."""
    with (
        patch("custom_components.aquamedic.config_flow.AquaMedicClient") as MockClient,
        patch(
            "custom_components.aquamedic.config_flow.async_get_clientsession",
            return_value=MagicMock(),
        ),
    ):
        MockClient.return_value.authenticate = AsyncMock()
        MockClient.return_value.get_devices = AsyncMock(return_value=[])

        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], SIM_INPUT_STEP1
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], SIM_INPUT_STEP2
        )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_REGION] == "sim"
    assert result["data"][CONF_SIM_HOST] == SIM_HOST
    assert "(simulator)" in result["title"]


async def test_sim_flow_client_receives_sim_host(
    hass, register_config_flow, simulator_flag
):
    """AquaMedicClient is instantiated with sim_host kwarg."""
    with (
        patch("custom_components.aquamedic.config_flow.AquaMedicClient") as MockClient,
        patch(
            "custom_components.aquamedic.config_flow.async_get_clientsession",
            return_value=MagicMock(),
        ),
    ):
        MockClient.return_value.authenticate = AsyncMock()
        MockClient.return_value.get_devices = AsyncMock(return_value=[])

        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], SIM_INPUT_STEP1
        )
        await hass.config_entries.flow.async_configure(
            result["flow_id"], SIM_INPUT_STEP2
        )

    _, kwargs = MockClient.call_args
    assert kwargs.get("sim_host") == SIM_HOST


async def test_sim_flow_auth_error_returns_to_sim_host_step(
    hass, register_config_flow, simulator_flag
):
    """Auth error while on sim region re-shows the sim_host step."""
    with (
        patch("custom_components.aquamedic.config_flow.AquaMedicClient") as MockClient,
        patch(
            "custom_components.aquamedic.config_flow.async_get_clientsession",
            return_value=MagicMock(),
        ),
    ):
        MockClient.return_value.authenticate = AsyncMock(
            side_effect=AquaMedicAuthError("bad")
        )

        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], SIM_INPUT_STEP1
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], SIM_INPUT_STEP2
        )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "sim_host"
    assert result["errors"]["base"] == "invalid_auth"


async def test_sim_flow_cannot_connect_returns_to_sim_host_step(
    hass, register_config_flow, simulator_flag
):
    """Connection error while on sim region re-shows the sim_host step."""
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
            result["flow_id"], SIM_INPUT_STEP1
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], SIM_INPUT_STEP2
        )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "sim_host"
    assert result["errors"]["base"] == "cannot_connect"


# ── client._sim_urls ──────────────────────────────────────────────────────────


def test_sim_urls_builds_correct_urls():
    from custom_components.aquamedic.client import _sim_urls

    urls = _sim_urls("http://192.168.100.10:8080")
    assert urls["LOGIN"] == "http://192.168.100.10:8080/app/login"
    assert urls["BINDINGS"] == "http://192.168.100.10:8080/app/bindings"
    assert "{device_id}" in urls["DEVDATA"]
    assert "{device_id}" in urls["CONTROL"]


def test_sim_urls_strips_trailing_slash():
    from custom_components.aquamedic.client import _sim_urls

    urls = _sim_urls("http://localhost:8080/")
    assert urls["LOGIN"] == "http://localhost:8080/app/login"


# ── AquaMedicClient sim_host kwarg ────────────────────────────────────────────


def test_client_uses_sim_urls_when_region_sim():
    from unittest.mock import MagicMock

    import aiohttp

    from custom_components.aquamedic.client import AquaMedicClient

    session = MagicMock(spec=aiohttp.ClientSession)
    client = AquaMedicClient(
        session, "u", "p", region="sim", sim_host="http://sim:9000"
    )
    assert client._legacy_urls["LOGIN"] == "http://sim:9000/app/login"


def test_client_uses_standard_urls_when_no_sim_host():
    from unittest.mock import MagicMock

    import aiohttp

    from custom_components.aquamedic.client import AquaMedicClient
    from custom_components.aquamedic.const import GIZWITS_API_URLS

    session = MagicMock(spec=aiohttp.ClientSession)
    client = AquaMedicClient(session, "u", "p", region="eu")
    assert client._legacy_urls == GIZWITS_API_URLS["eu"]


# ── Simulator flag: disabled when file absent ─────────────────────────────────


async def test_sim_region_hidden_when_flag_absent(hass, register_config_flow):
    """'sim' region must NOT appear in the form when flag file is absent."""
    from custom_components.aquamedic.config_flow import _SIM_FLAG

    _SIM_FLAG.unlink(missing_ok=True)  # ensure flag is absent

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM
    # Extract the region selector options
    region_sel = next(
        v for k, v in result["data_schema"].schema.items() if str(k) == "region"
    )
    option_values = [o["value"] for o in region_sel.config["options"]]
    assert "sim" not in option_values


async def test_sim_step_aborts_when_flag_absent(hass, register_config_flow):
    """async_step_sim_host must abort when flag file is absent."""
    from custom_components.aquamedic.config_flow import _SIM_FLAG, AquaMedicConfigFlow

    _SIM_FLAG.unlink(missing_ok=True)

    flow = AquaMedicConfigFlow()
    flow.hass = hass
    result = await flow.async_step_sim_host()
    assert result["type"] == "abort"
    assert result["reason"] == "simulator_disabled"


# ── _simulator_enabled() True path (L95) ─────────────────────────────────────


def test_simulator_enabled_returns_true_when_flag_exists(simulator_flag):
    """L95: _SIM_FLAG.exists() path when flag file is present."""
    from custom_components.aquamedic.config_flow import _simulator_enabled

    assert _simulator_enabled() is True


def test_simulator_enabled_returns_false_when_flag_absent():
    """_SIM_FLAG.exists() returns False when flag file is absent."""
    from custom_components.aquamedic.config_flow import _SIM_FLAG, _simulator_enabled

    _SIM_FLAG.unlink(missing_ok=True)
    assert _simulator_enabled() is False


# ── Token persistence in _async_try_connect (L288-298) ───────────────────────


async def test_flow_persists_aep_tokens_in_entry(hass, register_config_flow):
    """L288-298: tokens stored in config entry when client has refresh_token."""
    with (
        patch("custom_components.aquamedic.config_flow.AquaMedicClient") as MockClient,
        patch(
            "custom_components.aquamedic.config_flow.async_get_clientsession",
            return_value=MagicMock(),
        ),
    ):
        mock_instance = MockClient.return_value
        mock_instance.authenticate = AsyncMock()
        mock_instance.get_devices = AsyncMock(return_value=[])
        mock_instance.refresh_token = "rt-stored"
        mock_instance.access_token = "jwt-stored"
        mock_instance.token_created_at = 1700000000
        mock_instance.token_expired_at = 1700086400
        mock_instance.api_mode = "aep"
        mock_instance.device_list_api = "smart_home"

        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], VALID_INPUT
        )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    data = result["data"]
    assert data.get("refresh_token") == "rt-stored"
    assert data.get("access_token") == "jwt-stored"
    assert data.get("api_mode") == "aep"
    assert data.get("device_list_api") == "smart_home"


async def test_flow_skips_token_persistence_when_no_refresh_token(
    hass, register_config_flow
):
    """No token keys in entry when refresh_token is None."""
    with (
        patch("custom_components.aquamedic.config_flow.AquaMedicClient") as MockClient,
        patch(
            "custom_components.aquamedic.config_flow.async_get_clientsession",
            return_value=MagicMock(),
        ),
    ):
        mock_instance = MockClient.return_value
        mock_instance.authenticate = AsyncMock()
        mock_instance.get_devices = AsyncMock(return_value=[])
        mock_instance.refresh_token = None
        mock_instance.access_token = None
        mock_instance.api_mode = "aep"
        mock_instance.device_list_api = "smart_home"

        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], VALID_INPUT
        )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert "refresh_token" not in result["data"]
    assert "access_token" not in result["data"]


# ── Re-authentication flow ────────────────────────────────────────────────────


async def test_reauth_flow_shows_form(hass, register_config_flow):
    """async_step_reauth → async_step_reauth_confirm shows the form."""
    existing_entry = MockConfigEntry(
        domain=DOMAIN,
        data={**VALID_INPUT, CONF_USERNAME: "old@test.com"},
        entry_id="reauth-entry-id",
    )
    existing_entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_REAUTH, "entry_id": "reauth-entry-id"},
        data=existing_entry.data,
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"


async def test_reauth_flow_success(hass, register_config_flow):
    """Successful reauth updates the entry and reloads."""
    existing_entry = MockConfigEntry(
        domain=DOMAIN,
        data={**VALID_INPUT, CONF_USERNAME: "old@test.com"},
        entry_id="reauth-entry-id",
    )
    existing_entry.add_to_hass(hass)

    with (
        patch("custom_components.aquamedic.config_flow.AquaMedicClient") as MockClient,
        patch(
            "custom_components.aquamedic.config_flow.async_get_clientsession",
            return_value=MagicMock(),
        ),
    ):
        mock_instance = MockClient.return_value
        mock_instance.authenticate = AsyncMock()
        mock_instance.refresh_token = "new-rt"
        mock_instance.access_token = "new-jwt"
        mock_instance.token_created_at = 1000
        mock_instance.token_expired_at = 2000
        mock_instance.api_mode = "aep"
        mock_instance.device_list_api = "smart_home"

        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={
                "source": config_entries.SOURCE_REAUTH,
                "entry_id": "reauth-entry-id",
            },
            data=existing_entry.data,
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"username": "new@test.com", "password": "newpwd"},
        )

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    # Entry data must be updated with new credentials
    assert existing_entry.data[CONF_USERNAME] == "new@test.com"
    assert existing_entry.data[CONF_PASSWORD] == "newpwd"
    assert existing_entry.data.get("refresh_token") == "new-rt"


async def test_reauth_flow_invalid_auth(hass, register_config_flow):
    """Wrong password on reauth → shows form again with invalid_auth error."""
    existing_entry = MockConfigEntry(
        domain=DOMAIN,
        data=VALID_INPUT,
        entry_id="reauth-entry-id",
    )
    existing_entry.add_to_hass(hass)

    with (
        patch("custom_components.aquamedic.config_flow.AquaMedicClient") as MockClient,
        patch(
            "custom_components.aquamedic.config_flow.async_get_clientsession",
            return_value=MagicMock(),
        ),
    ):
        from custom_components.aquamedic.client import AquaMedicAuthError

        MockClient.return_value.authenticate = AsyncMock(
            side_effect=AquaMedicAuthError("bad password")
        )
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={
                "source": config_entries.SOURCE_REAUTH,
                "entry_id": "reauth-entry-id",
            },
            data=existing_entry.data,
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"username": MOCK_USERNAME, "password": "wrongpwd"},
        )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"]["base"] == "invalid_auth"


async def test_reauth_flow_cannot_connect(hass, register_config_flow):
    """Network error on reauth → cannot_connect error."""
    existing_entry = MockConfigEntry(
        domain=DOMAIN,
        data=VALID_INPUT,
        entry_id="reauth-entry-id",
    )
    existing_entry.add_to_hass(hass)

    with (
        patch("custom_components.aquamedic.config_flow.AquaMedicClient") as MockClient,
        patch(
            "custom_components.aquamedic.config_flow.async_get_clientsession",
            return_value=MagicMock(),
        ),
    ):
        from custom_components.aquamedic.client import AquaMedicConnectionError

        MockClient.return_value.authenticate = AsyncMock(
            side_effect=AquaMedicConnectionError("timeout")
        )
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={
                "source": config_entries.SOURCE_REAUTH,
                "entry_id": "reauth-entry-id",
            },
            data=existing_entry.data,
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"username": MOCK_USERNAME, "password": "pwd"},
        )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"]["base"] == "cannot_connect"


async def test_reauth_flow_unknown_error(hass, register_config_flow):
    """Unexpected exception on reauth → unknown error."""
    existing_entry = MockConfigEntry(
        domain=DOMAIN,
        data=VALID_INPUT,
        entry_id="reauth-entry-id",
    )
    existing_entry.add_to_hass(hass)

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
            DOMAIN,
            context={
                "source": config_entries.SOURCE_REAUTH,
                "entry_id": "reauth-entry-id",
            },
            data=existing_entry.data,
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"username": MOCK_USERNAME, "password": "pwd"},
        )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"]["base"] == "unknown"


# ── Reconfigure flow ──────────────────────────────────────────────────────────


async def test_reconfigure_flow_shows_form(hass, register_config_flow):
    """async_step_reconfigure shows form pre-filled with current data."""
    existing_entry = MockConfigEntry(
        domain=DOMAIN,
        data={**VALID_INPUT, CONF_USERNAME: "current@test.com", CONF_SCAN_INTERVAL: 60},
        entry_id="reconf-entry-id",
    )
    existing_entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={
            "source": config_entries.SOURCE_RECONFIGURE,
            "entry_id": "reconf-entry-id",
        },
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "reconfigure"


async def test_reconfigure_flow_success(hass, register_config_flow):
    """Successful reconfigure updates credentials, interval and tokens."""
    existing_entry = MockConfigEntry(
        domain=DOMAIN,
        data=VALID_INPUT,
        entry_id="reconf-entry-id",
    )
    existing_entry.add_to_hass(hass)

    with (
        patch("custom_components.aquamedic.config_flow.AquaMedicClient") as MockClient,
        patch(
            "custom_components.aquamedic.config_flow.async_get_clientsession",
            return_value=MagicMock(),
        ),
    ):
        mock_instance = MockClient.return_value
        mock_instance.authenticate = AsyncMock()
        mock_instance.refresh_token = "rt-new"
        mock_instance.access_token = "jwt-new"
        mock_instance.token_created_at = 1000
        mock_instance.token_expired_at = 2000
        mock_instance.api_mode = "aep"
        mock_instance.device_list_api = "smart_home"

        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={
                "source": config_entries.SOURCE_RECONFIGURE,
                "entry_id": "reconf-entry-id",
            },
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_USERNAME: "updated@test.com",
                CONF_PASSWORD: "newpassword",
                CONF_SCAN_INTERVAL: 60,
            },
        )

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert existing_entry.data[CONF_USERNAME] == "updated@test.com"
    assert existing_entry.data[CONF_PASSWORD] == "newpassword"
    assert existing_entry.data[CONF_SCAN_INTERVAL] == 60
    assert existing_entry.data.get("refresh_token") == "rt-new"


async def test_reconfigure_flow_invalid_auth(hass, register_config_flow):
    """Wrong new password on reconfigure → invalid_auth."""
    existing_entry = MockConfigEntry(
        domain=DOMAIN,
        data=VALID_INPUT,
        entry_id="reconf-entry-id",
    )
    existing_entry.add_to_hass(hass)

    with (
        patch("custom_components.aquamedic.config_flow.AquaMedicClient") as MockClient,
        patch(
            "custom_components.aquamedic.config_flow.async_get_clientsession",
            return_value=MagicMock(),
        ),
    ):
        from custom_components.aquamedic.client import AquaMedicAuthError

        MockClient.return_value.authenticate = AsyncMock(
            side_effect=AquaMedicAuthError("bad")
        )
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={
                "source": config_entries.SOURCE_RECONFIGURE,
                "entry_id": "reconf-entry-id",
            },
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_USERNAME: MOCK_USERNAME,
                CONF_PASSWORD: "bad",
                CONF_SCAN_INTERVAL: 30,
            },
        )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"]["base"] == "invalid_auth"


async def test_reconfigure_flow_cannot_connect(hass, register_config_flow):
    """Network error on reconfigure → cannot_connect."""
    existing_entry = MockConfigEntry(
        domain=DOMAIN,
        data=VALID_INPUT,
        entry_id="reconf-entry-id",
    )
    existing_entry.add_to_hass(hass)

    with (
        patch("custom_components.aquamedic.config_flow.AquaMedicClient") as MockClient,
        patch(
            "custom_components.aquamedic.config_flow.async_get_clientsession",
            return_value=MagicMock(),
        ),
    ):
        from custom_components.aquamedic.client import AquaMedicConnectionError

        MockClient.return_value.authenticate = AsyncMock(
            side_effect=AquaMedicConnectionError("timeout")
        )
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={
                "source": config_entries.SOURCE_RECONFIGURE,
                "entry_id": "reconf-entry-id",
            },
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_USERNAME: MOCK_USERNAME,
                CONF_PASSWORD: "pwd",
                CONF_SCAN_INTERVAL: 30,
            },
        )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"]["base"] == "cannot_connect"


async def test_reconfigure_flow_unknown_error(hass, register_config_flow):
    """Unexpected exception on reconfigure → unknown error."""
    existing_entry = MockConfigEntry(
        domain=DOMAIN,
        data=VALID_INPUT,
        entry_id="reconf-entry-id",
    )
    existing_entry.add_to_hass(hass)

    with (
        patch("custom_components.aquamedic.config_flow.AquaMedicClient") as MockClient,
        patch(
            "custom_components.aquamedic.config_flow.async_get_clientsession",
            return_value=MagicMock(),
        ),
    ):
        MockClient.return_value.authenticate = AsyncMock(
            side_effect=RuntimeError("oops")
        )
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={
                "source": config_entries.SOURCE_RECONFIGURE,
                "entry_id": "reconf-entry-id",
            },
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_USERNAME: MOCK_USERNAME,
                CONF_PASSWORD: "pwd",
                CONF_SCAN_INTERVAL: 30,
            },
        )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"]["base"] == "unknown"


async def test_reconfigure_flow_no_token_persistence_when_none(
    hass, register_config_flow
):
    """refresh_token=None on reconfigure → no token keys in entry."""
    existing_entry = MockConfigEntry(
        domain=DOMAIN,
        data=VALID_INPUT,
        entry_id="reconf-entry-id",
    )
    existing_entry.add_to_hass(hass)

    with (
        patch("custom_components.aquamedic.config_flow.AquaMedicClient") as MockClient,
        patch(
            "custom_components.aquamedic.config_flow.async_get_clientsession",
            return_value=MagicMock(),
        ),
    ):
        mock_instance = MockClient.return_value
        mock_instance.authenticate = AsyncMock()
        mock_instance.refresh_token = None
        mock_instance.access_token = None
        mock_instance.api_mode = "aep"
        mock_instance.device_list_api = "smart_home"

        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={
                "source": config_entries.SOURCE_RECONFIGURE,
                "entry_id": "reconf-entry-id",
            },
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_USERNAME: "new@test.com",
                CONF_PASSWORD: "pwd",
                CONF_SCAN_INTERVAL: 30,
            },
        )

    assert result["type"] == FlowResultType.ABORT
    assert "refresh_token" not in existing_entry.data


# ── entry_not_found guard tests (L314 reauth, L410 reconfigure) ───────────────


async def test_reauth_entry_not_found_aborts(hass, register_config_flow):
    """L314: async_step_reauth aborts when entry_id does not exist in registry."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={
            "source": config_entries.SOURCE_REAUTH,
            "entry_id": "nonexistent-entry-id-xyz",
        },
        data={},
    )
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "entry_not_found"


async def test_reconfigure_entry_not_found_aborts(hass, register_config_flow):
    """L410: async_step_reconfigure aborts when entry_id does not exist in registry."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={
            "source": config_entries.SOURCE_RECONFIGURE,
            "entry_id": "nonexistent-entry-id-xyz",
        },
    )
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "entry_not_found"
