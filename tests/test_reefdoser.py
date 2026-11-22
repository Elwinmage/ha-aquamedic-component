"""Tests for the Reefdoser EVO 5 entities and the set_doser_schedule service."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.aquamedic.binary_sensor import (
    REEFDOSER_FAULT_DESCRIPTIONS,
    AquaMedicFaultEntity,
)
from custom_components.aquamedic.binary_sensor import (
    async_setup_entry as binary_sensor_setup,
)
from custom_components.aquamedic.button import async_setup_entry as button_setup
from custom_components.aquamedic.client import AquaMedicConnectionError
from custom_components.aquamedic.const import (
    DOMAIN,
    REEFDOSER_EVO5_PRODUCT_KEY,
)
from custom_components.aquamedic.coordinator import AquaMedicDeviceData
from custom_components.aquamedic.doser import DOSE_TABLE_LEN
from custom_components.aquamedic.entity import build_device_info, resolve_model
from custom_components.aquamedic.number import (
    REEFDOSER_NUMBER_DESCRIPTIONS,
    AquaMedicNumberEntity,
)
from custom_components.aquamedic.number import async_setup_entry as number_setup
from custom_components.aquamedic.select import (
    REEFDOSER_SELECT_DESCRIPTIONS,
    AquaMedicSelectEntity,
)
from custom_components.aquamedic.select import async_setup_entry as select_setup
from custom_components.aquamedic.sensor import (
    CALIBRATION_TIME_DESCRIPTION,
    AquaMedicDoserCalibrationTimeSensor,
    AquaMedicDoserScheduleSensor,
)
from custom_components.aquamedic.sensor import async_setup_entry as sensor_setup
from custom_components.aquamedic.services import (
    SERVICE_SET_DOSER_SCHEDULE,
    async_register_services,
    async_unregister_services,
)
from custom_components.aquamedic.switch import (
    REEFDOSER_SWITCH_DESCRIPTIONS,
    AquaMedicSwitchEntity,
)
from custom_components.aquamedic.switch import async_setup_entry as switch_setup
from tests.conftest import MOCK_DEVICE_ONLINE, MOCK_DID

DOSER_DID = "doser-did"
CH1_TABLE = "0f0f0002" + "00" * (DOSE_TABLE_LEN - 4)
BLANK = "00" * DOSE_TABLE_LEN

# Values of the status read verified against the app (see the datapoint list).
DOSER_ATTRS = {
    "switch": True,
    "channe1": False,
    "channe2": True,
    "Timer1ON": True,
    "Timer2ON": False,
    "CALSW": False,
    "CALSet": 2,
    "IntervalT1": 0,
    "IntervalT2": 3,
    "Calib1": 50,
    "CH1SWTime": CH1_TABLE,
    "CH2SWTime": BLANK,
    "time1": 12,
    "OpenCircuit": False,
    "Fault_UART": True,
}
DOSER_DEVICE = {
    **MOCK_DEVICE_ONLINE,
    "did": DOSER_DID,
    "dev_alias": "Reefdoser",
    "product_key": REEFDOSER_EVO5_PRODUCT_KEY,
}


def _doser(attrs=None, **device) -> AquaMedicDeviceData:
    return AquaMedicDeviceData(
        {**DOSER_DEVICE, **device},
        {"attr": dict(DOSER_ATTRS if attrs is None else attrs)},
    )


@pytest.fixture
def doser_coordinator(coordinator):
    coordinator.data = {DOSER_DID: _doser()}
    return coordinator


def _entry(hass, coordinator) -> MagicMock:
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "doser-entry"
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    return entry


async def _setup(platform_setup, hass, coordinator) -> list:
    added: list = []
    await platform_setup(
        hass, _entry(hass, coordinator), lambda entities, **kw: added.extend(entities)
    )
    return added


# ── Device identity ───────────────────────────────────────────────────────────


def test_model_label():
    assert resolve_model(REEFDOSER_EVO5_PRODUCT_KEY) == "Reefdoser EVO 5"


def test_device_info_uses_the_model(doser_coordinator):
    info = build_device_info(doser_coordinator, DOSER_DID)
    assert info["model"] == "Reefdoser EVO 5"
    assert info.get("model_id") is None


# ── Setup of every platform ───────────────────────────────────────────────────


async def test_switch_setup(hass, doser_coordinator):
    added = await _setup(switch_setup, hass, doser_coordinator)
    # power + calibration + 5 manual runs + 5 schedule switches
    assert len(added) == 12
    assert {e.unique_id for e in added} >= {
        f"{DOSER_DID}_power",
        f"{DOSER_DID}_calibration",
        f"{DOSER_DID}_doser_run_5",
        f"{DOSER_DID}_doser_timer_1",
    }


async def test_number_setup(hass, doser_coordinator):
    added = await _setup(number_setup, hass, doser_coordinator)
    assert len(added) == 6  # 5 intervals + calibration amount


async def test_select_setup(hass, doser_coordinator):
    added = await _setup(select_setup, hass, doser_coordinator)
    # No pump role select: the doser is not a DC Runner.
    assert [e.unique_id for e in added] == [f"{DOSER_DID}_calibration_channel"]


async def test_binary_sensor_setup(hass, doser_coordinator):
    added = await _setup(binary_sensor_setup, hass, doser_coordinator)
    assert {e.unique_id for e in added} == {
        f"{DOSER_DID}_open_circuit",
        f"{DOSER_DID}_fault_uart",
    }


async def test_button_setup(hass, doser_coordinator):
    added = await _setup(button_setup, hass, doser_coordinator)
    assert [e.unique_id for e in added] == [f"{DOSER_DID}_refresh"]


async def test_sensor_setup(hass, doser_coordinator):
    added = await _setup(sensor_setup, hass, doser_coordinator)
    assert {e.unique_id for e in added} == {
        *(f"{DOSER_DID}_doser_schedule_{c}" for c in range(1, 6)),
        f"{DOSER_DID}_calibration_time",
    }


# ── Switches ──────────────────────────────────────────────────────────────────


def _switch(coordinator, key: str) -> AquaMedicSwitchEntity:
    desc = next(d for d in REEFDOSER_SWITCH_DESCRIPTIONS if d.key == key)
    return AquaMedicSwitchEntity(coordinator, DOSER_DID, desc)


def test_switch_states(doser_coordinator):
    assert _switch(doser_coordinator, "power").is_on is True
    assert _switch(doser_coordinator, "doser_run_1").is_on is False
    assert _switch(doser_coordinator, "doser_run_2").is_on is True
    assert _switch(doser_coordinator, "doser_timer_1").is_on is True
    assert _switch(doser_coordinator, "doser_timer_3").is_on is None


def test_switch_channel_placeholder(doser_coordinator):
    entity = _switch(doser_coordinator, "doser_timer_4")
    assert entity.entity_description.translation_placeholders == {"channel": "4"}


@pytest.mark.parametrize(
    ("key", "attr"),
    [
        ("power", "switch"),
        ("calibration", "CALSW"),
        ("doser_run_3", "channe3"),
        ("doser_timer_5", "Timer5ON"),
    ],
)
async def test_switch_writes_the_firmware_attribute(doser_coordinator, key, attr):
    doser_coordinator._client.control_device = AsyncMock()
    entity = _switch(doser_coordinator, key)
    await entity.async_turn_on()
    await entity.async_turn_off()
    calls = [c.args for c in doser_coordinator._client.control_device.await_args_list]
    assert calls == [(DOSER_DID, {attr: 1}), (DOSER_DID, {attr: 0})]


# ── Numbers ───────────────────────────────────────────────────────────────────


def _number(coordinator, key: str) -> AquaMedicNumberEntity:
    desc = next(d for d in REEFDOSER_NUMBER_DESCRIPTIONS if d.key == key)
    return AquaMedicNumberEntity(coordinator, DOSER_DID, desc)


async def test_number_values_and_write(doser_coordinator):
    assert _number(doser_coordinator, "doser_interval_2").native_value == 3.0
    assert _number(doser_coordinator, "calibration_amount").native_value == 50.0
    entity = _number(doser_coordinator, "doser_interval_5")
    assert (entity.native_min_value, entity.native_max_value) == (0, 30)
    await entity.async_set_native_value(7)
    doser_coordinator._client.control_device.assert_awaited_with(
        DOSER_DID, {"IntervalT5": 7}
    )


# ── Select ────────────────────────────────────────────────────────────────────


def _select(coordinator) -> AquaMedicSelectEntity:
    return AquaMedicSelectEntity(
        coordinator, DOSER_DID, REEFDOSER_SELECT_DESCRIPTIONS[0]
    )


@pytest.mark.parametrize(
    ("raw", "option"),
    [
        (0, "channel_1"),
        (2, "channel_3"),
        # A number, even as a string, is an index: 4 is the fifth channel.
        ("4", "channel_5"),
        ("校准3", "channel_3"),
    ],
)
def test_calibration_channel_reads_index_or_label(doser_coordinator, raw, option):
    doser_coordinator.data[DOSER_DID].attrs["CALSet"] = raw
    assert _select(doser_coordinator).current_option == option


async def test_calibration_channel_writes_the_index(doser_coordinator):
    await _select(doser_coordinator).async_select_option("channel_5")
    doser_coordinator._client.control_device.assert_awaited_with(
        DOSER_DID, {"CALSet": 4}
    )


# ── Binary sensors ────────────────────────────────────────────────────────────


def test_alerts(doser_coordinator):
    by_key = {
        d.key: AquaMedicFaultEntity(doser_coordinator, DOSER_DID, d)
        for d in REEFDOSER_FAULT_DESCRIPTIONS
    }
    assert by_key["open_circuit"].is_on is False
    assert by_key["fault_uart"].is_on is True


# ── Dose schedule sensor ──────────────────────────────────────────────────────


def _schedule(coordinator, channel=1) -> AquaMedicDoserScheduleSensor:
    return AquaMedicDoserScheduleSensor(coordinator, DOSER_DID, channel)


def test_schedule_sensor_state_and_attributes(doser_coordinator):
    sensor = _schedule(doser_coordinator)
    assert sensor.available
    assert sensor.native_value == 2
    assert sensor.did == DOSER_DID
    assert sensor.channel == 1
    assert sensor.translation_placeholders == {"channel": "1"}
    attrs = sensor.extra_state_attributes
    assert attrs is not None
    assert attrs["schedule"] == [{"slot": 0, "time": 915, "amount_ml": 2}]
    assert attrs["channel"] == 1
    assert attrs["max_slots"] == 24
    assert attrs["timer_on"] is True
    assert attrs["interval"] == 0
    assert attrs["reef_role"] == "doser_schedule"


def test_schedule_sensor_empty_channel(doser_coordinator):
    sensor = _schedule(doser_coordinator, 2)
    assert sensor.native_value == 0
    attrs = sensor.extra_state_attributes
    assert attrs is not None
    assert attrs["schedule"] == []
    assert attrs["timer_on"] is False


def test_schedule_sensor_waits_for_the_table(doser_coordinator):
    sensor = _schedule(doser_coordinator, 3)
    assert not sensor.available
    assert sensor.native_value is None
    attrs = sensor.extra_state_attributes
    assert attrs is not None
    assert attrs["schedule"] == []
    assert attrs["timer_on"] is None
    assert attrs["interval"] is None


def test_schedule_sensor_without_device(doser_coordinator):
    doser_coordinator.data = {}
    assert _schedule(doser_coordinator).native_value is None


def test_schedule_sensor_stays_available_offline(doser_coordinator):
    doser_coordinator.data = {DOSER_DID: _doser(is_online=False)}
    assert _schedule(doser_coordinator).available


# ── Calibration time sensor ───────────────────────────────────────────────────


def _cal_time(coordinator) -> AquaMedicDoserCalibrationTimeSensor:
    return AquaMedicDoserCalibrationTimeSensor(
        coordinator, DOSER_DID, CALIBRATION_TIME_DESCRIPTION
    )


def test_calibration_time_value(doser_coordinator):
    sensor = _cal_time(doser_coordinator)
    assert sensor.available
    assert sensor.native_value == 12


def test_calibration_time_missing(doser_coordinator):
    doser_coordinator.data = {DOSER_DID: _doser({})}
    sensor = _cal_time(doser_coordinator)
    assert not sensor.available
    assert sensor.native_value is None


def test_calibration_time_unavailable_when_offline(doser_coordinator):
    doser_coordinator.data = {DOSER_DID: _doser(is_online=False)}
    assert not _cal_time(doser_coordinator).available


# ── Service ───────────────────────────────────────────────────────────────────

DOSES = [{"time": "15:15", "amount_ml": 2}]


@pytest.fixture
def loaded(hass, doser_coordinator):
    entry = MockConfigEntry(domain=DOMAIN, data={})
    entry.add_to_hass(hass)
    doser_coordinator.data[MOCK_DID] = AquaMedicDeviceData(MOCK_DEVICE_ONLINE, {})
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = doser_coordinator
    async_register_services(hass)

    ent_reg = er.async_get(hass)
    ids = {}
    for channel in (1, 2):
        ids[f"ch{channel}"] = ent_reg.async_get_or_create(
            "sensor",
            DOMAIN,
            f"{DOSER_DID}_doser_schedule_{channel}",
            config_entry=entry,
        ).entity_id
    ids["power"] = ent_reg.async_get_or_create(
        "switch", DOMAIN, f"{DOSER_DID}_power", config_entry=entry
    ).entity_id
    ids["foreign"] = ent_reg.async_get_or_create(
        "sensor", "other", "x_doser_schedule_1"
    ).entity_id
    ids["gone"] = ent_reg.async_get_or_create(
        "sensor", DOMAIN, "ghost_doser_schedule_1", config_entry=entry
    ).entity_id
    return ids


async def _call(hass, **data):
    await hass.services.async_call(
        DOMAIN, SERVICE_SET_DOSER_SCHEDULE, data, blocking=True
    )


async def test_service_registration_is_removed_with_the_integration(hass):
    async_register_services(hass)
    assert hass.services.has_service(DOMAIN, SERVICE_SET_DOSER_SCHEDULE)
    async_unregister_services(hass)
    assert not hass.services.has_service(DOMAIN, SERVICE_SET_DOSER_SCHEDULE)


async def test_set_doser_schedule_writes_the_channel_table(
    hass, doser_coordinator, loaded
):
    await _call(hass, entity_id=loaded["ch2"], doses=DOSES)

    doser_coordinator._client.control_device.assert_awaited_once_with(
        DOSER_DID, {"CH2SWTime": CH1_TABLE}
    )
    doser_coordinator.async_request_refresh.assert_awaited_once()


async def test_set_doser_schedule_accepts_a_program_read_from_the_sensor(
    hass, doser_coordinator, loaded
):
    # The "slot" index of the attribute is ignored, so it can be sent back.
    await _call(
        hass,
        entity_id=loaded["ch2"],
        doses=[{"slot": 0, "time": 915, "amount_ml": 2}],
    )
    doser_coordinator._client.control_device.assert_awaited_once()


async def test_set_doser_schedule_skips_an_up_to_date_channel(
    hass, doser_coordinator, loaded
):
    await _call(hass, entity_id=loaded["ch1"], doses=DOSES)
    doser_coordinator._client.control_device.assert_not_awaited()


async def test_set_doser_schedule_clears_a_channel(hass, doser_coordinator, loaded):
    await _call(hass, entity_id=loaded["ch1"], doses=[])
    doser_coordinator._client.control_device.assert_awaited_once_with(
        DOSER_DID, {"CH1SWTime": BLANK}
    )


@pytest.mark.parametrize("key", ["power", "foreign"])
async def test_set_doser_schedule_refuses_other_entities(hass, loaded, key):
    with pytest.raises(ServiceValidationError, match="not an Aqua Medic dose"):
        await _call(hass, entity_id=loaded[key], doses=DOSES)


async def test_set_doser_schedule_refuses_an_unregistered_entity(hass, loaded):
    with pytest.raises(ServiceValidationError, match="not an Aqua Medic dose"):
        await _call(hass, entity_id="sensor.nothing", doses=DOSES)


async def test_set_doser_schedule_refuses_an_unloaded_device(hass, loaded):
    with pytest.raises(ServiceValidationError, match="not loaded"):
        await _call(hass, entity_id=loaded["gone"], doses=DOSES)


async def test_set_doser_schedule_reports_invalid_doses(
    hass, doser_coordinator, loaded
):
    with pytest.raises(ServiceValidationError, match="Reefdoser"):
        await _call(
            hass, entity_id=loaded["ch2"], doses=[{"time": "10:00", "amount_ml": 0}]
        )
    doser_coordinator._client.control_device.assert_not_awaited()


async def test_set_doser_schedule_validates_before_sending(
    hass, doser_coordinator, loaded
):
    # One valid channel and one that cannot be written: nothing is sent.
    doser_coordinator.data[DOSER_DID].attrs.pop("CH2SWTime")
    with pytest.raises(ServiceValidationError):
        await _call(
            hass,
            entity_id=[loaded["ch2"], loaded["gone"]],
            doses=DOSES,
        )
    doser_coordinator._client.control_device.assert_not_awaited()


async def test_set_doser_schedule_wraps_cloud_errors(hass, doser_coordinator, loaded):
    doser_coordinator._client.control_device = AsyncMock(
        side_effect=AquaMedicConnectionError("down")
    )
    with pytest.raises(HomeAssistantError, match="dose schedule"):
        await _call(hass, entity_id=loaded["ch2"], doses=DOSES)


@pytest.mark.parametrize(
    "data",
    [
        {"doses": DOSES},
        {"entity_id": "sensor.x"},
        {"entity_id": "sensor.x", "doses": [{"time": "10:00"}]},
    ],
)
async def test_set_doser_schedule_schema(hass, loaded, data):
    with pytest.raises(vol.Invalid):
        await _call(hass, **data)
