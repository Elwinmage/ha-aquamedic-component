"""Maintenance tracking for Aqua Medic devices.

This module centralises:

- The static catalogue of maintenance tasks per pump role (see ``TASKS`` and
  ``tasks_for(...)``).
- The persistent storage of "last reset" timestamps, per-task interval
  overrides, per-task notification flags and the user-declared pump role, via
  Home Assistant's ``helpers.storage.Store`` (one JSON file per config entry,
  under ``.storage/aquamedic_maintenance_<entry_id>``).
- The helpers exposed to entities (button, number, switch, select) to read and
  write that state, plus the derived values ``days_left`` / ``overdue``.

Design notes
------------
- One ``MaintenanceStore`` per config entry, created in ``async_setup_entry``
  and attached to the coordinator as ``coordinator.maintenance`` so platforms
  can fetch it without going through ``hass.data`` again.
- A maintenance "instance" is identified by a pair ``(did, task_key)``. Unlike
  the Red Sea integration there is no sub-device here: one Gizwits device is
  one pump.
- The DC Runner return pump and the DC Skimmer share the same firmware and the
  same Gizwits product key, so the API cannot tell them apart. The user
  declares the role once through the ``pump_role`` select; the value is stored
  here (and not in a RestoreEntity) because the platforms need to read it at
  setup time, before any entity exists.
- Entity attributes are named ``reef_role`` / ``task_key`` / ``days_left`` on
  purpose: this is the same contract as ha-reefbeat-component, which lets the
  ha-reef-card maintenance view pick these tasks up without any card-side
  change.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Final

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.storage import Store

from .const import (
    DC_RUNNER_PRODUCT_KEY,
    DC_RUNNER_SERIES_PRODUCT_KEY,
    SMARTDRIFT_PRODUCT_KEY,
)

_LOGGER = logging.getLogger(__name__)

# Storage format: bump when the JSON shape changes incompatibly.
STORAGE_VERSION: Final[int] = 1
STORAGE_KEY_TPL: Final[str] = "aquamedic_maintenance_{entry_id}"

# Stable role prefix for the entity attribute `reef_role`, used by the
# alert blueprint and by the ha-reef-card maintenance view.
ROLE_PREFIX: Final[str] = "maint_"

# ── Pump roles ────────────────────────────────────────────────────────────────
# "unknown" is the default: as long as the user has not declared what the pump
# actually is, no maintenance task is created for DC Runner series devices.
PUMP_ROLE_UNKNOWN: Final[str] = "unknown"
PUMP_ROLE_RETURN: Final[str] = "return"
PUMP_ROLE_SKIMMER: Final[str] = "skimmer"
# Implicit role of every EcoDrift / SmartDrift: it is a flow pump, and its
# product key is unambiguous, so the user is never asked.
PUMP_ROLE_DRIFT: Final[str] = "drift"

PUMP_ROLE_OPTIONS: Final[tuple[str, ...]] = (
    PUMP_ROLE_UNKNOWN,
    PUMP_ROLE_RETURN,
    PUMP_ROLE_SKIMMER,
)

# Product keys whose role cannot be derived from the API (see const.py).
ROLE_AMBIGUOUS_PRODUCT_KEYS: Final[frozenset[str]] = frozenset(
    {DC_RUNNER_PRODUCT_KEY, DC_RUNNER_SERIES_PRODUCT_KEY}
)


# =============================================================================
# Task catalogue
# =============================================================================


@dataclass(frozen=True, slots=True)
class MaintenanceTask:
    """Definition of a single maintenance task.

    Attributes
    ----------
    key:
        Stable identifier, used in the entity unique_id and the storage key.
        Must not change once released, or users lose their reset history.
    translation_key:
        translation_key of the action button. Also exposed as `reef_role`
        through ReefRoleMixin, so blueprints and cards can target the task
        independently of the install language.
    default_days / min_days / max_days:
        Interval bounds in days. Aqua Medic publishes no numeric interval
        ("clean regularly", "from time to time"), so these come from reef
        keeping practice and are widened around the default.
    unit:
        Display unit of the configuration number entity: "days", "weeks" or
        "months". Storage always stays in days so `days_left` is comparable
        across tasks and across integrations.
    """

    key: str
    translation_key: str
    default_days: int
    min_days: int
    max_days: int
    icon: str = "mdi:wrench-check"
    unit: str = "weeks"


# EcoDrift / SmartDrift x.1 / x.3 flow pumps.
_DRIFT_TASKS: Final[tuple[MaintenanceTask, ...]] = (
    MaintenanceTask(
        key="drift_rotor_clean",
        translation_key="maint_drift_rotor_clean",
        default_days=60,  # 2 months
        min_days=30,
        max_days=90,
        icon="mdi:fan",
        unit="months",
    ),
    MaintenanceTask(
        key="drift_descale",
        translation_key="maint_drift_descale",
        default_days=180,  # 6 months
        min_days=90,
        max_days=270,
        icon="mdi:spray-bottle",
        unit="months",
    ),
    MaintenanceTask(
        key="drift_impeller_replace",
        translation_key="maint_drift_impeller_replace",
        default_days=540,  # 18 months
        min_days=360,
        max_days=730,
        icon="mdi:cog-refresh",
        unit="months",
    ),
)

# DC Runner series used as a return pump.
_RETURN_TASKS: Final[tuple[MaintenanceTask, ...]] = (
    MaintenanceTask(
        key="runner_strainer_clean",
        translation_key="maint_runner_strainer_clean",
        default_days=42,  # 6 weeks
        min_days=21,
        max_days=63,
        icon="mdi:filter-variant",
        unit="weeks",
    ),
    MaintenanceTask(
        key="runner_impeller_clean",
        translation_key="maint_runner_impeller_clean",
        default_days=120,  # 4 months
        min_days=60,
        max_days=180,
        icon="mdi:engine",
        unit="months",
    ),
    MaintenanceTask(
        key="runner_impeller_replace",
        translation_key="maint_runner_impeller_replace",
        default_days=540,  # 18 months
        min_days=360,
        max_days=730,
        icon="mdi:cog-refresh",
        unit="months",
    ),
)

# DC Runner series used as a skimmer pump (needle wheel).
_SKIMMER_TASKS: Final[tuple[MaintenanceTask, ...]] = (
    MaintenanceTask(
        key="skimmer_cup_clean",
        translation_key="maint_skimmer_cup_clean",
        default_days=14,  # 2 weeks
        min_days=7,
        max_days=28,
        icon="mdi:cup-water",
        unit="weeks",
    ),
    MaintenanceTask(
        key="skimmer_venturi_clean",
        translation_key="maint_skimmer_venturi_clean",
        default_days=28,  # 4 weeks
        min_days=14,
        max_days=56,
        icon="mdi:weather-windy",
        unit="weeks",
    ),
    MaintenanceTask(
        key="skimmer_needle_wheel_clean",
        translation_key="maint_skimmer_needle_wheel_clean",
        default_days=60,  # 2 months
        min_days=30,
        max_days=120,
        icon="mdi:fan",
        unit="months",
    ),
    MaintenanceTask(
        key="skimmer_body_descale",
        translation_key="maint_skimmer_body_descale",
        default_days=180,  # 6 months
        min_days=90,
        max_days=365,
        icon="mdi:spray-bottle",
        unit="months",
    ),
    MaintenanceTask(
        key="skimmer_needle_wheel_replace",
        translation_key="maint_skimmer_needle_wheel_replace",
        default_days=540,  # 18 months
        min_days=360,
        max_days=730,
        icon="mdi:cog-refresh",
        unit="months",
    ),
)

# Catalogue keyed by pump role.
TASKS: Final[dict[str, tuple[MaintenanceTask, ...]]] = {
    PUMP_ROLE_DRIFT: _DRIFT_TASKS,
    PUMP_ROLE_RETURN: _RETURN_TASKS,
    PUMP_ROLE_SKIMMER: _SKIMMER_TASKS,
    # An undeclared DC Runner gets no task: creating both sets and letting the
    # user mute half of them would pollute the maintenance view.
    PUMP_ROLE_UNKNOWN: (),
}


def role_is_user_defined(product_key: str | None) -> bool:
    """Return True when the pump role must be declared by the user."""
    return product_key in ROLE_AMBIGUOUS_PRODUCT_KEYS


def tasks_for(role: str) -> tuple[MaintenanceTask, ...]:
    """Return the maintenance task list for a pump role, or empty."""
    return TASKS.get(role, ())


def tasks_for_device(product_key: str | None, role: str) -> tuple[MaintenanceTask, ...]:
    """Return the task list for a device, given its product key and role.

    SmartDrift / EcoDrift never asks the user: the product key is enough.
    """
    if product_key == SMARTDRIFT_PRODUCT_KEY:
        return _DRIFT_TASKS
    if role_is_user_defined(product_key):
        return tasks_for(role)
    return ()


def all_task_keys() -> tuple[str, ...]:
    """Return every catalogue task key (used by tests and tooling)."""
    return tuple(task.key for tasks in TASKS.values() for task in tasks)


# =============================================================================
# Persistent storage
# =============================================================================


# Storage shape (JSON):
# {
#   "instances": {
#     "<did>:<task_key>": {
#       "last_reset": "2026-08-13T10:30:00+00:00",  # ISO-8601 UTC
#       "interval_days": 60,                        # optional override
#       "notify": false                             # only stored when disabled
#     }
#   },
#   "roles": {"<did>": "skimmer"}                   # only stored when declared
# }


def _instance_id(did: str, task_key: str) -> str:
    """Build the storage key for a maintenance instance."""
    return f"{did}:{task_key}"


@dataclass(slots=True)
class MaintenanceState:
    """In-memory state for a single maintenance instance."""

    last_reset: datetime | None = None
    interval_days: int | None = None  # None means "use task.default_days"
    # Whether the alert blueprint should notify when this instance becomes
    # overdue. Defaults to True; only the "disabled" value is persisted.
    notify: bool = True


class MaintenanceStore:
    """Persistent maintenance state for one config entry.

    Wraps ``helpers.storage.Store`` with a typed API and a small listener
    mechanism so entities refresh as soon as the state changes.
    """

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self._hass = hass
        self._store: Store[dict[str, Any]] = Store(
            hass, STORAGE_VERSION, STORAGE_KEY_TPL.format(entry_id=entry_id)
        )
        self._data: dict[str, MaintenanceState] = {}
        self._roles: dict[str, str] = {}
        self._listeners: dict[str, list[Callable[[], None]]] = {}
        self._loaded = False

    # ---- loading / saving ------------------------------------------------

    async def async_load(self) -> None:
        """Load persisted state (no-op if already loaded)."""
        if self._loaded:
            return
        raw = await self._store.async_load() or {}
        for iid, payload in (raw.get("instances") or {}).items():
            self._data[iid] = MaintenanceState(
                last_reset=_parse_dt(payload.get("last_reset")),
                interval_days=payload.get("interval_days"),
                # Absent key means "never disabled" -> notifications on.
                notify=payload.get("notify", True) is not False,
            )
        for did, role in (raw.get("roles") or {}).items():
            if role in PUMP_ROLE_OPTIONS:
                self._roles[did] = role
        self._loaded = True
        _LOGGER.debug(
            "MaintenanceStore loaded %d instance(s), %d role(s)",
            len(self._data),
            len(self._roles),
        )

    async def _async_save(self) -> None:
        out_instances: dict[str, dict[str, Any]] = {}
        for iid, state in self._data.items():
            entry: dict[str, Any] = {}
            if state.last_reset is not None:
                entry["last_reset"] = state.last_reset.isoformat()
            if state.interval_days is not None:
                entry["interval_days"] = state.interval_days
            # Persist only the non-default value to keep the store lean.
            if not state.notify:
                entry["notify"] = False
            if entry:
                out_instances[iid] = entry
        roles = {
            did: role for did, role in self._roles.items() if role != PUMP_ROLE_UNKNOWN
        }
        await self._store.async_save({"instances": out_instances, "roles": roles})

    # ---- public read API -------------------------------------------------

    def get_state(self, did: str, task_key: str) -> MaintenanceState:
        """Return the state for an instance (auto-created if absent)."""
        iid = _instance_id(did, task_key)
        state = self._data.get(iid)
        if state is None:
            state = MaintenanceState()
            self._data[iid] = state
        return state

    def get_last_reset(self, did: str, task_key: str) -> datetime | None:
        """Return the last reset timestamp, or None when never reset."""
        return self.get_state(did, task_key).last_reset

    def get_interval(self, did: str, task_key: str, default: int) -> int:
        """Return the configured interval in days, or the task default."""
        val = self.get_state(did, task_key).interval_days
        return val if val is not None else default

    def get_notify(self, did: str, task_key: str) -> bool:
        """Return True when overdue alerts are enabled for this instance."""
        return self.get_state(did, task_key).notify

    def get_role(self, did: str) -> str:
        """Return the declared pump role, or PUMP_ROLE_UNKNOWN."""
        return self._roles.get(did, PUMP_ROLE_UNKNOWN)

    # ---- public write API ------------------------------------------------

    async def async_reset(self, did: str, task_key: str) -> datetime:
        """Mark a maintenance task done now, persist, and notify listeners."""
        now = datetime.now(timezone.utc)
        state = self.get_state(did, task_key)
        state.last_reset = now
        await self._async_save()
        self._notify(_instance_id(did, task_key))
        return now

    async def async_set_interval(self, did: str, task_key: str, days: int) -> None:
        """Override the interval for an instance, persist, and notify."""
        state = self.get_state(did, task_key)
        state.interval_days = int(days)
        await self._async_save()
        self._notify(_instance_id(did, task_key))

    async def async_set_notify(self, did: str, task_key: str, enabled: bool) -> None:
        """Enable/disable overdue alerts for an instance, persist, and notify."""
        state = self.get_state(did, task_key)
        state.notify = bool(enabled)
        await self._async_save()
        self._notify(_instance_id(did, task_key))

    async def async_set_role(self, did: str, role: str) -> None:
        """Declare the pump role of a device, persist, and notify listeners.

        The caller is responsible for reloading the config entry: the task
        list is read at platform setup time, so entities only appear or
        disappear after a reload.
        """
        if role not in PUMP_ROLE_OPTIONS:
            raise ValueError(f"Unknown pump role: {role}")
        self._roles[did] = role
        await self._async_save()
        self._notify(_role_listener_id(did))

    # ---- listener plumbing ----------------------------------------------

    @callback
    def async_add_listener(
        self, did: str, task_key: str, cb: Callable[[], None]
    ) -> Callable[[], None]:
        """Register a no-arg callback for changes to a specific instance.

        Returns an unsubscribe callable.
        """
        return self._add_listener(_instance_id(did, task_key), cb)

    @callback
    def async_add_role_listener(
        self, did: str, cb: Callable[[], None]
    ) -> Callable[[], None]:
        """Register a no-arg callback for pump role changes of a device."""
        return self._add_listener(_role_listener_id(did), cb)

    def _add_listener(self, iid: str, cb: Callable[[], None]) -> Callable[[], None]:
        self._listeners.setdefault(iid, []).append(cb)

        def _unsub() -> None:
            lst = self._listeners.get(iid)
            if lst and cb in lst:
                lst.remove(cb)

        return _unsub

    def _notify(self, iid: str) -> None:
        for cb in list(self._listeners.get(iid, [])):
            try:
                cb()
            except Exception:  # pragma: no cover - defensive
                _LOGGER.exception("MaintenanceStore listener raised")


def _role_listener_id(did: str) -> str:
    """Build the listener key used for pump role changes."""
    return f"{did}:__role__"


def get_store(coordinator: Any) -> MaintenanceStore:
    """Return the coordinator's MaintenanceStore, lazy-creating a fallback.

    Different code paths wire the store (``async_setup_entry``) and consume it
    (the four platforms), and test fixtures do not always wire it. Rather than
    crashing a platform, build an in-memory store bound to a unique key: the
    entities stay usable, nothing is persisted, and a WARNING makes the
    misconfiguration visible.
    """
    store = getattr(coordinator, "maintenance", None)
    if store is None:
        _LOGGER.warning(
            "MaintenanceStore missing on the coordinator; using an ephemeral "
            "fallback (maintenance state will not persist across restarts)"
        )
        store = MaintenanceStore(coordinator.hass, f"fallback_{id(coordinator)}")
        coordinator.maintenance = store
    return store


# =============================================================================
# Derived calculations (pure helpers, no side effects)
# =============================================================================


def compute_days_left(
    last_reset: datetime | None, interval_days: int, now: datetime | None = None
) -> int | None:
    """Compute the number of days left before the task becomes overdue.

    Returns ``None`` when no reset has ever been recorded (the task is
    "pending first reset", not overdue: the user may have just installed the
    integration). Returns a negative number when overdue.
    """
    if last_reset is None:
        return None
    ref = now or datetime.now(timezone.utc)
    elapsed = (ref - last_reset).total_seconds() / 86400.0
    remaining = interval_days - elapsed
    # Floor: a partially used day still counts, in both directions.
    return int(remaining) if remaining >= 0 else -int(-remaining + 0.999999)


def is_overdue(
    last_reset: datetime | None, interval_days: int, now: datetime | None = None
) -> bool:
    """Return True when the task is past its interval."""
    dl = compute_days_left(last_reset, interval_days, now)
    return dl is not None and dl < 0


def _parse_dt(value: Any) -> datetime | None:
    """Parse an ISO-8601 string into an aware datetime, or return None."""
    if not isinstance(value, str):
        return None
    try:
        dt = datetime.fromisoformat(value)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt
