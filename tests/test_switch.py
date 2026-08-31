"""Tests for switch.py."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.aquamedic.switch import (
    SWITCH_DESCRIPTIONS,
    AquaMedicLocalSwitchEntity,
    AquaMedicSwitchDescription,
    AquaMedicSwitchEntity,
    _SwitchKind,
)
from tests.conftest import MOCK_DID


def _get_desc(key: str) -> AquaMedicSwitchDescription:
    for d in SWITCH_DESCRIPTIONS:
        if d.key == key:
            return d
    raise KeyError(key)


@pytest.fixture
def switch_power(coordinator):
    return AquaMedicSwitchEntity(coordinator, MOCK_DID, _get_desc("power"))


@pytest.fixture
def switch_feed(coordinator):
    return AquaMedicSwitchEntity(coordinator, MOCK_DID, _get_desc("feed_switch"))


@pytest.fixture
def switch_local(coordinator):
    return AquaMedicLocalSwitchEntity(coordinator, MOCK_DID, _get_desc("control_0_10v"))


# ── Descriptions ──────────────────────────────────────────────────────────────


def test_all_descriptions_present():
    keys = {d.key for d in SWITCH_DESCRIPTIONS}
    assert "power" in keys
    assert "pulse_tide" in keys
    assert "feed_switch" in keys
    assert "timer_on" in keys
    assert "control_0_10v" in keys


def test_local_switch_kind():
    desc = _get_desc("control_0_10v")
    assert desc.kind is _SwitchKind.LOCAL


def test_gizwits_switch_kind():
    desc = _get_desc("power")
    assert desc.kind is _SwitchKind.GIZWITS


# ── Gizwits switch state ──────────────────────────────────────────────────────


def test_switch_power_is_on(switch_power):
    assert switch_power.is_on is True  # SwitchON=1


def test_switch_feed_is_off(switch_feed):
    assert switch_feed.is_on is False  # FeedSwitch=0


def test_switch_available_online(switch_power):
    assert switch_power.available is True


def test_switch_unavailable_offline(coordinator):
    from custom_components.aquamedic.coordinator import AquaMedicDeviceData
    from tests.conftest import MOCK_DEVICE_OFFLINE, MOCK_LATEST

    coordinator.data = {MOCK_DID: AquaMedicDeviceData(MOCK_DEVICE_OFFLINE, MOCK_LATEST)}
    sw = AquaMedicSwitchEntity(coordinator, MOCK_DID, _get_desc("power"))
    assert sw.available is False


def test_switch_unavailable_no_data(coordinator):
    coordinator.data = {}
    sw = AquaMedicSwitchEntity(coordinator, MOCK_DID, _get_desc("power"))
    assert sw.available is False


def test_switch_icon_on(switch_power):
    assert switch_power.icon == "mdi:power"


def test_switch_icon_off(coordinator):
    from custom_components.aquamedic.coordinator import AquaMedicDeviceData
    from tests.conftest import MOCK_DEVICE_ONLINE, MOCK_LATEST

    attrs = {**MOCK_LATEST["attr"], "SwitchON": 0}
    coordinator.data = {
        MOCK_DID: AquaMedicDeviceData(MOCK_DEVICE_ONLINE, {"attr": attrs})
    }
    sw = AquaMedicSwitchEntity(coordinator, MOCK_DID, _get_desc("power"))
    assert sw.icon == "mdi:power-off"


async def test_switch_turn_on(switch_power, coordinator, mock_client):
    await switch_power.async_turn_on()
    mock_client.control_device.assert_called_once_with(MOCK_DID, {"SwitchON": 1})


async def test_switch_turn_off(switch_power, coordinator, mock_client):
    await switch_power.async_turn_off()
    mock_client.control_device.assert_called_once_with(MOCK_DID, {"SwitchON": 0})


# ── Local 0-10V switch ────────────────────────────────────────────────────────


def test_local_switch_default_off(switch_local):
    assert switch_local.is_on is False


def test_local_switch_always_available(switch_local, coordinator):
    coordinator.data = {}  # device offline
    assert switch_local.available is True


async def test_local_switch_turn_on(switch_local, coordinator):
    switch_local.async_write_ha_state = lambda: None  # hass not attached in unit tests
    await switch_local.async_turn_on()
    assert coordinator.get_control_0_10v(MOCK_DID) is True


async def test_local_switch_turn_off(switch_local, coordinator):
    switch_local.async_write_ha_state = lambda: None  # hass not attached in unit tests
    await switch_local.async_turn_on()
    await switch_local.async_turn_off()
    assert coordinator.get_control_0_10v(MOCK_DID) is False


def test_local_switch_icon(switch_local):
    assert switch_local.icon == "mdi:tune-variant"


# ── AquaMedicLocalSwitchEntity.device_info and async_added_to_hass ────────────


def test_local_switch_device_info(switch_local, coordinator):
    """device_info uses coordinator data to build DeviceInfo."""
    info = switch_local.device_info
    assert isinstance(info, dict)
    assert ("aquamedic", MOCK_DID) in info["identifiers"]


def test_local_switch_device_info_no_data(coordinator):
    """device_info falls back to did when coordinator.data is empty."""
    from custom_components.aquamedic.switch import (
        AquaMedicLocalSwitchEntity,
        AquaMedicSwitchDescription,
        _SwitchKind,
    )

    coordinator.data = {}
    desc = AquaMedicSwitchDescription(
        key="control_0_10v",
        translation_key="control_0_10v",
        attr="",
        kind=_SwitchKind.LOCAL,
        icon="mdi:tune-variant",
        icon_off="mdi:tune-variant",
    )
    entity = AquaMedicLocalSwitchEntity(coordinator, MOCK_DID, desc)
    info = entity.device_info
    assert info["name"] == MOCK_DID


# ── AquaMedicLocalSwitchEntity.async_added_to_hass state restore ─────────────


async def test_local_switch_restore_on_state(coordinator):
    """async_added_to_hass restores 'on' state from last_state."""
    from custom_components.aquamedic.switch import (
        AquaMedicLocalSwitchEntity,
        AquaMedicSwitchDescription,
        _SwitchKind,
    )

    desc = AquaMedicSwitchDescription(
        key="control_0_10v",
        translation_key="control_0_10v",
        attr="",
        kind=_SwitchKind.LOCAL,
        icon="mdi:tune-variant",
        icon_off="mdi:tune-variant",
    )
    entity = AquaMedicLocalSwitchEntity(coordinator, MOCK_DID, desc)
    entity.async_write_ha_state = MagicMock()  # hass not attached in unit tests

    last_state = MagicMock()
    last_state.state = "on"
    entity.async_get_last_state = AsyncMock(return_value=last_state)

    with (
        patch(
            "homeassistant.helpers.restore_state.RestoreEntity.async_added_to_hass",
            new_callable=AsyncMock,
        ),
        patch(
            "homeassistant.helpers.update_coordinator.CoordinatorEntity.async_added_to_hass",
            new_callable=AsyncMock,
        ),
    ):
        await entity.async_added_to_hass()

    assert coordinator.get_control_0_10v(MOCK_DID) is True


async def test_local_switch_restore_off_state(coordinator):
    """async_added_to_hass restores 'off' state from last_state."""
    from custom_components.aquamedic.switch import (
        AquaMedicLocalSwitchEntity,
        AquaMedicSwitchDescription,
        _SwitchKind,
    )

    coordinator.set_control_0_10v(MOCK_DID, True)  # pre-set to True

    desc = AquaMedicSwitchDescription(
        key="control_0_10v",
        translation_key="control_0_10v",
        attr="",
        kind=_SwitchKind.LOCAL,
        icon="mdi:tune-variant",
        icon_off="mdi:tune-variant",
    )
    entity = AquaMedicLocalSwitchEntity(coordinator, MOCK_DID, desc)
    entity.async_write_ha_state = MagicMock()

    last_state = MagicMock()
    last_state.state = "off"
    entity.async_get_last_state = AsyncMock(return_value=last_state)

    with (
        patch(
            "homeassistant.helpers.restore_state.RestoreEntity.async_added_to_hass",
            new_callable=AsyncMock,
        ),
        patch(
            "homeassistant.helpers.update_coordinator.CoordinatorEntity.async_added_to_hass",
            new_callable=AsyncMock,
        ),
    ):
        await entity.async_added_to_hass()

    assert coordinator.get_control_0_10v(MOCK_DID) is False


@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_local_switch_no_restore_when_unavailable(
    coordinator, expected_lingering_timers
):
    """async_added_to_hass skips restore when last state is 'unavailable'."""
    from unittest.mock import AsyncMock, MagicMock

    from custom_components.aquamedic.switch import (
        AquaMedicLocalSwitchEntity,
        AquaMedicSwitchDescription,
        _SwitchKind,
    )

    desc = AquaMedicSwitchDescription(
        key="control_0_10v",
        translation_key="control_0_10v",
        attr="",
        kind=_SwitchKind.LOCAL,
        icon="mdi:tune-variant",
        icon_off="mdi:tune-variant",
    )
    entity = AquaMedicLocalSwitchEntity(coordinator, MOCK_DID, desc)

    last_state = MagicMock()
    last_state.state = "unavailable"
    entity.async_get_last_state = AsyncMock(return_value=last_state)

    with patch(
        "homeassistant.helpers.restore_state.RestoreEntity.async_added_to_hass",
        new_callable=AsyncMock,
    ):
        await entity.async_added_to_hass()

    # Should remain False (default)
    assert coordinator.get_control_0_10v(MOCK_DID) is False


async def test_local_switch_no_restore_when_none(coordinator):
    """async_added_to_hass skips restore when last_state is None."""
    from unittest.mock import AsyncMock

    from custom_components.aquamedic.switch import (
        AquaMedicLocalSwitchEntity,
        AquaMedicSwitchDescription,
        _SwitchKind,
    )

    desc = AquaMedicSwitchDescription(
        key="control_0_10v",
        translation_key="control_0_10v",
        attr="",
        kind=_SwitchKind.LOCAL,
        icon="mdi:tune-variant",
        icon_off="mdi:tune-variant",
    )
    entity = AquaMedicLocalSwitchEntity(coordinator, MOCK_DID, desc)
    entity.async_get_last_state = AsyncMock(return_value=None)

    with (
        patch(
            "homeassistant.helpers.restore_state.RestoreEntity.async_added_to_hass",
            new_callable=AsyncMock,
        ),
        patch(
            "homeassistant.helpers.update_coordinator.CoordinatorEntity.async_added_to_hass",
            new_callable=AsyncMock,
        ),
    ):
        await entity.async_added_to_hass()

    assert coordinator.get_control_0_10v(MOCK_DID) is False
