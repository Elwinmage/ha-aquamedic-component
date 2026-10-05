"""Tests for entity.py base class."""

from __future__ import annotations

import pytest

from custom_components.aquamedic.const import DOMAIN, SMARTDRIFT_PRODUCT_KEY
from custom_components.aquamedic.entity import AquaMedicEntity, ReefRoleMixin
from tests.conftest import MOCK_DID


class _ConcreteEntity(AquaMedicEntity):
    """Minimal concrete entity for testing."""


@pytest.fixture
def entity(coordinator):
    return _ConcreteEntity(coordinator, MOCK_DID, "test_suffix")


def test_unique_id(entity):
    assert entity._attr_unique_id == f"{MOCK_DID}_test_suffix"


def test_device_info_keys(entity):
    info = entity.device_info
    assert (DOMAIN, MOCK_DID) in info["identifiers"]
    assert info["manufacturer"] == "Aqua Medic"
    assert info["model"] == "SmartDrift"
    assert info["name"] == "SmartDrift Test"


def test_device_info_offline_fallback(coordinator):
    """When device data is missing, name falls back to did."""
    coordinator.data = {}
    e = _ConcreteEntity(coordinator, MOCK_DID, "x")
    info = e.device_info
    assert info["name"] == MOCK_DID


def test_gizwits_value_existing(entity):
    assert entity._gizwits_value("Flow") == 75


def test_gizwits_value_missing(entity):
    assert entity._gizwits_value("NoSuchAttr") is None
    assert entity._gizwits_value("NoSuchAttr", 0) == 0


def test_gizwits_value_no_data(coordinator):
    coordinator.data = {}
    e = _ConcreteEntity(coordinator, MOCK_DID, "x")
    assert e._gizwits_value("Flow") is None


def test_device_property_returns_none_when_missing(coordinator):
    coordinator.data = {}
    e = _ConcreteEntity(coordinator, MOCK_DID, "x")
    assert e._device is None


def test_device_property_returns_data(entity):
    assert entity._device is not None
    assert entity._device.attrs["Flow"] == 75


# ── resolve_model ─────────────────────────────────────────────────────────────


def test_resolve_model_maps_the_dc_runner_family():
    """Both DC Runner product keys share a single HA-visible model label."""
    from custom_components.aquamedic.const import (
        DC_RUNNER_PRODUCT_KEY,
        DC_RUNNER_SERIES_PRODUCT_KEY,
    )
    from custom_components.aquamedic.entity import resolve_model

    assert resolve_model(DC_RUNNER_SERIES_PRODUCT_KEY) == "DC Runner"
    assert resolve_model(DC_RUNNER_PRODUCT_KEY) == "DC Runner"


def test_resolve_model_falls_back_to_smartdrift():
    from custom_components.aquamedic.entity import resolve_model

    assert resolve_model(SMARTDRIFT_PRODUCT_KEY) == "SmartDrift"
    assert resolve_model(None) == "SmartDrift"


# ── ReefRoleMixin ─────────────────────────────────────────────────────────────


class _Roled(ReefRoleMixin):
    """Mixin user declaring a translation_key, like a real entity."""

    translation_key = "maint_drift_descale"
    _attr_extra_state_attributes = {"days_left": 3}


class _Roleless(ReefRoleMixin):
    """Mixin user without a translation_key: reef_role must not appear."""


def test_mixin_adds_reef_role_from_the_translation_key():
    assert _Roled().extra_state_attributes == {
        "days_left": 3,
        "reef_role": "maint_drift_descale",
    }


def test_mixin_keeps_the_attributes_when_there_is_no_role():
    obj = _Roleless()
    obj._attr_extra_state_attributes = {"days_left": 3}
    assert obj.extra_state_attributes == {"days_left": 3}


def test_mixin_returns_none_without_role_nor_attributes():
    assert _Roleless().extra_state_attributes is None


# ── resolve_model_id / build_device_info ──────────────────────────────────────


