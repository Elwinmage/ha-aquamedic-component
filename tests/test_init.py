"""Basic smoke tests for Aquamedic."""

from custom_components.aquamedic.const import DOMAIN


def test_domain():
    """Ensure the DOMAIN constant is correct."""
    assert DOMAIN == "aquamedic"
