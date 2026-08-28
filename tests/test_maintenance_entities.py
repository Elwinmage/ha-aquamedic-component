"""Tests for the maintenance entities (button, number, switch, select)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.aquamedic.button import AquaMedicMaintenanceButton
from custom_components.aquamedic.const import DC_SKIMMER_PRODUCT_KEY
from custom_components.aquamedic.coordinator import AquaMedicDeviceData
from custom_components.aquamedic.maintenance import (
    PUMP_ROLE_RETURN,
    PUMP_ROLE_SKIMMER,
    PUMP_ROLE_UNKNOWN,
    MaintenanceStore,
    tasks_for,
)
from custom_components.aquamedic.number import AquaMedicMaintenanceIntervalNumber
from custom_components.aquamedic.select import AquaMedicPumpRoleSelect
from custom_components.aquamedic.switch import AquaMedicMaintenanceNotifySwitch
from tests.conftest import MOCK_DEVICE_ONLINE, MOCK_DID, MOCK_LATEST

DC_DID = "dc-runner-did"


@pytest.fixture(autouse=True)
async def _stop_coordinator_timer(coordinator):
    """Cancel the refresh timer started when an entity is added to hass.

    CoordinatorEntity registers its coordinator listener through
    `async_on_remove`, which only runs when the entity *platform* removes the
    entity. These tests drive the entities directly, so the listener — and the
    refresh timer that adding it schedules — would outlive the test and trip
    HA's lingering-timer check during teardown.
    """
    yield
    await coordinator.async_shutdown()


def _task(role: str, key: str):
    for task in tasks_for(role):
        if task.key == key:
            return task
    raise KeyError(key)


@pytest.fixture
async def store(hass, coordinator):
    """A loaded store, attached to the coordinator like async_setup_entry does."""
    store = MaintenanceStore(hass, "maint-entities")
    await store.async_load()
    coordinator.maintenance = store
    return store


@pytest.fixture
def dc_coordinator(coordinator):
    """Coordinator holding one DC Runner series device."""
    coordinator.data[DC_DID] = AquaMedicDeviceData(
        {
            **MOCK_DEVICE_ONLINE,
            "did": DC_DID,
            "product_key": DC_SKIMMER_PRODUCT_KEY,
            "dev_alias": "Abschäumer",
        },
        MOCK_LATEST,
    )
    return coordinator


def _wire(entity, hass):
    """Make an entity able to write its state without a real platform."""
    entity.hass = hass
    entity.entity_id = "domain.maintenance_test"
    entity.async_write_ha_state = MagicMock()
    return entity


# ── Button ────────────────────────────────────────────────────────────────────


@pytest.fixture
def button(coordinator, store, hass):
    task = _task(PUMP_ROLE_SKIMMER, "skimmer_cup_clean")
    return _wire(AquaMedicMaintenanceButton(coordinator, MOCK_DID, task), hass)


def test_button_unique_id(button):
    assert button._attr_unique_id == f"{MOCK_DID}_maint_skimmer_cup_clean"


def test_button_uses_the_catalogue_icon(button):
    assert button._attr_icon == "mdi:cup-water"


def test_button_is_available_even_offline(button, coordinator):
    coordinator.last_update_success = False
    assert button.available is True


def test_button_publishes_the_card_contract(button):
    attrs = button.extra_state_attributes
    assert attrs is not None
    assert attrs["reef_role"] == "maint_skimmer_cup_clean"
    assert attrs["task_key"] == "skimmer_cup_clean"
    assert attrs["interval_days"] == 14
    assert attrs["notify"] is True


def test_button_is_pending_until_first_reset(button):
    attrs = button.extra_state_attributes
    assert attrs is not None
    assert attrs["days_left"] is None
    assert attrs["overdue"] is False
    assert attrs["last_reset"] is None


async def test_button_press_records_the_reset(button, store):
    await button.async_press()
    attrs = button.extra_state_attributes
    assert attrs is not None
    assert attrs["last_reset"] is not None
    assert attrs["days_left"] == 13  # 14-day interval, a fraction of day elapsed
    assert store.get_last_reset(MOCK_DID, "skimmer_cup_clean") is not None


async def test_button_reports_overdue(button, store):
    # 19.5 days elapsed on a 14-day interval -> -5.5, floored away from zero.
    # A whole number of days would sit exactly on the rounding boundary.
    stale = datetime.now(timezone.utc) - timedelta(days=19, hours=12)
    store.get_state(MOCK_DID, "skimmer_cup_clean").last_reset = stale
    attrs = button.extra_state_attributes
    assert attrs is not None
    assert attrs["overdue"] is True
    assert attrs["days_left"] == -6


async def test_button_mirrors_the_notify_switch(button, store):
    await store.async_set_notify(MOCK_DID, "skimmer_cup_clean", False)
    attrs = button.extra_state_attributes
    assert attrs is not None
    assert attrs["notify"] is False


async def test_button_refreshes_on_store_change(button, store):
    await button.async_added_to_hass()
    await store.async_reset(MOCK_DID, "skimmer_cup_clean")
    assert button.async_write_ha_state.called
    await button.async_will_remove_from_hass()
    button.async_write_ha_state.reset_mock()
    await store.async_reset(MOCK_DID, "skimmer_cup_clean")
    assert not button.async_write_ha_state.called


async def test_removal_without_subscription_is_safe(button):
    await button.async_will_remove_from_hass()


# ── Interval number ───────────────────────────────────────────────────────────


@pytest.fixture
def weekly_number(coordinator, store, hass):
    task = _task(PUMP_ROLE_SKIMMER, "skimmer_cup_clean")
    return _wire(AquaMedicMaintenanceIntervalNumber(coordinator, MOCK_DID, task), hass)


@pytest.fixture
def monthly_number(coordinator, store, hass):
    task = _task(PUMP_ROLE_RETURN, "runner_impeller_clean")
    return _wire(AquaMedicMaintenanceIntervalNumber(coordinator, MOCK_DID, task), hass)


def test_number_unique_id(weekly_number):
    assert (
        weekly_number._attr_unique_id == f"{MOCK_DID}_maint_skimmer_cup_clean_interval"
    )


def test_number_carries_the_unit_in_its_role(weekly_number, monthly_number):
    assert (
        weekly_number._attr_translation_key == "maint_skimmer_cup_clean_interval_weeks"
    )
    assert (
        monthly_number._attr_translation_key
        == "maint_runner_impeller_clean_interval_months"
    )


def test_weekly_bounds_are_converted(weekly_number):
    # 7..28 days -> 1..4 weeks, default 14 days -> 2 weeks
    assert weekly_number.native_min_value == 1
    assert weekly_number.native_max_value == 4
    assert weekly_number.native_value == 2


def test_monthly_bounds_are_converted(monthly_number):
    # 60..180 days -> 2..6 months, default 120 days -> 4 months
    assert monthly_number.native_min_value == 2
    assert monthly_number.native_max_value == 6
    assert monthly_number.native_value == 4


def test_number_is_available_even_offline(weekly_number, coordinator):
    coordinator.last_update_success = False
    assert weekly_number.available is True


async def test_setting_the_slider_stores_days(weekly_number, store):
    await weekly_number.async_set_native_value(3)
    assert store.get_interval(MOCK_DID, "skimmer_cup_clean", 14) == 21
    assert weekly_number.native_value == 3


async def test_slider_rounds_before_converting(monthly_number, store):
    await monthly_number.async_set_native_value(2.6)
    assert store.get_interval(MOCK_DID, "runner_impeller_clean", 120) == 90


# ── Notify switch ─────────────────────────────────────────────────────────────


@pytest.fixture
def notify_switch(coordinator, store, hass):
    task = _task(PUMP_ROLE_SKIMMER, "skimmer_cup_clean")
    return _wire(AquaMedicMaintenanceNotifySwitch(coordinator, MOCK_DID, task), hass)


def test_switch_unique_id_and_role(notify_switch):
    assert notify_switch._attr_unique_id == f"{MOCK_DID}_maint_skimmer_cup_clean_notify"
    assert notify_switch._attr_translation_key == "maint_skimmer_cup_clean_notify"


def test_switch_defaults_to_on(notify_switch):
    assert notify_switch.is_on is True
    assert notify_switch.icon == "mdi:bell-ring"


def test_switch_is_available_even_offline(notify_switch, coordinator):
    coordinator.last_update_success = False
    assert notify_switch.available is True


async def test_turning_the_switch_off_mutes_the_task(notify_switch, store):
    await notify_switch.async_added_to_hass()
    await notify_switch.async_turn_off()
    assert store.get_notify(MOCK_DID, "skimmer_cup_clean") is False
    assert notify_switch.is_on is False
    assert notify_switch.icon == "mdi:bell-off"

    await notify_switch.async_turn_on()
    assert notify_switch.is_on is True
    assert notify_switch.icon == "mdi:bell-ring"


async def test_switch_reads_the_store_before_the_first_state(notify_switch, store):
    await store.async_set_notify(MOCK_DID, "skimmer_cup_clean", False)
    await notify_switch.async_added_to_hass()
    assert notify_switch.is_on is False


# ── Pump role select ──────────────────────────────────────────────────────────


@pytest.fixture
def role_select(dc_coordinator, store, hass):
    select = _wire(AquaMedicPumpRoleSelect(dc_coordinator, DC_DID), hass)
    select.hass.config_entries.async_reload = AsyncMock()
    return select


def test_role_select_defaults_to_unknown(role_select):
    assert role_select.current_option == PUMP_ROLE_UNKNOWN
    assert role_select.options == [
        PUMP_ROLE_UNKNOWN,
        PUMP_ROLE_RETURN,
        PUMP_ROLE_SKIMMER,
    ]


def test_role_select_is_available_even_offline(role_select, dc_coordinator):
    dc_coordinator.last_update_success = False
    assert role_select.available is True


def test_role_select_exposes_its_reef_role(role_select):
    attrs = role_select.extra_state_attributes
    assert attrs is not None and attrs["reef_role"] == "pump_role"


async def test_selecting_a_role_stores_it_and_reloads(
    role_select, store, dc_coordinator
):
    dc_coordinator.entry_id = "reload-me"
    await role_select.async_select_option(PUMP_ROLE_SKIMMER)
    await role_select.hass.async_block_till_done()

    assert store.get_role(DC_DID) == PUMP_ROLE_SKIMMER
    role_select.hass.config_entries.async_reload.assert_awaited_once_with("reload-me")


async def test_selecting_the_same_role_is_a_no_op(role_select, store, dc_coordinator):
    dc_coordinator.entry_id = "reload-me"
    await store.async_set_role(DC_DID, PUMP_ROLE_RETURN)
    await role_select.async_select_option(PUMP_ROLE_RETURN)
    await role_select.hass.async_block_till_done()

    role_select.hass.config_entries.async_reload.assert_not_called()


async def test_clearing_the_role_also_reloads(role_select, store, dc_coordinator):
    """Going back to "unknown" removes the tasks, so it reloads too."""
    dc_coordinator.entry_id = "reload-me"
    await store.async_set_role(DC_DID, PUMP_ROLE_SKIMMER)
    await role_select.async_select_option(PUMP_ROLE_UNKNOWN)
    await role_select.hass.async_block_till_done()

    assert store.get_role(DC_DID) == PUMP_ROLE_UNKNOWN
    role_select.hass.config_entries.async_reload.assert_awaited_once_with("reload-me")


async def test_an_invalid_role_is_refused(role_select, store):
    await role_select.async_select_option("pump-ish")
    assert store.get_role(DC_DID) == PUMP_ROLE_UNKNOWN


async def test_role_is_saved_even_without_an_entry_id(
    role_select, store, dc_coordinator
):
    dc_coordinator.entry_id = None
    await role_select.async_select_option(PUMP_ROLE_RETURN)
    await role_select.hass.async_block_till_done()

    assert store.get_role(DC_DID) == PUMP_ROLE_RETURN
    role_select.hass.config_entries.async_reload.assert_not_called()


async def test_role_select_refreshes_on_role_change(role_select, store):
    await role_select.async_added_to_hass()
    await store.async_set_role(DC_DID, PUMP_ROLE_SKIMMER)
    assert role_select.async_write_ha_state.called

    await role_select.async_will_remove_from_hass()
    role_select.async_write_ha_state.reset_mock()
    await store.async_set_role(DC_DID, PUMP_ROLE_RETURN)
    assert not role_select.async_write_ha_state.called


async def test_role_select_removal_without_subscription_is_safe(role_select):
    await role_select.async_will_remove_from_hass()
