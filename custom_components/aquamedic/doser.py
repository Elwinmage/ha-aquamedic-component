"""Dose-table codec for the Aqua Medic Reefdoser EVO 5.

The dosing pump has five channels. Each channel owns one binary datapoint
(``CH1SWTime`` … ``CH5SWTime``) holding a table of 24 slots of 4 bytes::

    Byte0 hour   Byte1 minute   Byte2..3 amount in ml (uint16, big endian)

A slot with a zero amount is empty (the app clears a slot by zeroing it).
The pump doses the given amount once a day at the slot time while the
channel timer (``Timer<n>ON``) is on.

This module is pure (no Home Assistant import) so the wire format can be
tested on its own. Times are exchanged as minutes since midnight, like the
pump schedules of schedule.py and of ha-reefbeat-component.

Wire encoding: see schedule.py — reading is lenient (hex, base64 or a list
of byte values), writing always uses the documented hex form padded to the
datapoint length.
"""

from __future__ import annotations

from itertools import pairwise
from typing import Any, Final

from .const import REEFDOSER_EVO5_PRODUCT_KEY
from .schedule import ScheduleError, _to_bytes, format_minutes, parse_minutes

# Most channels a dosing pump has (the EVO 5). Smaller models (the EVO 3) use
# the same datapoint names for their first channels only.
CHANNEL_COUNT: Final[int] = 5
DOSE_SLOT_COUNT: Final[int] = 24
DOSE_SLOT_LEN: Final[int] = 4
DOSE_TABLE_LEN: Final[int] = DOSE_SLOT_COUNT * DOSE_SLOT_LEN
# The amount is a uint16 on the wire.
MAX_AMOUNT_ML: Final[int] = 0xFFFF

CHANNELS: Final[tuple[int, ...]] = tuple(range(1, CHANNEL_COUNT + 1))


# Product keys whose channel count is known. Any other device is recognised
# as a dosing pump by the dose tables it reports (see channel_count()).
KNOWN_PRODUCTS: Final[dict[str, int]] = {REEFDOSER_EVO5_PRODUCT_KEY: 5}


def channel_count(product_key: str | None, attrs: dict[str, Any] | None) -> int:
    """Return how many channels the device dispenses on, 0 if it is not a doser.

    The channel count of a known product comes from the table above. For any
    other product it is the number of consecutive dose tables (``CH1SWTime``,
    ``CH2SWTime`` …) the device reports, so a smaller model of the family is
    handled as soon as the cloud reports its datapoints.
    """
    if product_key in KNOWN_PRODUCTS:
        return KNOWN_PRODUCTS[product_key]
    count = 0
    while count < CHANNEL_COUNT and has_table(attrs, count + 1):
        count += 1
    return count


def channels_of(count: int) -> tuple[int, ...]:
    """Return the channel numbers 1..*count*."""
    return tuple(range(1, count + 1))


def table_attr(channel: int) -> str:
    """Return the Gizwits attribute holding the dose table of *channel* (1-5)."""
    _check_channel(channel)
    return f"CH{channel}SWTime"


def timer_attr(channel: int) -> str:
    """Return the Gizwits attribute enabling the schedule of *channel*."""
    _check_channel(channel)
    return f"Timer{channel}ON"


def run_attr(channel: int) -> str:
    """Return the Gizwits attribute starting a manual run of *channel*."""
    _check_channel(channel)
    # Spelled "channe<n>" by the firmware.
    return f"channe{channel}"


def interval_attr(channel: int) -> str:
    """Return the Gizwits attribute holding the interval of *channel*."""
    _check_channel(channel)
    return f"IntervalT{channel}"


def _check_channel(channel: int) -> None:
    if channel not in CHANNELS:
        raise ScheduleError(f"channel {channel!r} is outside 1-{CHANNEL_COUNT}")


# =============================================================================
# Decoding
# =============================================================================


def has_table(attrs: dict[str, Any] | None, channel: int) -> bool:
    """Return True when the device reported the dose table of *channel*."""
    return attrs is not None and table_attr(channel) in attrs


def decode_table(raw: Any) -> list[dict[str, Any]]:
    """Decode one ``CH<n>SWTime`` value into its programmed doses.

    Returns the doses sorted by time, each as ``{"slot", "time", "amount_ml"}``
    with ``time`` in minutes since midnight. An unreadable value gives an
    empty list rather than an error, so a firmware answering in an unexpected
    shape cannot break the update loop.
    """
    data = _to_bytes(raw, DOSE_TABLE_LEN)
    if data is None:
        return []
    doses: list[dict[str, Any]] = []
    for slot in range(DOSE_SLOT_COUNT):
        hour, minute, amount_hi, amount_lo = data[
            slot * DOSE_SLOT_LEN : (slot + 1) * DOSE_SLOT_LEN
        ]
        amount = (amount_hi << 8) | amount_lo
        if amount == 0:
            continue
        doses.append({"slot": slot, "time": hour * 60 + minute, "amount_ml": amount})
    doses.sort(key=lambda d: (d["time"], d["slot"]))
    return doses


def daily_total_ml(doses: list[dict[str, Any]]) -> int:
    """Return the volume dosed in one day by a list of doses."""
    return sum(d["amount_ml"] for d in doses)


# =============================================================================
# Encoding
# =============================================================================


def normalize_doses(doses: list[dict[str, Any]]) -> list[dict[str, int]]:
    """Validate user doses and return them sorted, ready to encode.

    Two doses at the same minute are refused rather than merged: which one
    the firmware keeps is undocumented, and silently adding them would dose a
    volume nobody asked for.
    """
    if len(doses) > DOSE_SLOT_COUNT:
        raise ScheduleError(f"too many doses: {len(doses)} (max {DOSE_SLOT_COUNT})")

    result: list[dict[str, int]] = []
    for pos, raw in enumerate(doses):
        if not isinstance(raw, dict):
            raise ScheduleError(f"dose {pos}: not a mapping")
        where = f"dose {pos}"
        minutes = parse_minutes(raw.get("time"), f"{where} time")
        try:
            amount = int(raw.get("amount_ml"))  # type: ignore[arg-type]
        except (TypeError, ValueError) as exc:
            raise ScheduleError(
                f"{where} amount_ml: invalid value {raw.get('amount_ml')!r}"
            ) from exc
        if not 1 <= amount <= MAX_AMOUNT_ML:
            raise ScheduleError(
                f"{where} amount_ml: {amount} is outside 1-{MAX_AMOUNT_ML}"
            )
        result.append({"time": minutes, "amount_ml": amount})

    result.sort(key=lambda d: d["time"])
    for previous, current in pairwise(result):
        if previous["time"] == current["time"]:
            raise ScheduleError(f"two doses at {format_minutes(current['time'])}")
    return result


def encode_table(doses: list[dict[str, Any]]) -> str:
    """Encode normalized doses as the hex string of a whole ``CH<n>SWTime``.

    Unused slots are zeroed, so a dose removed in the UI cannot survive on
    the device.
    """
    data = bytearray(DOSE_TABLE_LEN)
    for slot, dose in enumerate(doses):
        offset = slot * DOSE_SLOT_LEN
        data[offset], data[offset + 1] = divmod(dose["time"], 60)
        data[offset + 2], data[offset + 3] = divmod(dose["amount_ml"], 256)
    return data.hex()


def build_control_payload(
    channel: int,
    doses: list[dict[str, Any]],
    current_attrs: dict[str, Any] | None = None,
) -> dict[str, str]:
    """Return the attribute to send to replace the dose table of *channel*.

    The table is always rewritten as a whole, in chronological order. An empty
    dict is returned when the device already holds exactly that table.
    """
    attr = table_attr(channel)
    encoded = encode_table(normalize_doses(doses))
    current = _to_bytes((current_attrs or {}).get(attr), DOSE_TABLE_LEN)
    if current is not None and current.hex() == encoded:
        return {}
    return {attr: encoded}
