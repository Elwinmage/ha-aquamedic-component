"""Time-slot scheduler codec for Aqua Medic / Gizwits pumps.

Both firmwares expose the same scheduler shape: 48 ``AutoTimeNN`` binary
datapoints (``AutoTime00`` … ``AutoTime47``), one per time slot, honoured by
the pump while its ``TimerON`` switch is on. Only the slot layout differs
(see the captures under ``scripts/devices_datapoints/``):

DC Runner series (return pump and skimmer) — 6 bytes per slot::

    Byte0 start hour   Byte1 start minute
    Byte2 end hour     Byte3 end minute
    Byte4 mode         0 stop, 1 auto, 2 feeding
    Byte5 value        speed in % (auto) or pause in minutes (feeding),
                       0 when stopped

SmartDrift / EcoDrift — 8 bytes per slot::

    Byte0..3           same start / end as above
    Byte4 mode         0 stop, 1 classic wave, 2 sine wave, 3 random wave,
                       4 constant flow, 5 feeding
    Byte5 value        flow in % or feeding time in minutes, 0 when stopped
    Byte6 frequency    in %
    Byte7 pulse/tide   0 pulse, 1 tide

This module is pure (no Home Assistant import) so the wire format can be
tested on its own. Times are exchanged as minutes since midnight, the same
convention as the schedules of ha-reefbeat-component, which lets ha-reef-card
draw both with the same maths.

Wire encoding: the Gizwits Open API carries a binary datapoint as a hex
string padded to the datapoint length. Reading is deliberately lenient (hex,
base64 or a list of byte values) because the AEP and Gateway endpoints are
not documented on that point; writing always uses the documented hex form.
"""

from __future__ import annotations

import base64
import binascii
import re
from dataclasses import dataclass
from itertools import pairwise
from typing import Any, Final

from .const import (
    DC_RUNNER_SERIES_PRODUCT_KEY,
    SMARTDRIFT_PRODUCT_KEY,
)

SLOT_COUNT: Final[int] = 48
SLOT_ATTR_TPL: Final[str] = "AutoTime{index:02d}"

MINUTES_PER_DAY: Final[int] = 24 * 60
# The device stores an end time as hour/minute: 23:59 is the last one that is
# unambiguous on every firmware (24:00 is not guaranteed to be accepted).
MAX_MINUTE: Final[int] = MINUTES_PER_DAY - 1

KIND_RUNNER: Final[str] = "runner"
KIND_DRIFT: Final[str] = "drift"

MODE_STOP: Final[str] = "stop"
MODE_FEEDING: Final[str] = "feeding"

_HEX_RE: Final[re.Pattern[str]] = re.compile(r"^[0-9a-fA-F]*$")


class ScheduleError(ValueError):
    """Raised when a schedule cannot be encoded for the device."""


@dataclass(frozen=True, slots=True)
class ScheduleLayout:
    """Slot layout of one firmware family."""

    kind: str
    slot_len: int
    # Index in this tuple is the mode byte on the wire.
    modes: tuple[str, ...]
    # Upper bound of the value byte for a running mode (percentage).
    max_value: int = 100
    # Upper bound of the value byte in feeding mode (minutes).
    max_feed_minutes: int = 60
    # Lowest speed the motor accepts while running, 0 when unconstrained.
    min_value: int = 0
    has_frequency: bool = False


LAYOUT_RUNNER: Final[ScheduleLayout] = ScheduleLayout(
    kind=KIND_RUNNER,
    slot_len=6,
    modes=(MODE_STOP, "auto", MODE_FEEDING),
    # Below 30 % the DC Runner motor may stall (see number.py).
    min_value=30,
)

LAYOUT_DRIFT: Final[ScheduleLayout] = ScheduleLayout(
    kind=KIND_DRIFT,
    slot_len=8,
    modes=(
        MODE_STOP,
        "classic_wave",
        "sine_wave",
        "random_wave",
        "constant_flow",
        MODE_FEEDING,
    ),
    has_frequency=True,
)

_LAYOUTS: Final[dict[str, ScheduleLayout]] = {
    DC_RUNNER_SERIES_PRODUCT_KEY: LAYOUT_RUNNER,
    SMARTDRIFT_PRODUCT_KEY: LAYOUT_DRIFT,
}


