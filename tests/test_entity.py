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
