"""DataUpdateCoordinator for Aqua Medic / Gizwits devices."""

from __future__ import annotations

import logging
import time
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .client import AquaMedicClient, AquaMedicConnectionError
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN
from .maintenance import MaintenanceStore

_LOGGER = logging.getLogger(__name__)

# How long a value just written is kept when the cloud still reports the
# previous one. The Gizwits "latest" endpoint lags a few seconds behind an
# accepted command, and the refresh that follows a write would otherwise put
# the old value back on screen until the next poll.
OPTIMISTIC_HOLD_SECONDS = 20.0

_MISSING: Any = object()


def _same_value(left: Any, right: Any) -> bool:
    """Compare a written value with what the cloud reports.

    The cloud answers booleans as 0/1 or true/false and binary datapoints in
    either letter case, so plain equality would see a difference where there
    is none.
    """
    if isinstance(left, bool) or isinstance(right, bool):
        try:
            return bool(int(left)) == bool(int(right))
        except (TypeError, ValueError):
            return False
    if isinstance(left, str) and isinstance(right, str):
        return left.lower() == right.lower()
    return left == right


class AquaMedicDeviceData:
    """Holds parsed state for one device."""

    def __init__(self, device: dict, latest: dict) -> None:
        self.did = device.get("did", "")
        self.product_key = device.get("product_key", "")
        self.name = device.get("dev_alias") or device.get("product_name") or "AquaMedic"
        self.is_online = AquaMedicClient.resolve_is_online(device, latest)
        # A copy: optimistic writes change it, and must not reach the
        # response it was read from.
        self.attrs: dict = dict(latest.get("attr") or {})
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
        # Values written but not confirmed by the cloud yet:
        # did → attr → (value, monotonic deadline)
        self._pending: dict[str, dict[str, tuple[Any, float]]] = {}
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

    # ── Optimistic writes ─────────────────────────────────────────────────────

    async def async_control(self, did: str, attrs: dict[str, Any]) -> None:
        """Send a command and show its effect at once.

        The new values are put in the coordinator data before the cloud is
        called, so every entity (and the card reading them) updates
        immediately instead of after the round trip. If the cloud refuses
        the command, the previous values are restored and the error is
        raised to the caller.
        """
        device = self.data.get(did) if self.data else None
        previous: dict[str, Any] = {}
        if device is not None:
            deadline = time.monotonic() + OPTIMISTIC_HOLD_SECONDS
            pending = self._pending.setdefault(did, {})
            for attr, value in attrs.items():
                previous[attr] = device.attrs.get(attr, _MISSING)
                device.attrs[attr] = value
                pending[attr] = (value, deadline)
            self.async_update_listeners()

        try:
            await self._client.control_device(did, attrs)
        except Exception:
            if device is not None:
                pending = self._pending.get(did, {})
                for attr, value in previous.items():
                    pending.pop(attr, None)
                    if value is _MISSING:
                        device.attrs.pop(attr, None)
                    else:
                        device.attrs[attr] = value
                self.async_update_listeners()
            raise

        await self.async_request_refresh()

    def _apply_pending(self, did: str, attrs: dict[str, Any]) -> None:
        """Keep the values just written until the cloud catches up.

        A pending value is dropped as soon as the cloud reports it, or when
        its hold expires: from then on the cloud is the truth again, so a
        command the pump silently ignored cannot stay on screen.
        """
        pending = self._pending.get(did)
        if not pending:
            return
        now = time.monotonic()
        for attr, (value, deadline) in list(pending.items()):
            if now >= deadline or _same_value(value, attrs.get(attr, _MISSING)):
                del pending[attr]
            else:
                attrs[attr] = value
        if not pending:
            del self._pending[did]

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
            self._apply_pending(did, result[did].attrs)
            _LOGGER.debug(
                "Updated %s (%s): %s",
                result[did].name,
                did,
                result[did].attrs,
            )

        return result