def layout_for(product_key: str | None) -> ScheduleLayout | None:
    """Return the slot layout of a product, None when it has no scheduler."""
    if product_key is None:
        return None
    return _LAYOUTS.get(product_key)


def slot_attr(index: int) -> str:
    """Return the Gizwits attribute name of slot *index* (0-based)."""
    return SLOT_ATTR_TPL.format(index=index)


# =============================================================================
# Decoding
# =============================================================================


def _to_bytes(raw: Any, length: int) -> bytes | None:
    """Convert one raw datapoint value to exactly *length* bytes.

    Returns None when the value is absent or not understood, so a firmware
    answering in an unexpected shape yields an empty slot rather than a crash.
    """
    data: bytes | None = None
    if isinstance(raw, (bytes, bytearray)):
        data = bytes(raw)
    elif isinstance(raw, (list, tuple)):
        try:
            data = bytes(int(b) & 0xFF for b in raw)
        except (TypeError, ValueError):
            return None
    elif isinstance(raw, str):
        text = raw.strip()
        if text.lower().startswith("0x"):
            text = text[2:]
        if len(text) == length * 2 and _HEX_RE.match(text):
            data = bytes.fromhex(text)
        else:
            try:
                data = base64.b64decode(text, validate=True)
            except (binascii.Error, ValueError):
                return None
    if data is None or len(data) != length:
        return None
    return data


def decode_slot(raw: Any, layout: ScheduleLayout, index: int) -> dict[str, Any] | None:
    """Decode one ``AutoTimeNN`` value.

    Returns None for an unused slot. A slot is unused when it is blank or
    when its start and end are equal: the firmware has no "enabled" flag, an
    empty window is how the app clears a slot.
    """
    data = _to_bytes(raw, layout.slot_len)
    if data is None:
        return None
    start = data[0] * 60 + data[1]
    end = data[2] * 60 + data[3]
    if start == end:
        return None
    mode_idx = data[4]
    mode = layout.modes[mode_idx] if mode_idx < len(layout.modes) else MODE_STOP
    slot: dict[str, Any] = {
        "slot": index,
        "start": start,
        "end": end,
        "mode": mode,
        "value": data[5],
    }
    if layout.has_frequency:
        slot["frequency"] = data[6]
        slot["tide"] = bool(data[7])
    return slot


def decode_schedule(attrs: dict[str, Any], layout: ScheduleLayout) -> list[dict]:
    """Decode every programmed slot of a device, sorted by start time."""
    slots: list[dict] = []
    for index in range(SLOT_COUNT):
        slot = decode_slot(attrs.get(slot_attr(index)), layout, index)
        if slot is not None:
            slots.append(slot)
    slots.sort(key=lambda s: (s["start"], s["slot"]))
    return slots


def has_schedule(attrs: dict[str, Any] | None) -> bool:
    """Return True when the device reported its scheduler datapoints."""
    return attrs is not None and slot_attr(0) in attrs


# =============================================================================
# Encoding
# =============================================================================


def parse_minutes(value: Any, field: str) -> int:
    """Read a time of day given as minutes since midnight or as "HH:MM"."""
    if isinstance(value, bool):
        raise ScheduleError(f"{field}: invalid time {value!r}")
    if isinstance(value, (int, float)):
        minutes = int(value)
    elif isinstance(value, str):
        parts = value.strip().split(":")
        try:
            if len(parts) == 1:
                minutes = int(parts[0])
            elif len(parts) in (2, 3):
                minutes = int(parts[0]) * 60 + int(parts[1])
            else:
                raise ValueError(value)
        except ValueError as exc:
            raise ScheduleError(f"{field}: invalid time {value!r}") from exc
    else:
        raise ScheduleError(f"{field}: invalid time {value!r}")
    if not 0 <= minutes <= MAX_MINUTE:
        raise ScheduleError(f"{field}: {value!r} is outside 00:00-23:59")
    return minutes