def _as_dc_runner(coordinator):
    """Turn the fixture device into a DC Runner series pump."""
    from custom_components.aquamedic.const import DC_RUNNER_SERIES_PRODUCT_KEY
    from custom_components.aquamedic.coordinator import AquaMedicDeviceData
    from tests.conftest import MOCK_DEVICE_ONLINE, MOCK_LATEST

    coordinator.data = {
        MOCK_DID: AquaMedicDeviceData(
            {**MOCK_DEVICE_ONLINE, "product_key": DC_RUNNER_SERIES_PRODUCT_KEY},
            MOCK_LATEST,
        )
    }


def test_resolve_model_id_carries_the_declared_role():
    from custom_components.aquamedic.const import DC_RUNNER_SERIES_PRODUCT_KEY
    from custom_components.aquamedic.entity import resolve_model_id

    assert resolve_model_id(DC_RUNNER_SERIES_PRODUCT_KEY, "skimmer") == "skimmer"
    assert resolve_model_id(DC_RUNNER_SERIES_PRODUCT_KEY, "return") == "return"


def test_resolve_model_id_is_none_until_the_role_is_declared():
    from custom_components.aquamedic.const import DC_RUNNER_SERIES_PRODUCT_KEY
    from custom_components.aquamedic.entity import resolve_model_id

    assert resolve_model_id(DC_RUNNER_SERIES_PRODUCT_KEY, "unknown") is None
    assert resolve_model_id(DC_RUNNER_SERIES_PRODUCT_KEY, None) is None


def test_resolve_model_id_ignores_unambiguous_product_keys():
    from custom_components.aquamedic.entity import resolve_model_id

    assert resolve_model_id(SMARTDRIFT_PRODUCT_KEY, "skimmer") is None
    assert resolve_model_id(None, "skimmer") is None


def test_device_info_has_no_model_id_for_a_smartdrift(entity, coordinator):
    assert entity.device_info["model_id"] is None
    # The role store is not even looked at for an unambiguous product key.
    assert getattr(coordinator, "maintenance", None) is None


async def test_device_info_publishes_the_role_as_model_id(hass, coordinator):
    from custom_components.aquamedic.maintenance import get_store

    _as_dc_runner(coordinator)
    await get_store(coordinator).async_set_role(MOCK_DID, "skimmer")

    info = _ConcreteEntity(coordinator, MOCK_DID, "x").device_info
    assert info["model"] == "DC Runner"
    assert info["model_id"] == "skimmer"


def test_device_info_model_id_is_none_while_the_role_is_unknown(coordinator):
    _as_dc_runner(coordinator)
    info = _ConcreteEntity(coordinator, MOCK_DID, "x").device_info
    assert info["model"] == "DC Runner"
    assert info["model_id"] is None


async def test_role_survives_in_the_registry_of_a_disabled_device(hass, coordinator):
    """The registry keeps (and still receives) the role of a disabled device.

    This is what ha-reef-card relies on: a disabled device has no entity
    state left, but its registry entry — model_id included — stays visible.
    """
    from homeassistant.helpers import device_registry as dr
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    from custom_components.aquamedic.maintenance import get_store

    entry = MockConfigEntry(domain=DOMAIN)
    entry.add_to_hass(hass)
    registry = dr.async_get(hass)
    _as_dc_runner(coordinator)

    def register():
        info = _ConcreteEntity(coordinator, MOCK_DID, "x").device_info
        return registry.async_get_or_create(config_entry_id=entry.entry_id, **info)

    device = register()
    assert device.model_id is None

    registry.async_update_device(device.id, disabled_by=dr.DeviceEntryDisabler.USER)

    # Entities of a disabled device still go through device registration
    # when the entry is set up, so an upgrade fills the role in.
    await get_store(coordinator).async_set_role(MOCK_DID, "skimmer")
    device = register()
    assert device.disabled_by is dr.DeviceEntryDisabler.USER
    assert device.model_id == "skimmer"

    # Clearing the role clears it in the registry too.
    await get_store(coordinator).async_set_role(MOCK_DID, "unknown")
    assert register().model_id is None
