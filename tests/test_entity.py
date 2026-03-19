"""Tests for entity.py base class."""

from __future__ import annotations

import pytest

from custom_components.aquamedic.entity import AquaMedicEntity
from custom_components.aquamedic.const import DOMAIN, SMARTDRIFT_PRODUCT_KEY
from tests.conftest import MOCK_DID, MOCK_ATTRS


class _ConcreteEntity(AquaMedicEntity):
    """Minimal concrete entity for testing."""
    pass


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