def _bounded_int(value: Any, field: str, low: int, high: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise ScheduleError(f"{field}: invalid value {value!r}") from exc
    if not low <= number <= high:
        raise ScheduleError(f"{field}: {number} is outside {low}-{high}")
    return number


def normalize_slots(slots: list[dict[str, Any]], layout: ScheduleLayout) -> list[dict]:
    """Validate user slots and return them sorted, ready to encode.

    Overlaps and windows crossing midnight are refused rather than guessed:
    the firmware behaviour is undocumented for both, and a pump running the
    wrong program is worse than an explicit error. A window crossing midnight
    is written as two slots.
    """
    if len(slots) > SLOT_COUNT:
        raise ScheduleError(f"too many slots: {len(slots)} (max {SLOT_COUNT})")

    result: list[dict] = []
    for pos, raw in enumerate(slots):
        if not isinstance(raw, dict):
            raise ScheduleError(f"slot {pos}: not a mapping")
        where = f"slot {pos}"
        start = parse_minutes(raw.get("start"), f"{where} start")
        end = parse_minutes(raw.get("end"), f"{where} end")
        if end <= start:
            raise ScheduleError(
                f"{where}: end must be after start (split a slot crossing midnight)"
            )
        mode = raw.get("mode", layout.modes[1])
        if mode not in layout.modes:
            raise ScheduleError(
                f"{where}: unknown mode {mode!r} (expected {', '.join(layout.modes)})"
            )
        if mode == MODE_STOP:
            value = 0
        elif mode == MODE_FEEDING:
            value = _bounded_int(
                raw.get("value", 1), f"{where} value", 1, layout.max_feed_minutes
            )
        else:
            value = _bounded_int(
                raw.get("value", layout.max_value),
                f"{where} value",
                layout.min_value,
                layout.max_value,
            )
        slot: dict[str, Any] = {
            "start": start,
            "end": end,
            "mode": mode,
            "value": value,
        }
        if layout.has_frequency:
            slot["frequency"] = _bounded_int(
                raw.get("frequency", 0), f"{where} frequency", 0, 100
            )
            slot["tide"] = bool(raw.get("tide", False))
        result.append(slot)

    result.sort(key=lambda s: s["start"])
    for previous, current in pairwise(result):
        if current["start"] < previous["end"]:
            raise ScheduleError(
                "slots overlap: "
                f"{format_minutes(previous['start'])}-{format_minutes(previous['end'])}"
                f" and {format_minutes(current['start'])}-{format_minutes(current['end'])}"
            )
    return result


def format_minutes(minutes: int) -> str:
    """Format minutes since midnight as HH:MM."""
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def encode_slot(slot: dict[str, Any] | None, layout: ScheduleLayout) -> str:
    """Encode one normalized slot as the hex string the Open API expects.

    None encodes a blank (unused) slot.
    """
    data = bytearray(layout.slot_len)
    if slot is not None:
        data[0], data[1] = divmod(slot["start"], 60)
        data[2], data[3] = divmod(slot["end"], 60)
        data[4] = layout.modes.index(slot["mode"])
        data[5] = slot["value"]
        if layout.has_frequency:
            data[6] = slot["frequency"]
            data[7] = 1 if slot["tide"] else 0
    return data.hex()


def build_control_payload(
    slots: list[dict[str, Any]],
    layout: ScheduleLayout,
    current_attrs: dict[str, Any] | None = None,
) -> dict[str, str]:
    """Return the ``AutoTimeNN`` attributes to send for a whole schedule.

    The schedule is always rewritten as a whole: the given slots fill
    ``AutoTime00`` onwards in chronological order and every remaining slot is
    blanked, so a slot removed in the UI cannot survive on the device. Slots
    already holding the right bytes are left out of the payload.
    """
    normalized = normalize_slots(slots, layout)
    current_attrs = current_attrs or {}
    payload: dict[str, str] = {}
    for index in range(SLOT_COUNT):
        slot = normalized[index] if index < len(normalized) else None
        encoded = encode_slot(slot, layout)
        attr = slot_attr(index)
        current = _to_bytes(current_attrs.get(attr), layout.slot_len)
        if current is not None and current.hex() == encoded:
            continue
        payload[attr] = encoded
    return payload
