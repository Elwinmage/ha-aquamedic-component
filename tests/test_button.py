"""Tests for button.py."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from homeassistant.const import EntityCategory

from custom_components.aquamedic.button import (
    REFRESH_DESCRIPTION,
    AquaMedicRefreshButton,
)
from tests.conftest import MOCK_DID


@pytest.fixture
def button(coordinator):
    return AquaMedicRefreshButton(coordinator, MOCK_DID, REFRESH_DESCRIPTION)


def test_button_unique_id(button):
    assert button._attr_unique_id == f"{MOCK_DID}_refresh"


def test_button_icon():
    assert REFRESH_DESCRIPTION.icon == "mdi:refresh"


def test_button_entity_category():
    assert REFRESH_DESCRIPTION.entity_category == EntityCategory.DIAGNOSTIC


def test_button_available_when_coordinator_ok(button, coordinator):
    assert button.available is coordinator.last_update_success


def test_button_available_independent_of_device_online(button, coordinator):
    """Button available is not tied to device online status."""
    from custom_components.aquamedic.coordinator import AquaMedicDeviceData
    from tests.conftest import MOCK_DEVICE_OFFLINE, MOCK_LATEST

    coordinator.data = {MOCK_DID: AquaMedicDeviceData(MOCK_DEVICE_OFFLINE, MOCK_LATEST)}
    assert button.available is True


async def test_button_press_triggers_refresh(button, coordinator):
    """async_press calls coordinator.async_request_refresh."""
    coordinator.async_request_refresh = AsyncMock()
    await button.async_press()
    coordinator.async_request_refresh.assert_called_once()
