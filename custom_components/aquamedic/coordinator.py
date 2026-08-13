"""DataUpdateCoordinator for Aqua Medic / Gizwits devices."""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .client import AquaMedicClient, AquaMedicConnectionError
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN
from .maintenance import MaintenanceStore

_LOGGER = logging.getLogger(__name__)


class AquaMedicDeviceData:
    """Holds parsed state for one device."""

    def __init__(self, device: dict, latest: dict) -> None:
        self.did = device.get("did", "")
        self.product_key = device.get("product_key", "")
        self.name = device.get("dev_alias") or device.get("product_name") or "AquaMedic"
        self.is_online = AquaMedicClient.resolve_is_online(device, latest)
        self.attrs: dict = latest.get("attr", {})
        self.updated_at = latest.get("updated_at")

    def get(self, attr: str, default=None):
        """Convenience getter for a single attribute value."""
        return self.attrs.get(attr, default)


class AquaMedicCoordinator(DataUpdateCoordinator[dict[str, AquaMedicDeviceData]]):
    """Fetch data from all Gizwits devices at a configurable interval.

    ``data``           — dict keyed by did → AquaMedicDeviceData
    ``control_0_10v``  — per-device local flag: when True, the pump is driven
                         by an external 0-10V signal and the Flow number entity
                         must be disabled.
    ``maintenance``    — persistent maintenance state, attached by
                         ``async_setup_entry``. Optional so tests and
                         standalone use keep working: platforms go through
                         ``maintenance.get_store()``, which falls back to an
                         ephemeral store.
    ``entry_id``       — owning config entry, needed to reload the entry when
                         the user changes a pump role.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        client: AquaMedicClient,
        scan_interval: int = DEFAULT_SCAN_INTERVAL,
        entry_id: str | None = None,
    ) -> None:
        self._client = client
        self.entry_id = entry_id
        self.maintenance: MaintenanceStore | None = None
        # Local state: did → bool (0-10V mode active)
        self._control_0_10v: dict[str, bool] = {}
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )

    # ── 0-10V local state ─────────────────────────────────────────────────────

    def get_control_0_10v(self, did: str) -> bool:
        """Return True if 0-10V mode is active for this device."""
        return self._control_0_10v.get(did, False)

    def set_control_0_10v(self, did: str, value: bool) -> None:
        """Set the 0-10V mode flag for a device and notify listeners."""
        self._control_0_10v[did] = value
        self.async_update_listeners()

    # ── Data fetch ────────────────────────────────────────────────────────────

    async def _async_update_data(self) -> dict[str, AquaMedicDeviceData]:
        """Pull fresh data from the Gizwits API."""
        try:
            devices = await self._client.get_devices()
        except AquaMedicConnectionError as exc:
            raise UpdateFailed(f"Failed to fetch device list: {exc}") from exc

        result: dict[str, AquaMedicDeviceData] = {}

        for device in devices:
            did = device.get("did")
            if not did:
                continue
            try:
                latest = await self._client.get_device_data(did)
            except AquaMedicConnectionError as exc:
                _LOGGER.warning("Could not fetch data for device %s: %s", did, exc)
                latest = {}

            result[did] = AquaMedicDeviceData(device, latest)
            _LOGGER.debug(
                "Updated %s (%s): %s",
                result[did].name,
                did,
                result[did].attrs,
            )

        return result
