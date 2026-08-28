"""Tests for maintenance.py — catalogue, persistent store and helpers."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from custom_components.aquamedic.const import (
    DC_RUNNER_PRODUCT_KEY,
    DC_RUNNER_SERIES_PRODUCT_KEY,
    SMARTDRIFT_PRODUCT_KEY,
)
from custom_components.aquamedic.maintenance import (
    PUMP_ROLE_DRIFT,
    PUMP_ROLE_OPTIONS,
    PUMP_ROLE_RETURN,
    PUMP_ROLE_SKIMMER,
    PUMP_ROLE_UNKNOWN,
    ROLE_PREFIX,
    TASKS,
    MaintenanceStore,
    _parse_dt,
    all_task_keys,
    compute_days_left,
    get_store,
    is_overdue,
    role_is_user_defined,
    tasks_for,
    tasks_for_device,
)
from tests.conftest import MOCK_DID

# ── Catalogue ─────────────────────────────────────────────────────────────────


def test_task_keys_are_unique():
    keys = all_task_keys()
    assert len(keys) == len(set(keys))


def test_every_task_declares_a_maint_translation_key():
    for tasks in TASKS.values():
        for task in tasks:
            assert task.translation_key == f"{ROLE_PREFIX}{task.key}"


def test_every_task_has_consistent_bounds():
    for tasks in TASKS.values():
        for task in tasks:
            assert 0 < task.min_days <= task.default_days <= task.max_days


def test_every_task_uses_a_known_unit():
    for tasks in TASKS.values():
        for task in tasks:
            assert task.unit in ("days", "weeks", "months")


def test_unknown_role_has_no_task():
    assert tasks_for(PUMP_ROLE_UNKNOWN) == ()


def test_tasks_for_returns_empty_on_garbage():
    assert tasks_for("not-a-role") == ()


def test_drift_return_and_skimmer_have_dedicated_tasks():
    assert len(tasks_for(PUMP_ROLE_DRIFT)) == 3
    assert len(tasks_for(PUMP_ROLE_RETURN)) == 3
    assert len(tasks_for(PUMP_ROLE_SKIMMER)) == 5


def test_smartdrift_ignores_the_declared_role():
    """A SmartDrift is unambiguous: its tasks never depend on the role."""
    assert tasks_for_device(SMARTDRIFT_PRODUCT_KEY, PUMP_ROLE_UNKNOWN) == tasks_for(
        PUMP_ROLE_DRIFT
    )


def test_dc_runner_series_follows_the_declared_role():
    assert tasks_for_device(
        DC_RUNNER_SERIES_PRODUCT_KEY, PUMP_ROLE_SKIMMER
    ) == tasks_for(PUMP_ROLE_SKIMMER)
    assert tasks_for_device(
        DC_RUNNER_SERIES_PRODUCT_KEY, PUMP_ROLE_RETURN
    ) == tasks_for(PUMP_ROLE_RETURN)


def test_undeclared_dc_runner_gets_no_task():
    assert tasks_for_device(DC_RUNNER_SERIES_PRODUCT_KEY, PUMP_ROLE_UNKNOWN) == ()


def test_unknown_product_key_gets_no_task():
    assert tasks_for_device("unknown-pk", PUMP_ROLE_SKIMMER) == ()
    assert tasks_for_device(None, PUMP_ROLE_SKIMMER) == ()


def test_role_is_user_defined_only_for_the_dc_runner_family():
    assert role_is_user_defined(DC_RUNNER_SERIES_PRODUCT_KEY) is True
    assert role_is_user_defined(DC_RUNNER_PRODUCT_KEY) is True
    assert role_is_user_defined(SMARTDRIFT_PRODUCT_KEY) is False
    assert role_is_user_defined(None) is False


# ── Store: read / write ───────────────────────────────────────────────────────


@pytest.fixture
def store(hass):
    return MaintenanceStore(hass, "test-entry-id")


async def test_load_is_idempotent(store):
    await store.async_load()
    await store.async_load()
    assert store.get_role(MOCK_DID) == PUMP_ROLE_UNKNOWN


async def test_interval_falls_back_to_the_default(store):
    await store.async_load()
    assert store.get_interval(MOCK_DID, "skimmer_cup_clean", 14) == 14


async def test_interval_override_is_kept(store):
    await store.async_load()
    await store.async_set_interval(MOCK_DID, "skimmer_cup_clean", 21)
    assert store.get_interval(MOCK_DID, "skimmer_cup_clean", 14) == 21


async def test_reset_stamps_now(store):
    await store.async_load()
    before = datetime.now(timezone.utc)
    stamped = await store.async_reset(MOCK_DID, "drift_descale")
    assert stamped >= before
    assert store.get_last_reset(MOCK_DID, "drift_descale") == stamped


async def test_notify_defaults_to_enabled(store):
    await store.async_load()
    assert store.get_notify(MOCK_DID, "drift_descale") is True


async def test_notify_can_be_disabled(store):
    await store.async_load()
    await store.async_set_notify(MOCK_DID, "drift_descale", False)
    assert store.get_notify(MOCK_DID, "drift_descale") is False


async def test_role_roundtrip(store):
    await store.async_load()
    await store.async_set_role(MOCK_DID, PUMP_ROLE_SKIMMER)
    assert store.get_role(MOCK_DID) == PUMP_ROLE_SKIMMER


async def test_unknown_role_is_rejected(store):
    await store.async_load()
    with pytest.raises(ValueError):
        await store.async_set_role(MOCK_DID, "pump-ish")


async def test_state_survives_a_reload(hass):
    """Everything written by one store instance is read back by the next."""
    first = MaintenanceStore(hass, "persist-entry")
    await first.async_load()
    await first.async_set_interval(MOCK_DID, "skimmer_cup_clean", 21)
    await first.async_set_notify(MOCK_DID, "skimmer_cup_clean", False)
    await first.async_set_role(MOCK_DID, PUMP_ROLE_SKIMMER)
    reset_at = await first.async_reset(MOCK_DID, "skimmer_cup_clean")

    second = MaintenanceStore(hass, "persist-entry")
    await second.async_load()
    assert second.get_interval(MOCK_DID, "skimmer_cup_clean", 14) == 21
    assert second.get_notify(MOCK_DID, "skimmer_cup_clean") is False
    assert second.get_role(MOCK_DID) == PUMP_ROLE_SKIMMER
    assert second.get_last_reset(MOCK_DID, "skimmer_cup_clean") == reset_at


async def test_default_role_is_not_persisted(hass):
    """Only a declared role is written, so the file stays lean."""
    store = MaintenanceStore(hass, "lean-entry")
    await store.async_load()
    await store.async_set_role(MOCK_DID, PUMP_ROLE_UNKNOWN)

    reloaded = MaintenanceStore(hass, "lean-entry")
    await reloaded.async_load()
    assert reloaded.get_role(MOCK_DID) == PUMP_ROLE_UNKNOWN


async def test_corrupted_role_is_ignored_on_load(hass, hass_storage):
    hass_storage["aquamedic_maintenance_corrupt"] = {
        "version": 1,
        "key": "aquamedic_maintenance_corrupt",
        "data": {"instances": {}, "roles": {MOCK_DID: "definitely-not-a-role"}},
    }
    store = MaintenanceStore(hass, "corrupt")
    await store.async_load()
    assert store.get_role(MOCK_DID) == PUMP_ROLE_UNKNOWN


async def test_naive_timestamp_is_read_as_utc(hass, hass_storage):
    hass_storage["aquamedic_maintenance_naive"] = {
        "version": 1,
        "key": "aquamedic_maintenance_naive",
        "data": {
            "instances": {
                f"{MOCK_DID}:drift_descale": {"last_reset": "2026-01-01T00:00:00"}
            },
            "roles": {},
        },
    }
    store = MaintenanceStore(hass, "naive")
    await store.async_load()
    last = store.get_last_reset(MOCK_DID, "drift_descale")
    assert last is not None and last.tzinfo is timezone.utc


# ── Store: listeners ──────────────────────────────────────────────────────────


async def test_listener_fires_on_reset(store):
    await store.async_load()
    calls: list[int] = []
    store.async_add_listener(MOCK_DID, "drift_descale", lambda: calls.append(1))
    await store.async_reset(MOCK_DID, "drift_descale")
    assert calls == [1]


async def test_listener_is_scoped_to_its_instance(store):
    await store.async_load()
    calls: list[int] = []
    store.async_add_listener(MOCK_DID, "drift_descale", lambda: calls.append(1))
    await store.async_reset(MOCK_DID, "drift_rotor_clean")
    assert calls == []


async def test_unsubscribe_stops_the_callback(store):
    await store.async_load()
    calls: list[int] = []
    unsub = store.async_add_listener(MOCK_DID, "drift_descale", lambda: calls.append(1))
    unsub()
    unsub()  # idempotent
    await store.async_reset(MOCK_DID, "drift_descale")
    assert calls == []


async def test_role_listener_fires_on_role_change(store):
    await store.async_load()
    calls: list[str] = []
    store.async_add_role_listener(MOCK_DID, lambda: calls.append("changed"))
    await store.async_set_role(MOCK_DID, PUMP_ROLE_RETURN)
    assert calls == ["changed"]


async def test_a_raising_listener_does_not_break_the_store(store):
    await store.async_load()
    seen: list[int] = []

    def boom() -> None:
        raise RuntimeError("listener failure")

    store.async_add_listener(MOCK_DID, "drift_descale", boom)
    store.async_add_listener(MOCK_DID, "drift_descale", lambda: seen.append(1))
    await store.async_reset(MOCK_DID, "drift_descale")
    assert seen == [1]


# ── get_store ─────────────────────────────────────────────────────────────────


def test_get_store_returns_the_attached_store(coordinator, hass):
    attached = MaintenanceStore(hass, "attached")
    coordinator.maintenance = attached
    assert get_store(coordinator) is attached


def test_get_store_builds_an_ephemeral_fallback(coordinator):
    coordinator.maintenance = None
    fallback = get_store(coordinator)
    assert isinstance(fallback, MaintenanceStore)
    # Cached on the coordinator so the four platforms share one instance.
    assert get_store(coordinator) is fallback


def test_get_store_fallback_works_without_a_maintenance_attribute(hass):
    bare = MagicMock(spec=["hass"])
    bare.hass = hass
    assert isinstance(get_store(bare), MaintenanceStore)


# ── Derived calculations ──────────────────────────────────────────────────────


def test_days_left_is_none_when_never_reset():
    assert compute_days_left(None, 30) is None
    assert is_overdue(None, 30) is False


def test_days_left_counts_down():
    now = datetime(2026, 8, 13, 12, 0, tzinfo=timezone.utc)
    last = now - timedelta(days=10)
    assert compute_days_left(last, 30, now) == 20


def test_a_partially_used_day_still_counts():
    now = datetime(2026, 8, 13, 12, 0, tzinfo=timezone.utc)
    last = now - timedelta(days=10, hours=12)
    assert compute_days_left(last, 30, now) == 19


def test_overdue_is_negative_and_rounded_away_from_zero():
    now = datetime(2026, 8, 13, 12, 0, tzinfo=timezone.utc)
    last = now - timedelta(days=30, hours=1)
    assert compute_days_left(last, 30, now) == -1
    assert is_overdue(last, 30, now) is True


def test_days_left_uses_now_by_default():
    last = datetime.now(timezone.utc) - timedelta(days=1)
    assert compute_days_left(last, 30) == 28


def test_parse_dt_rejects_garbage():
    assert _parse_dt(None) is None
    assert _parse_dt(42) is None
    assert _parse_dt("not-a-date") is None


def test_parse_dt_keeps_an_explicit_offset():
    parsed = _parse_dt("2026-08-13T12:00:00+02:00")
    assert parsed is not None and parsed.utcoffset() == timedelta(hours=2)


def test_pump_role_options_are_the_three_user_choices():
    assert PUMP_ROLE_OPTIONS == (
        PUMP_ROLE_UNKNOWN,
        PUMP_ROLE_RETURN,
        PUMP_ROLE_SKIMMER,
    )
