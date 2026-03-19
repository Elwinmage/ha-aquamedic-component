"""Number platform for Aqua Medic SmartDrift pumps."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DC_RUNNER_PRODUCT_KEY, DOMAIN, SMARTDRIFT_PRODUCT_KEY
from .coordinator import AquaMedicCoordinator
from .entity import AquaMedicEntity

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class AquaMedicNumberDescription(NumberEntityDescription):
    attr: str = ""
    gated_by_0_10v: bool = False


NUMBER_DESCRIPTIONS: tuple[AquaMedicNumberDescription, ...] = (
    AquaMedicNumberDescription(
        key="flow",
        translation_key="flow",
        attr="Flow",
        native_min_value=0,
        native_max_value=100,
        native_step=1,
        native_unit_of_measurement="%",
        icon="mdi:water-percent",
        mode=NumberMode.SLIDER,
        gated_by_0_10v=True,
    ),
    AquaMedicNumberDescription(
        key="frequency",
        translation_key="frequency",
        attr="Frequency",
        native_min_value=0,
        native_max_value=100,
        native_step=1,
        native_unit_of_measurement="%",
        icon="mdi:sine-wave",
        mode=NumberMode.SLIDER,
    ),
    AquaMedicNumberDescription(
        key="feed_time",
        translation_key="feed_time",
        attr="FeedTime",
        native_min_value=1,
        native_max_value=60,
        native_step=1,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        device_class=NumberDeviceClass.DURATION,
        icon="mdi:timer-sand",
        mode=NumberMode.BOX,
        entity_category=EntityCategory.CONFIG,
    ),
)

# DC Runner: single speed control — attr confirmed from working integration
# min=30 enforced: below 30% the DC Runner motor may stall
DC_RUNNER_NUMBER_DESCRIPTIONS: tuple[AquaMedicNumberDescription, ...] = (
    AquaMedicNumberDescription(
        key="flow",
        translation_key="flow",
        attr="Flow",
        native_min_value=30,
        native_max_value=100,
        native_step=1,
        native_unit_of_measurement="%",
        icon="mdi:water-percent",
        mode=NumberMode.SLIDER,
        gated_by_0_10v=True,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: AquaMedicCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[NumberEntity] = []
    for did, dev in (coordinator.data or {}).items():
        if dev.product_key == SMARTDRIFT_PRODUCT_KEY:
            descs = NUMBER_DESCRIPTIONS
        elif dev.product_key == DC_RUNNER_PRODUCT_KEY:
            descs = DC_RUNNER_NUMBER_DESCRIPTIONS
        else:
            continue
        for desc in descs:
            entities.append(AquaMedicNumberEntity(coordinator, did, desc))
    async_add_entities(entities)


class AquaMedicNumberEntity(AquaMedicEntity, NumberEntity):  # type: ignore[misc]
    """Numeric entity backed by a Gizwits uint8 attribute.

    Flow becomes unavailable when the 0-10V switch is ON.
    """

    def __init__(
        self,
        coordinator: AquaMedicCoordinator,
        did: str,
        description: AquaMedicNumberDescription,
    ) -> None:
        super().__init__(coordinator, did, description.key)
        self.entity_description = description
        self._desc = description

    @property
    def available(self) -> bool:  # type: ignore[override]
        dev = self._device
        if not (
            self.coordinator.last_update_success
            and dev is not None
            and dev.is_online
        ):
            return False
        if self._desc.gated_by_0_10v and self.coordinator.get_control_0_10v(self._did):
            return False
        return True

    @property
    def native_value(self) -> float | None:  # type: ignore[reportIncompatibleVariableOverride]
        val = self._gizwits_value(self._desc.attr)
        return float(val) if val is not None else None

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator._client.control_device(
            self._did, {self._desc.attr: int(value)}
        )
        await self.coordinator.async_request_refresh()
