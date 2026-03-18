"""DataUpdateCoordinator for Aquamedic."""
from __future__ import annotations
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from .const import DOMAIN


class AquamedicCoordinator(DataUpdateCoordinator):
    """Manage data fetching for Aquamedic."""
