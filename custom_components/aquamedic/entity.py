"""Base entity class for Aqua Medic integration."""

from __future__ import annotations

from collections.abc import Callable
from functools import cached_property
from typing import Any

from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DC_RUNNER_PRODUCT_KEY, DC_RUNNER_SERIES_PRODUCT_KEY, DOMAIN
from .coordinator import AquaMedicCoordinator, AquaMedicDeviceData
from .maintenance import (
    PUMP_ROLE_UNKNOWN,
    MaintenanceStore,
    MaintenanceTask,
    get_store,
    role_is_user_defined,
)

# Product keys handled as the "DC Runner" line — return-pump and skimmer
# variants share the DC Runner series firmware, and the speculative legacy PK
# is also part of the DC Runner family branding.
_DC_RUNNER_MODEL_PRODUCT_KEYS = frozenset(
    {DC_RUNNER_PRODUCT_KEY, DC_RUNNER_SERIES_PRODUCT_KEY}
)


def resolve_model(product_key: str | None) -> str:
    """Return the HA-visible model label for a given Gizwits product key.

    Shared by AquaMedicEntity and AquaMedicLocalSwitchEntity (which cannot
    inherit from AquaMedicEntity because of MRO conflicts with SwitchEntity).
    """
    if product_key in _DC_RUNNER_MODEL_PRODUCT_KEYS:
        return "DC Runner"
    return "SmartDrift"


def resolve_model_id(product_key: str | None, role: str | None) -> str | None:
    """Return the device registry ``model_id`` carrying the declared pump role.

    The DC Runner return pump and the DC Skimmer are both registered with the
    model "DC Runner" (see resolve_model()); what tells them apart is the role
    the user declares through the ``pump_role`` select. That select is an
    entity: once the device is disabled in Home Assistant it has no state and
    is not even listed to the frontend, so ha-reef-card can no longer tell
    which picture to draw behind its "disabled" banner.

    The device registry entry, on the other hand, stays visible while the
    device is disabled. Publishing the role there as ``model_id`` ("return" or
    "skimmer") gives the card a value that survives the disabling.

    Returns None when the product key is not ambiguous, or when the role has
    not been declared yet.
    """
    if not role_is_user_defined(product_key):
        return None
    if not role or role == PUMP_ROLE_UNKNOWN:
        return None
    return role


def build_device_info(coordinator: Any, did: str) -> DeviceInfo:
    """Build the DeviceInfo of a device from the coordinator data.

    Shared by AquaMedicEntity and AquaMedicLocalSwitchEntity so every entity
    of a device registers it with the same model and the same ``model_id``.
    """
    data = getattr(coordinator, "data", None)
    dev = data.get(did) if data else None
    product_key = dev.product_key if dev else None
    # The role store is only consulted for the ambiguous product keys, so a
    # SmartDrift never triggers the lazy creation of a fallback store.
    role = (
        get_store(coordinator).get_role(did)
        if role_is_user_defined(product_key)
        else None
    )
    return DeviceInfo(
        identifiers={(DOMAIN, did)},
        name=dev.name if dev else did,
        manufacturer="Aqua Medic",
        model=resolve_model(product_key),
        model_id=resolve_model_id(product_key, role),
    )


class ReefRoleMixin:
    """Expose `translation_key` as a stable `reef_role` state attribute.

    The attribute name is deliberately shared with ha-reefbeat-component:
    the ha-reef-card maintenance view scans `hass.states` for entities whose
    `reef_role` starts with "maint_", so publishing the same contract here is
    all it takes for Aqua Medic tasks to show up in the same view.

    This mixin must come FIRST in the MRO so its `extra_state_attributes`
    property wins over the default `Entity` one while still picking up the
    `_attr_extra_state_attributes` set by subclasses.
    """

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        base = getattr(self, "_attr_extra_state_attributes", None) or {}
        tk = getattr(self, "translation_key", None)
        if tk:
            return {**base, "reef_role": tk}
        return dict(base) if base else None


class AquaMedicEntity(CoordinatorEntity[AquaMedicCoordinator]):
    """Base class for all Aqua Medic entities."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: AquaMedicCoordinator,
        did: str,
        unique_suffix: str,
    ) -> None:
        super().__init__(coordinator)
        self._did = did
        self._attr_unique_id = f"{did}_{unique_suffix}"

    # ── Helpers ───────────────────────────────────────────────────────────────

    @property
    def _device(self) -> AquaMedicDeviceData | None:
        """Return the coordinator data for this device."""
        return self.coordinator.data.get(self._did) if self.coordinator.data else None

    def _gizwits_value(self, attr: str, default=None):
        """Read one Gizwits attribute value from coordinator data.

        Named _gizwits_value (not _attr_value) to avoid collision with
        HA's internal _attr_* namespace.
        """
        dev = self._device
        return dev.get(attr, default) if dev else default

    @cached_property
    def device_info(self) -> DeviceInfo:  # type: ignore[reportIncompatibleVariableOverride]
        """Build DeviceInfo from coordinator device data."""
        return build_device_info(self.coordinator, self._did)

    # available is intentionally NOT overridden here.
    # Each platform entity overrides it directly with # type: ignore[override]
    # to avoid the cached_property vs property conflict that Pyright reports
    # when the override is placed in an intermediate base class.


class AquaMedicMaintenanceEntity(ReefRoleMixin, AquaMedicEntity):  # type: ignore[misc]
    """Common plumbing for the three maintenance entities of a task.

    The action button, the interval number and the notification switch all
    share the same (device, task) binding, the same persistent store and the
    same refresh-on-store-change lifecycle. Only the translation_key suffix
    and the behaviour differ, so everything else lives here.

    `available` is intentionally NOT overridden here (see the note above):
    each concrete entity declares it, and they all return True — maintenance
    bookkeeping is local, so it stays usable while the cloud is unreachable.
    """

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: AquaMedicCoordinator,
        did: str,
        task: MaintenanceTask,
        unique_suffix: str,
        translation_key: str,
    ) -> None:
        super().__init__(coordinator, did, unique_suffix)
        self._task = task
        self._attr_translation_key = translation_key
        self._unsub: Callable[[], None] | None = None

    @property
    def _store(self) -> MaintenanceStore:
        """Return the config entry's MaintenanceStore."""
        return get_store(self.coordinator)

    # ---- lifecycle -------------------------------------------------------

    def _on_store_change(self) -> None:
        """Refresh the entity when its stored state changed.

        Overridden by the switch, which mirrors the stored value into
        `_attr_is_on` before writing the state.
        """
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()

        @callback
        def _changed() -> None:
            self._on_store_change()

        self._unsub = self._store.async_add_listener(
            self._did, self._task.key, _changed
        )

    async def async_will_remove_from_hass(self) -> None:
        if self._unsub is not None:
            self._unsub()
            self._unsub = None
        await super().async_will_remove_from_hass()
