"""Binary sensor platform for Aqua Medic SmartDrift pumps — fault indicators."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, SMARTDRIFT_PRODUCT_KEY
from .coordinator import AquaMedicCoordinator
from .entity import AquaMedicEntity

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class AquaMedicFaultDescription(BinarySensorEntityDescription):
    attr: str = ""


FAULT_DESCRIPTIONS: tuple[AquaMedicFaultDescription, ...] = (
    AquaMedicFaultDescription(
        key="fault_overcurrent",
        translation_key="fault_overcurrent",
        attr="Fault_Overcurrent",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:current-ac",
    ),
    AquaMedicFaultDescription(
        key="fault_overvoltage",
        translation_key="fault_overvoltage",
        attr="Fault_Overvoltage",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:lightning-bolt",
    ),
    AquaMedicFaultDescription(
        key="fault_overtemp",
        translation_key="fault_overtemp",
        attr="Fault_OverTemp",
        device_class=BinarySensorDeviceClass.HEAT,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:thermometer-alert",
    ),
    AquaMedicFaultDescription(
        key="fault_undervoltage",
        translation_key="fault_undervoltage",
        attr="Fault_Undervoltage",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:battery-alert",
    ),
    AquaMedicFaultDescription(
        key="fault_lockedrotor",
        translation_key="fault_lockedrotor",
        attr="Fault_Lockedrotor",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:rotate-right-variant",
    ),
    AquaMedicFaultDescription(
        key="fault_no_liveload",
        translation_key="fault_no_liveload",
        attr="Fault_no_liveload",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:water-off",
    ),
    AquaMedicFaultDescription(
        key="fault_uart",
        translation_key="fault_uart",
        attr="Fault_UART",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:serial-port",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: AquaMedicCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[BinarySensorEntity] = []
    for did, dev in (coordinator.data or {}).items():
        if dev.product_key != SMARTDRIFT_PRODUCT_KEY:
            continue
        for desc in FAULT_DESCRIPTIONS:
            entities.append(AquaMedicFaultEntity(coordinator, did, desc))
    async_add_entities(entities)


class AquaMedicFaultEntity(AquaMedicEntity, BinarySensorEntity):  # type: ignore[misc]
    """Binary sensor that is ON when a fault is active."""

    def __init__(
        self,
        coordinator: AquaMedicCoordinator,
        did: str,
        description: AquaMedicFaultDescription,
    ) -> None:
        super().__init__(coordinator, did, description.key)
        self.entity_description = description
        self._desc = description

    @property
    def available(self) -> bool:  # type: ignore[override]
        dev = self._device
        # is_online is bool | None: None means "unknown" (e.g. first poll via Gateway)
        # → treat as available (optimistic); only False means explicitly offline.
        return bool(
            self.coordinator.last_update_success
            and dev is not None
            and dev.is_online is not False
        )

    @property
    def is_on(self) -> bool | None:  # type: ignore[reportIncompatibleVariableOverride]
        val = self._gizwits_value(self._desc.attr)
        return bool(val) if val is not None else None
