"""Tests for schedule.py — AutoTimeNN codec (pure, no Home Assistant)."""

from __future__ import annotations

import base64

import pytest

from custom_components.aquamedic.const import (
    DC_RUNNER_PRODUCT_KEY,
    DC_RUNNER_SERIES_PRODUCT_KEY,
    SMARTDRIFT_PRODUCT_KEY,
)
from custom_components.aquamedic.schedule import (
    LAYOUT_DRIFT,
    LAYOUT_RUNNER,
    SLOT_COUNT,
    ScheduleError,
    build_control_payload,
    decode_schedule,
    decode_slot,
    encode_slot,
    format_minutes,
    has_schedule,
    layout_for,
    normalize_slots,
    parse_minutes,
    slot_attr,
)

# 08:00 → 12:30, auto, 60 %
RUNNER_SLOT_HEX = "08000c1e013c"
# 08:00 → 12:30, sine wave, flow 60 %, frequency 40 %, tide
DRIFT_SLOT_HEX = "08000c1e023c2801"


# ── Layout lookup ─────────────────────────────────────────────────────────────


def test_layout_for_known_products():
    assert layout_for(DC_RUNNER_SERIES_PRODUCT_KEY) is LAYOUT_RUNNER
    assert layout_for(SMARTDRIFT_PRODUCT_KEY) is LAYOUT_DRIFT


def test_layout_for_products_without_scheduler():
    # The speculative legacy DC Runner key has no captured schedule datapoints.
    assert layout_for(DC_RUNNER_PRODUCT_KEY) is None
    assert layout_for(None) is None
    assert layout_for("unknown") is None


def test_slot_attr_is_zero_padded():
    assert slot_attr(0) == "AutoTime00"
    assert slot_attr(47) == "AutoTime47"


# ── Decoding ──────────────────────────────────────────────────────────────────


def test_decode_runner_slot_from_hex():
    assert decode_slot(RUNNER_SLOT_HEX, LAYOUT_RUNNER, 3) == {
        "slot": 3,
        "start": 480,
        "end": 750,
        "mode": "auto",
        "value": 60,
    }


def test_decode_drift_slot_from_hex():
    assert decode_slot(DRIFT_SLOT_HEX, LAYOUT_DRIFT, 0) == {
        "slot": 0,
        "start": 480,
        "end": 750,
        "mode": "sine_wave",
        "value": 60,
        "frequency": 40,
        "tide": True,
    }


@pytest.mark.parametrize(
    "raw",
    [
        RUNNER_SLOT_HEX.upper(),
        "0x" + RUNNER_SLOT_HEX,
        f"  {RUNNER_SLOT_HEX}  ",
        base64.b64encode(bytes.fromhex(RUNNER_SLOT_HEX)).decode(),
        list(bytes.fromhex(RUNNER_SLOT_HEX)),
        tuple(bytes.fromhex(RUNNER_SLOT_HEX)),
        bytes.fromhex(RUNNER_SLOT_HEX),
        bytearray.fromhex(RUNNER_SLOT_HEX),
    ],
)
def test_decode_accepts_every_wire_shape(raw):
    slot = decode_slot(raw, LAYOUT_RUNNER, 0)
    assert slot is not None
    assert (slot["start"], slot["end"], slot["mode"], slot["value"]) == (
        480,
        750,
        "auto",
        60,
    )


@pytest.mark.parametrize(
    "raw",
    [
        None,
        "",
        "zz",  # neither hex nor base64
        "0800",  # too short
        RUNNER_SLOT_HEX + "00",  # too long for a 6-byte slot
        ["a", "b", "c", "d", "e", "f"],  # not byte values
        42,  # unsupported type
        "000000000000",  # blank slot
        "08000800013c",  # start == end → unused
    ],
)
def test_decode_returns_none_for_unusable_values(raw):
    assert decode_slot(raw, LAYOUT_RUNNER, 0) is None


def test_decode_unknown_mode_falls_back_to_stop():
    slot = decode_slot("08000c1e093c", LAYOUT_RUNNER, 0)
    assert slot is not None and slot["mode"] == "stop"


def test_decode_schedule_sorts_by_start_and_skips_blanks():
    attrs = {slot_attr(i): "000000000000" for i in range(SLOT_COUNT)}
    attrs[slot_attr(0)] = "140016000250"  # 20:00-22:00 feeding 80
    attrs[slot_attr(5)] = RUNNER_SLOT_HEX
    schedule = decode_schedule(attrs, LAYOUT_RUNNER)
    assert [s["slot"] for s in schedule] == [5, 0]
    assert schedule[1]["mode"] == "feeding"


def test_has_schedule():
    assert has_schedule({slot_attr(0): "00"}) is True
    assert has_schedule({"SwitchON": 1}) is False
    assert has_schedule({}) is False
    assert has_schedule(None) is False


# ── Time parsing ──────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("value", "expected"),
    [(0, 0), (480, 480), (480.0, 480), ("08:00", 480), ("8:30:00", 510), ("90", 90)],
)
def test_parse_minutes(value, expected):
    assert parse_minutes(value, "start") == expected


@pytest.mark.parametrize(
    "value", [True, None, [], "abc", "1:2:3:4", "aa:bb", -1, 1440, "24:00"]
)
def test_parse_minutes_rejects_invalid(value):
    with pytest.raises(ScheduleError):
        parse_minutes(value, "start")


