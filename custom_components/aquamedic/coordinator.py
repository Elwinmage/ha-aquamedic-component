"""DataUpdateCoordinator for Aqua Medic / Gizwits devices."""

from __future__ import annotations

import logging
import time
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .client import AquaMedicAuthError, AquaMedicClient, AquaMedicConnectionError
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN, SMARTDRIFT_PRODUCT_KEY
from .local import LocalError, LocalPump, LocalSchema, async_discover
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
        # True when the attributes were read from the pump on the local
        # network rather than from the cloud.
        self.local = False

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
        local_hosts: list[str] | None = None,
    ) -> None:
        self._client = client
        self.entry_id = entry_id
        # Pumps reachable on the LAN: hosts still to identify, then did → pump.
        self._unbound_hosts: list[str] = list(local_hosts or [])
        self._local: dict[str, LocalPump] = {}
        # Pumps whose controls are sent locally. Reading is the same protocol
        # for every product; writing has only been checked on the SmartDrift.
        self._local_writes: set[str] = set()
        self._schemas: dict[str, LocalSchema] = {}
        self._local_failing: set[str] = set()
        self._devices_cache: list[dict] = []
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
            await self._send_control(did, attrs)
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

    async def _send_control(self, did: str, attrs: dict[str, Any]) -> None:
        """Send a command on the local network when possible, else by the cloud."""
        pump = self._local.get(did)
        if pump is not None and did in self._local_writes and pump.can_write(attrs):
            try:
                await pump.async_write(attrs)
            except LocalError as exc:
                _LOGGER.warning(
                    "Local write to %s failed (%s), sending it through the cloud",
                    did,
                    exc,
                )
            else:
                return
        await self._client.control_device(did, attrs)

    # ── Local network ─────────────────────────────────────────────────────────

    async def _async_bind_local(self, devices: list[dict]) -> None:
        """Match the configured addresses with the pumps of the account."""
        if not self._unbound_hosts:
            return
        known = {d.get("did"): d for d in devices}
        for host in list(self._unbound_hosts):
            info = await async_discover(host)
            if info is None:
                _LOGGER.debug("No pump answered locally at %s", host)
                continue
            did = info["did"]
            device = known.get(did)
            if device is None:
                _LOGGER.warning(
                    "The pump at %s (did %s) is not on this account: ignored",
                    host,
                    did,
                )
                self._unbound_hosts.remove(host)
                continue
            schema = await self._async_schema(device.get("product_key") or "")
            if schema is None:
                continue
            self._local[did] = LocalPump(host, schema)
            if device.get("product_key") == SMARTDRIFT_PRODUCT_KEY:
                self._local_writes.add(did)
            self._unbound_hosts.remove(host)
            _LOGGER.info("[Aqua Medic] Local access to %s at %s", did, host)

    async def _async_schema(self, product_key: str) -> LocalSchema | None:
        """Datapoint layout of a product, fetched once from the cloud."""
        if product_key in self._schemas:
            return self._schemas[product_key]
        try:
            schema = LocalSchema(await self._client.get_datapoints(product_key))
        except (AquaMedicConnectionError, AquaMedicAuthError, LocalError) as exc:
            _LOGGER.warning("No datapoint layout for %s: %s", product_key, exc)
            return None
        self._schemas[product_key] = schema
        return schema

    async def _async_read_local(self, did: str, data: AquaMedicDeviceData) -> None:
        """Replace the cloud values of a pump by the ones it reports itself."""
        pump = self._local.get(did)
        if pump is None:
            return
        try:
            values = await pump.async_read()
        except LocalError as exc:
            if did not in self._local_failing:
                _LOGGER.warning(
                    "Local read of %s at %s failed (%s): using the cloud",
                    data.name,
                    pump.host,
                    exc,
                )
                self._local_failing.add(did)
            return
        if did in self._local_failing:
            _LOGGER.info("[Aqua Medic] Local access to %s is back", data.name)
            self._local_failing.discard(did)
        data.attrs.update(values)
        data.is_online = True
        data.local = True

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
            # A pump reachable on the LAN keeps working while the cloud is down.
            if not (self._local and self._devices_cache):
                raise UpdateFailed(f"Failed to fetch device list: {exc}") from exc
            devices = self._devices_cache
        else:
            self._devices_cache = devices
            await self._async_bind_local(devices)

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
            await self._async_read_local(did, result[did])
            self._apply_pending(did, result[did].attrs)
            _LOGGER.debug(
                "Updated %s (%s): %s",
                result[did].name,
                did,
                result[did].attrs,
            )

        return result
