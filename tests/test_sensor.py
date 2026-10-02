"""Tests for sensor.py — time-slot schedule sensor."""

from __future__ import annotations

from unittest.mock import MagicMock

from custom_components.aquamedic.const import (
    DC_RUNNER_PRODUCT_KEY,
    DC_RUNNER_SERIES_PRODUCT_KEY,
    DOMAIN,
)
from custom_components.aquamedic.coordinator import AquaMedicDeviceData
from custom_components.aquamedic.schedule import (
    LAYOUT_DRIFT,
    LAYOUT_RUNNER,
    SLOT_COUNT,
    slot_attr,
)
from custom_components.aquamedic.sensor import (
    SCHEDULE_DESCRIPTION,
    AquaMedicScheduleSensor,
    async_setup_entry,
)
from tests.conftest import MOCK_ATTRS, MOCK_DEVICE_ONLINE, MOCK_DID

RUNNER_DID = "runner-did"


def _blank(slot_len: int) -> dict[str, str]:
    return {slot_attr(i): "00" * slot_len for i in range(SLOT_COUNT)}


def _set_attrs(coordinator, attrs: dict) -> None:
    coordinator.data = {
        MOCK_DID: AquaMedicDeviceData(MOCK_DEVICE_ONLINE, {"attr": attrs})
    }


def _sensor(coordinator, layout=LAYOUT_DRIFT) -> AquaMedicScheduleSensor:
    return AquaMedicScheduleSensor(coordinator, MOCK_DID, SCHEDULE_DESCRIPTION, layout)


# ── Setup ─────────────────────────────────────────────────────────────────────


async def test_setup_entry_creates_one_sensor_per_scheduler(hass, coordinator):
    coordinator.data[RUNNER_DID] = AquaMedicDeviceData(
        {
            **MOCK_DEVICE_ONLINE,
            "did": RUNNER_DID,
            "product_key": DC_RUNNER_SERIES_PRODUCT_KEY,
        },
        {},
    )
    # The legacy DC Runner key has no scheduler: no sensor for it.
    coordinator.data["legacy"] = AquaMedicDeviceData(
        {**MOCK_DEVICE_ONLINE, "did": "legacy", "product_key": DC_RUNNER_PRODUCT_KEY},
        {},
    )
    entry = MagicMock()
    entry.entry_id = "entry-1"
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    added: list = []

    await async_setup_entry(hass, entry, added.extend)

    assert sorted(e.did for e in added) == sorted([MOCK_DID, RUNNER_DID])
    kinds = {e.did: e.layout.kind for e in added}
    assert kinds == {MOCK_DID: "drift", RUNNER_DID: "runner"}
    assert all(e.unique_id.endswith("_schedule") for e in added)


async def test_setup_entry_empty_coordinator(hass, coordinator):
    coordinator.data = None
    entry = MagicMock()
    entry.entry_id = "entry-1"
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    added: list = []
    await async_setup_entry(hass, entry, added.extend)
    assert added == []


# ── State ─────────────────────────────────────────────────────────────────────


def test_unavailable_until_the_slots_are_reported(coordinator):
    # conftest attrs carry no AutoTimeNN datapoint.
    sensor = _sensor(coordinator)
    assert sensor.available is False
    assert sensor.native_value is None
    attrs = sensor.extra_state_attributes
    assert attrs["schedule"] == []
    assert attrs["reef_role"] == "schedule"


def test_unavailable_when_the_device_is_gone(coordinator):
    coordinator.data = {}
    sensor = _sensor(coordinator)
    assert sensor.available is False
    assert sensor.native_value is None
    assert sensor.extra_state_attributes["timer_on"] is None


def test_unavailable_when_the_last_update_failed(coordinator):
    _set_attrs(coordinator, {**MOCK_ATTRS, **_blank(8)})
    coordinator.last_update_success = False
    assert _sensor(coordinator).available is False


def test_state_counts_programmed_slots(coordinator):
    attrs = {**MOCK_ATTRS, **_blank(8), "TimerON": 1}
    attrs[slot_attr(0)] = "08000c1e023c2801"
    attrs[slot_attr(1)] = "0e001000043c0000"
    _set_attrs(coordinator, attrs)
    coordinator.last_update_success = True

    sensor = _sensor(coordinator)
    assert sensor.available is True
    assert sensor.native_value == 2
    extra = sensor.extra_state_attributes
    assert [s["mode"] for s in extra["schedule"]] == ["sine_wave", "constant_flow"]
    assert extra["kind"] == "drift"
    assert extra["max_slots"] == SLOT_COUNT
    assert extra["min_value"] == 0
    assert extra["timer_on"] is True
    assert "feeding" in extra["modes"]


def test_runner_layout_reports_its_motor_floor(coordinator):
    _set_attrs(coordinator, {**_blank(6), "TimerON": 0})
    coordinator.last_update_success = True
    sensor = _sensor(coordinator, LAYOUT_RUNNER)
    assert sensor.native_value == 0
    extra = sensor.extra_state_attributes
    assert extra["min_value"] == 30
    assert extra["timer_on"] is False
