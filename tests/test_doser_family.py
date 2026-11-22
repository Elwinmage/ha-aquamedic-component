"""A dosing pump with fewer channels (the EVO 3) is handled like the EVO 5."""

from __future__ import annotations

import pytest

from custom_components.aquamedic.binary_sensor import (
    async_setup_entry as binary_sensor_setup,
)
from custom_components.aquamedic.button import async_setup_entry as button_setup
from custom_components.aquamedic.const import REEFDOSER_EVO5_PRODUCT_KEY
from custom_components.aquamedic.coordinator import AquaMedicDeviceData
from custom_components.aquamedic.doser import (
    DOSE_TABLE_LEN,
    channel_count,
    channels_of,
)
from custom_components.aquamedic.entity import build_device_info, resolve_model
from custom_components.aquamedic.number import async_setup_entry as number_setup
from custom_components.aquamedic.select import async_setup_entry as select_setup
from custom_components.aquamedic.sensor import async_setup_entry as sensor_setup
from custom_components.aquamedic.switch import async_setup_entry as switch_setup
from tests.conftest import MOCK_DEVICE_ONLINE
from tests.test_reefdoser import _setup

EVO3_DID = "evo3-did"
# The product key of the EVO 3 is not known yet: it is told by its tables.
EVO3_KEY = "unknown-evo3-product-key"
BLANK = "00" * DOSE_TABLE_LEN
EVO3_ATTRS = {
    "switch": True,
    "CALSet": 1,
    "CH1SWTime": BLANK,
    "CH2SWTime": BLANK,
    "CH3SWTime": BLANK,
}


def _evo3(attrs=None) -> AquaMedicDeviceData:
    return AquaMedicDeviceData(
        {
            **MOCK_DEVICE_ONLINE,
            "did": EVO3_DID,
            "dev_alias": "Reefdoser 3",
            "product_key": EVO3_KEY,
        },
        {"attr": dict(EVO3_ATTRS if attrs is None else attrs)},
    )


@pytest.fixture
def evo3_coordinator(coordinator):
    coordinator.data = {EVO3_DID: _evo3()}
    return coordinator


# ── channel_count ─────────────────────────────────────────────────────────────


def test_a_known_product_has_its_known_channel_count_even_without_data():
    assert channel_count(REEFDOSER_EVO5_PRODUCT_KEY, {}) == 5
    assert channel_count(REEFDOSER_EVO5_PRODUCT_KEY, None) == 5


@pytest.mark.parametrize(
    ("tables", "expected"),
    [
        ((), 0),
        ((1,), 1),
        ((1, 2, 3), 3),
        # A gap ends the count: channel 3 alone does not make three channels.
        ((1, 3), 1),
        ((3,), 0),
        ((1, 2, 3, 4, 5), 5),
        ((1, 2, 3, 4, 5, 6), 5),
    ],
)
def test_an_unknown_product_is_counted_from_its_tables(tables, expected):
    attrs = {f"CH{n}SWTime": BLANK for n in tables}
    assert channel_count(EVO3_KEY, attrs) == expected


def test_a_device_without_data_is_not_a_doser():
    assert channel_count(EVO3_KEY, None) == 0
    assert channel_count(None, {"Flow": 30}) == 0


def test_channels_of():
    assert channels_of(0) == ()
    assert channels_of(3) == (1, 2, 3)


# ── Identity ──────────────────────────────────────────────────────────────────


def test_model_follows_the_channel_count():
    assert resolve_model(EVO3_KEY, 3) == "Reefdoser EVO 3"
    assert resolve_model(REEFDOSER_EVO5_PRODUCT_KEY, 5) == "Reefdoser EVO 5"
    assert resolve_model(EVO3_KEY) == "SmartDrift"


def test_device_info_of_a_three_channel_pump(evo3_coordinator):
    assert build_device_info(evo3_coordinator, EVO3_DID)["model"] == "Reefdoser EVO 3"


# ── Platforms ─────────────────────────────────────────────────────────────────


async def test_switches(hass, evo3_coordinator):
    added = await _setup(switch_setup, hass, evo3_coordinator)
    ids = {e.unique_id for e in added}
    # power + calibration + 3 manual runs + 3 schedule switches
    assert len(added) == 8
    assert f"{EVO3_DID}_doser_run_3" in ids
    assert f"{EVO3_DID}_doser_timer_3" in ids
    assert f"{EVO3_DID}_doser_run_4" not in ids


async def test_numbers(hass, evo3_coordinator):
    added = await _setup(number_setup, hass, evo3_coordinator)
    assert len(added) == 4  # 3 intervals + calibration amount


async def test_the_calibration_channel_offers_three_channels(hass, evo3_coordinator):
    (select,) = await _setup(select_setup, hass, evo3_coordinator)
    assert select.options == ["channel_1", "channel_2", "channel_3"]
    assert select.current_option == "channel_2"


async def test_binary_sensors_and_button(hass, evo3_coordinator):
    faults = await _setup(binary_sensor_setup, hass, evo3_coordinator)
    assert len(faults) == 2
    buttons = await _setup(button_setup, hass, evo3_coordinator)
    assert [e.unique_id for e in buttons] == [f"{EVO3_DID}_refresh"]


async def test_schedule_sensors(hass, evo3_coordinator):
    added = await _setup(sensor_setup, hass, evo3_coordinator)
    assert {e.unique_id for e in added} == {
        *(f"{EVO3_DID}_doser_schedule_{c}" for c in (1, 2, 3)),
        f"{EVO3_DID}_calibration_time",
    }


async def test_a_device_without_tables_gets_no_doser_entities(hass, coordinator):
    coordinator.data = {EVO3_DID: _evo3({"switch": True})}
    assert await _setup(switch_setup, hass, coordinator) == []
    assert await _setup(number_setup, hass, coordinator) == []
    assert await _setup(select_setup, hass, coordinator) == []
