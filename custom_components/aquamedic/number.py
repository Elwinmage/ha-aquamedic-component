"""Number platform for Aqua Medic SmartDrift pumps."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import ClassVar

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

from .const import (
    DC_RUNNER_PRODUCT_KEY,
    DC_SKIMMER_PRODUCT_KEY,
    DOMAIN,
    SMARTDRIFT_PRODUCT_KEY,
)
from .coordinator import AquaMedicCoordinator
from .entity import AquaMedicEntity, AquaMedicMaintenanceEntity
from .maintenance import MaintenanceTask, get_store, tasks_for_device

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

# DC Runner return pump: single speed control (attr Flow).
# min=30 enforced: below 30% the DC Runner motor may stall.
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

# DC Skimmer numeric controls (attrs confirmed from a real datapoint capture).
# Motor_Speed: motor gear, 0 stops the motor; running range is 30-100%. min=30
# is enforced because below 30% the motor may stall — use the power switch to
# stop the pump.
DC_SKIMMER_NUMBER_DESCRIPTIONS: tuple[AquaMedicNumberDescription, ...] = (
    AquaMedicNumberDescription(
        key="motor_speed",
        translation_key="motor_speed",
        attr="Motor_Speed",
        native_min_value=30,
        native_max_value=100,
        native_step=1,
        native_unit_of_measurement="%",
        icon="mdi:speedometer",
        mode=NumberMode.SLIDER,
        gated_by_0_10v=True,
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
    AquaMedicNumberDescription(
        key="auto_gears",
        translation_key="auto_gears",
        attr="AutoGears",
        native_min_value=0,
        native_max_value=100,
        native_step=1,
        native_unit_of_measurement="%",
        icon="mdi:speedometer-medium",
        mode=NumberMode.SLIDER,
        entity_category=EntityCategory.CONFIG,
    ),
    AquaMedicNumberDescription(
        key="auto_feed_time",
        translation_key="auto_feed_time",
        attr="AutoFeedTime",
        native_min_value=1,
        native_max_value=60,
        native_step=1,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        device_class=NumberDeviceClass.DURATION,
        icon="mdi:timer-sand-complete",
        mode=NumberMode.BOX,
        entity_category=EntityCategory.CONFIG,
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
        elif dev.product_key == DC_SKIMMER_PRODUCT_KEY:
            descs = DC_SKIMMER_NUMBER_DESCRIPTIONS
        else:
            continue
        for desc in descs:
            entities.append(AquaMedicNumberEntity(coordinator, did, desc))
        # One interval slider per applicable maintenance task.
        role = get_store(coordinator).get_role(did)
        for task in tasks_for_device(dev.product_key, role):
            entities.append(AquaMedicMaintenanceIntervalNumber(coordinator, did, task))
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
            self.coordinator.last_update_success and dev is not None and dev.is_online
        ):
            return False
        return not (
            self._desc.gated_by_0_10v and self.coordinator.get_control_0_10v(self._did)
        )

    @property
    def native_value(self) -> float | None:  # type: ignore[reportIncompatibleVariableOverride]
        val = self._gizwits_value(self._desc.attr)
        return float(val) if val is not None else None

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator._client.control_device(
            self._did, {self._desc.attr: int(value)}
        )
        await self.coordinator.async_request_refresh()


class AquaMedicMaintenanceIntervalNumber(AquaMedicMaintenanceEntity, NumberEntity):  # type: ignore[misc]
    """Slider exposing the interval of one maintenance task.

    A thin facade over the persistent MaintenanceStore: `native_value` reads
    `store.get_interval(...)` and `async_set_native_value` writes it back. The
    matching button reads the same value when computing `days_left`.

    Storage is always in days; only this entity converts to and from the
    task's display unit. The unit is carried by the translation_key (and
    therefore by `reef_role`, e.g. "maint_skimmer_cup_clean_interval_weeks"),
    which is how ha-reef-card knows what the slider value means without an
    extra attribute.
    """

    _attr_icon = "mdi:calendar-range"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_mode = NumberMode.SLIDER
    _attr_native_step = 1.0
    # Intervals are inherently integer; hide the trailing ".0" in the UI.
    _attr_suggested_display_precision = 0

    # Days-per-unit conversion factors. "days" must be listed explicitly,
    # otherwise a task declared in days silently falls back to the weekly
    # factor and is stored as weeks.
    _DAYS_PER_UNIT: ClassVar[dict[str, int]] = {"days": 1, "weeks": 7, "months": 30}

    def __init__(
        self,
        coordinator: AquaMedicCoordinator,
        did: str,
        task: MaintenanceTask,
    ) -> None:
        unit = task.unit
        super().__init__(
            coordinator,
            did,
            task,
            f"maint_{task.key}_interval",
            f"{task.translation_key}_interval_{unit}",
        )
        factor = self._DAYS_PER_UNIT.get(unit, 7)
        self._unit_factor = factor
        # No native_unit_of_measurement: the unit is part of the entity name
        # via the translation_key, so the same slider works for days, weeks
        # and months without asking HA to localise a custom unit string.
        self._attr_native_min_value = float(task.min_days // factor)
        self._attr_native_max_value = float(task.max_days // factor)

    @property
    def available(self) -> bool:  # type: ignore[override]
        return True

    @property
    def native_value(self) -> float | None:  # type: ignore[reportIncompatibleVariableOverride]
        """Return the stored interval (days) converted to the display unit."""
        days = self._store.get_interval(
            self._did, self._task.key, self._task.default_days
        )
        return float(days // self._unit_factor)

    async def async_set_native_value(self, value: float) -> None:
        """Persist the slider value as days (converted from the display unit)."""
        days = round(value) * self._unit_factor
        await self._store.async_set_interval(self._did, self._task.key, days)
