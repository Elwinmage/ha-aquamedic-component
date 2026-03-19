"""Base entity class for Aqua Medic integration."""

from __future__ import annotations

from functools import cached_property

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import AquaMedicCoordinator, AquaMedicDeviceData


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
        return DeviceInfo(
            identifiers={(DOMAIN, self._did)},
            name=name,
            manufacturer="Aqua Medic",
            model="SmartDrift",
        )

    # available is intentionally NOT overridden here.
    # Each platform entity overrides it directly with # type: ignore[override]
    # to avoid the cached_property vs property conflict that Pyright reports
    # when the override is placed in an intermediate base class.