def test_format_minutes():
    assert format_minutes(0) == "00:00"
    assert format_minutes(750) == "12:30"


# ── Normalisation ─────────────────────────────────────────────────────────────


def test_normalize_sorts_and_applies_defaults():
    slots = normalize_slots(
        [
            {"start": "12:00", "end": "13:00"},
            {"start": 60, "end": 120, "mode": "stop", "value": 80},
            {"start": "06:00", "end": "06:10", "mode": "feeding"},
        ],
        LAYOUT_RUNNER,
    )
    assert slots == [
        # value is forced to 0 when the pump is stopped
        {"start": 60, "end": 120, "mode": "stop", "value": 0},
        # feeding defaults to one minute
        {"start": 360, "end": 370, "mode": "feeding", "value": 1},
        # default mode is the first running one, at full speed
        {"start": 720, "end": 780, "mode": "auto", "value": 100},
    ]


def test_normalize_drift_adds_frequency_and_tide():
    slots = normalize_slots(
        [
            {
                "start": 0,
                "end": 60,
                "mode": "sine_wave",
                "value": 10,
                "frequency": 30,
                "tide": 1,
            },
            {"start": 60, "end": 120, "mode": "constant_flow", "value": 0},
        ],
        LAYOUT_DRIFT,
    )
    assert slots[0]["frequency"] == 30 and slots[0]["tide"] is True
    # A SmartDrift has no minimum flow, and frequency / tide default to off.
    assert slots[1] == {
        "start": 60,
        "end": 120,
        "mode": "constant_flow",
        "value": 0,
        "frequency": 0,
        "tide": False,
    }


@pytest.mark.parametrize(
    "slots",
    [
        ["not a dict"],
        [{"start": 60, "end": 60}],  # empty window
        [{"start": 120, "end": 60}],  # crosses midnight
        [{"start": 0, "end": 60, "mode": "sine_wave"}],  # not a runner mode
        [{"start": 0, "end": 60, "value": 10}],  # below the 30 % motor floor
        [{"start": 0, "end": 60, "value": 101}],
        [{"start": 0, "end": 60, "value": "fast"}],
        [{"start": 0, "end": 60, "mode": "feeding", "value": 0}],
        [{"start": 0, "end": 60, "mode": "feeding", "value": 61}],
        [{"start": 0, "end": 120}, {"start": 60, "end": 180}],  # overlap
        [{"start": i, "end": i + 1} for i in range(SLOT_COUNT + 1)],  # too many
    ],
)
def test_normalize_rejects_invalid(slots):
    with pytest.raises(ScheduleError):
        normalize_slots(slots, LAYOUT_RUNNER)


def test_normalize_rejects_bad_drift_frequency():
    with pytest.raises(ScheduleError):
        normalize_slots(
            [{"start": 0, "end": 60, "frequency": 150}],
            LAYOUT_DRIFT,
        )


def test_normalize_accepts_adjacent_slots():
    slots = normalize_slots(
        [{"start": 0, "end": 60}, {"start": 60, "end": 120}], LAYOUT_RUNNER
    )
    assert len(slots) == 2


# ── Encoding ──────────────────────────────────────────────────────────────────


def test_encode_roundtrip_runner():
    slot = decode_slot(RUNNER_SLOT_HEX, LAYOUT_RUNNER, 0)
    assert encode_slot(slot, LAYOUT_RUNNER) == RUNNER_SLOT_HEX


def test_encode_roundtrip_drift():
    slot = decode_slot(DRIFT_SLOT_HEX, LAYOUT_DRIFT, 0)
    assert encode_slot(slot, LAYOUT_DRIFT) == DRIFT_SLOT_HEX


def test_encode_blank_slot_is_padded_to_the_datapoint_length():
    assert encode_slot(None, LAYOUT_RUNNER) == "00" * 6
    assert encode_slot(None, LAYOUT_DRIFT) == "00" * 8


def test_payload_rewrites_every_slot_when_nothing_is_known():
    payload = build_control_payload(
        [{"start": "08:00", "end": "12:30", "mode": "auto", "value": 60}],
        LAYOUT_RUNNER,
    )
    assert len(payload) == SLOT_COUNT
    assert payload["AutoTime00"] == RUNNER_SLOT_HEX
    assert payload["AutoTime01"] == "00" * 6


def test_payload_only_carries_changed_slots():
    current = {slot_attr(i): "00" * 6 for i in range(SLOT_COUNT)}
    current[slot_attr(0)] = RUNNER_SLOT_HEX
    current[slot_attr(1)] = "140016000250"
    # Same first slot, second one removed.
    payload = build_control_payload(
        [{"start": 480, "end": 750, "mode": "auto", "value": 60}],
        LAYOUT_RUNNER,
        current,
    )
    assert payload == {"AutoTime01": "00" * 6}


def test_payload_empty_when_program_is_unchanged():
    current = {slot_attr(i): "00" * 6 for i in range(SLOT_COUNT)}
    assert build_control_payload([], LAYOUT_RUNNER, current) == {}


def test_payload_propagates_validation_errors():
    with pytest.raises(ScheduleError):
        build_control_payload([{"start": 10, "end": 5}], LAYOUT_RUNNER)
