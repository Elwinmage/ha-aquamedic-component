"""Tests for doser.py — Reefdoser EVO 5 dose-table codec."""

from __future__ import annotations

import base64

import pytest

from custom_components.aquamedic.doser import (
    CHANNELS,
    DOSE_SLOT_COUNT,
    DOSE_TABLE_LEN,
    MAX_AMOUNT_ML,
    build_control_payload,
    daily_total_ml,
    decode_table,
    encode_table,
    has_table,
    interval_attr,
    normalize_doses,
    run_attr,
    table_attr,
    timer_attr,
)
from custom_components.aquamedic.schedule import ScheduleError

# Channel 1 of the capture reported with the datapoint list: one dose of 2 ml
# at 15:15 (raw amount 00 02), every other slot empty.
CAPTURE_CH1 = "0f0f0002" + "00" * (DOSE_TABLE_LEN - 4)


# ── Attribute names ───────────────────────────────────────────────────────────


def test_attribute_names_follow_the_firmware_spelling():
    assert [table_attr(c) for c in CHANNELS] == [
        "CH1SWTime",
        "CH2SWTime",
        "CH3SWTime",
        "CH4SWTime",
        "CH5SWTime",
    ]
    assert timer_attr(3) == "Timer3ON"
    assert interval_attr(5) == "IntervalT5"
    # "channe<n>" is not a typo of ours: that is how the firmware spells it.
    assert run_attr(2) == "channe2"


@pytest.mark.parametrize("channel", [0, 6, -1])
def test_channel_out_of_range_is_refused(channel):
    with pytest.raises(ScheduleError, match="outside 1-5"):
        table_attr(channel)


def test_has_table():
    assert has_table({"CH2SWTime": "00"}, 2)
    assert not has_table({"CH2SWTime": "00"}, 1)
    assert not has_table(None, 1)


# ── Decoding ──────────────────────────────────────────────────────────────────


def test_decode_the_real_capture():
    assert decode_table(CAPTURE_CH1) == [
        {"slot": 0, "time": 15 * 60 + 15, "amount_ml": 2}
    ]


def test_decode_blank_table_has_no_dose():
    assert decode_table("00" * DOSE_TABLE_LEN) == []


def test_decode_sorts_by_time_and_reads_a_16_bit_amount():
    data = bytearray(DOSE_TABLE_LEN)
    data[0:4] = bytes([21, 0, 0x01, 0x2C])  # 21:00, 300 ml
    data[4:8] = bytes([8, 30, 0, 5])  # 08:30, 5 ml
    assert decode_table(data.hex()) == [
        {"slot": 1, "time": 8 * 60 + 30, "amount_ml": 5},
        {"slot": 0, "time": 21 * 60, "amount_ml": 300},
    ]
    assert daily_total_ml(decode_table(data.hex())) == 305


def test_decode_accepts_base64_and_byte_lists():
    raw = bytes.fromhex(CAPTURE_CH1)
    expected = decode_table(CAPTURE_CH1)
    assert decode_table(base64.b64encode(raw).decode()) == expected
    assert decode_table(list(raw)) == expected


@pytest.mark.parametrize("raw", [None, "", "zz", "0f0f0002", 42, ["x"]])
def test_decode_unreadable_value_gives_no_dose(raw):
    assert decode_table(raw) == []


# ── Encoding ──────────────────────────────────────────────────────────────────


def test_encode_round_trips_the_capture():
    doses = normalize_doses([{"time": "15:15", "amount_ml": 2}])
    assert encode_table(doses) == CAPTURE_CH1


def test_encode_sorts_and_zeroes_unused_slots():
    doses = normalize_doses(
        [
            {"time": 21 * 60, "amount_ml": 300},
            {"time": "08:30", "amount_ml": 5},
        ]
    )
    encoded = encode_table(doses)
    assert len(encoded) == DOSE_TABLE_LEN * 2
    assert encoded == "081e0005" + "1500012c" + "00" * (DOSE_TABLE_LEN - 8)
    assert decode_table(encoded) == [
        {"slot": 0, "time": 510, "amount_ml": 5},
        {"slot": 1, "time": 1260, "amount_ml": 300},
    ]


def test_empty_list_clears_the_table():
    assert encode_table(normalize_doses([])) == "00" * DOSE_TABLE_LEN


# ── Validation ────────────────────────────────────────────────────────────────


def test_too_many_doses_is_refused():
    doses = [{"time": i, "amount_ml": 1} for i in range(DOSE_SLOT_COUNT + 1)]
    with pytest.raises(ScheduleError, match="too many doses"):
        normalize_doses(doses)


def test_24_doses_are_accepted():
    doses = [{"time": i * 10, "amount_ml": 1} for i in range(DOSE_SLOT_COUNT)]
    assert len(normalize_doses(doses)) == DOSE_SLOT_COUNT


def test_non_mapping_dose_is_refused():
    with pytest.raises(ScheduleError, match="not a mapping"):
        normalize_doses(["15:15"])  # type: ignore[list-item]


@pytest.mark.parametrize("amount", [0, -3, MAX_AMOUNT_ML + 1])
def test_amount_out_of_range_is_refused(amount):
    with pytest.raises(ScheduleError, match="amount_ml"):
        normalize_doses([{"time": "10:00", "amount_ml": amount}])


@pytest.mark.parametrize("amount", [None, "abc"])
def test_amount_not_a_number_is_refused(amount):
    with pytest.raises(ScheduleError, match="invalid value"):
        normalize_doses([{"time": "10:00", "amount_ml": amount}])


def test_invalid_time_is_refused():
    with pytest.raises(ScheduleError, match="time"):
        normalize_doses([{"time": "25:00", "amount_ml": 1}])


def test_two_doses_in_the_same_minute_are_refused():
    with pytest.raises(ScheduleError, match="two doses at 10:00"):
        normalize_doses(
            [{"time": "10:00", "amount_ml": 1}, {"time": 600, "amount_ml": 2}]
        )


# ── Control payload ───────────────────────────────────────────────────────────


def test_payload_targets_the_channel_attribute():
    payload = build_control_payload(3, [{"time": "15:15", "amount_ml": 2}])
    assert payload == {"CH3SWTime": CAPTURE_CH1}


def test_payload_is_empty_when_the_pump_already_holds_the_table():
    attrs = {"CH1SWTime": CAPTURE_CH1.upper()}
    assert build_control_payload(1, [{"time": "15:15", "amount_ml": 2}], attrs) == {}


def test_payload_is_sent_when_the_table_differs():
    attrs = {"CH1SWTime": "00" * DOSE_TABLE_LEN}
    assert build_control_payload(1, [{"time": "15:15", "amount_ml": 2}], attrs) == {
        "CH1SWTime": CAPTURE_CH1
    }
