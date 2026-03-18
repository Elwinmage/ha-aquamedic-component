"""Shared pytest fixtures for Aquamedic tests."""
import pytest


@pytest.fixture
def domain():
    """Return the integration domain."""
    return "aquamedic"
