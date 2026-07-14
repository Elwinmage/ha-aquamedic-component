"""Base entity class for Aqua Medic integration."""

from __future__ import annotations

from functools import cached_property

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DC_RUNNER_PRODUCT_KEY, DC_RUNNER_SERIES_PRODUCT_KEY, DOMAIN
from .coordinator import AquaMedicCoordinator, AquaMedicDeviceData


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
        dev = self._device
        name = dev.name if dev else self._did
        model = resolve_model(dev.product_key if dev else None)
        return DeviceInfo(
            identifiers={(DOMAIN, self._did)},
            name=name,
            manufacturer="Aqua Medic",
            model=model,
        )

    # available is intentionally NOT overridden here.
    # Each platform entity overrides it directly with # type: ignore[override]
    # to avoid the cached_property vs property conflict that Pyright reports
    # when the override is placed in an intermediate base class.
