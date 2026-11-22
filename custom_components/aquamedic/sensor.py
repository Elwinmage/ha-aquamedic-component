"""Sensor platform for Aqua Medic pumps — time-slot schedule."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, UnitOfTime, UnitOfVolume
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import AquaMedicCoordinator
from .doser import (
    DOSE_SLOT_COUNT,
    channel_count,
    channels_of,
    daily_total_ml,
    decode_table,
    has_table,
    interval_attr,
    table_attr,
    timer_attr,
)
from .entity import AquaMedicEntity, ReefRoleMixin
from .schedule import (
    SLOT_COUNT,
    ScheduleLayout,
    decode_schedule,
    has_schedule,
    layout_for,
)

_LOGGER = logging.getLogger(__name__)

SCHEDULE_DESCRIPTION = SensorEntityDescription(
    key="schedule",
    translation_key="schedule",
    icon="mdi:calendar-clock",
)

# Reefdoser EVO 5: time the pump took on its last calibration run, in seconds.
CALIBRATION_TIME_DESCRIPTION = SensorEntityDescription(
    key="calibration_time",
    translation_key="calibration_time",
    icon="mdi:timer-sand",
    device_class=SensorDeviceClass.DURATION,
    native_unit_of_measurement=UnitOfTime.SECONDS,
    entity_category=EntityCategory.DIAGNOSTIC,
)

# Suffix of the dose-schedule sensor unique_id: "<did>_doser_schedule_<channel>"
# (parsed back by services.py to find the pump and the channel to program).
DOSER_SCHEDULE_KEY = "doser_schedule"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: AquaMedicCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[SensorEntity] = []
    for did, dev in (coordinator.data or {}).items():
        if channels := channel_count(dev.product_key, dev.attrs):
            entities.extend(
                AquaMedicDoserScheduleSensor(coordinator, did, channel)
                for channel in channels_of(channels)
            )
            entities.append(
                AquaMedicDoserCalibrationTimeSensor(
                    coordinator, did, CALIBRATION_TIME_DESCRIPTION
                )
            )
            continue
        layout = layout_for(dev.product_key)
        if layout is None:
            continue
        entities.append(
            AquaMedicScheduleSensor(coordinator, did, SCHEDULE_DESCRIPTION, layout)
        )
    async_add_entities(entities)


class AquaMedicScheduleSensor(ReefRoleMixin, AquaMedicEntity, SensorEntity):  # type: ignore[misc]
    """Time-slot program of a pump, decoded from its ``AutoTimeNN`` datapoints.

    The state is the number of programmed slots; the program itself is in
    the ``schedule`` attribute, one entry per slot::

        {"slot": 0, "start": 480, "end": 720, "mode": "auto", "value": 60}

    ``start`` / ``end`` are minutes since midnight. SmartDrift slots also
    carry ``frequency`` and ``tide``. The pump only follows the program while
    its timer switch is on.

    The entity is created for every pump that has a scheduler, even when the
    pump is offline at setup, and simply stays unavailable until the cloud
    reports the slot datapoints. Writing goes through the
    ``aquamedic.set_schedule`` service, which targets this entity.
    """

    def __init__(
        self,
        coordinator: AquaMedicCoordinator,
        did: str,
        description: SensorEntityDescription,
        layout: ScheduleLayout,
    ) -> None:
        super().__init__(coordinator, did, description.key)
        self.entity_description = description
        self._layout = layout

    @property
    def did(self) -> str:
        """Gizwits device id this schedule belongs to."""
        return self._did

    @property
    def layout(self) -> ScheduleLayout:
        """Slot layout of the pump firmware."""
        return self._layout

    def _attrs(self) -> dict[str, Any]:
        dev = self._device
        return dev.attrs if dev else {}

    @property
    def available(self) -> bool:  # type: ignore[override]
        # The last program received is still the one stored in the pump when
        # it goes offline, so only a missing program makes this unavailable.
        return bool(self.coordinator.last_update_success) and has_schedule(
            self._attrs()
        )

    @property
    def native_value(self) -> int | None:  # type: ignore[reportIncompatibleVariableOverride]
        attrs = self._attrs()
        if not has_schedule(attrs):
            return None
        return len(decode_schedule(attrs, self._layout))

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:  # pyright: ignore[reportIncompatibleVariableOverride]
        attrs = self._attrs()
        self._attr_extra_state_attributes = {
            "schedule": decode_schedule(attrs, self._layout)
            if has_schedule(attrs)
            else [],
            "kind": self._layout.kind,
            "modes": list(self._layout.modes),
            "max_slots": SLOT_COUNT,
            "min_value": self._layout.min_value,
            "timer_on": bool(attrs.get("TimerON")) if "TimerON" in attrs else None,
        }
        # ReefRoleMixin adds reef_role on top of what is published here.
        return super().extra_state_attributes  # type: ignore[misc]


class AquaMedicDoserScheduleSensor(ReefRoleMixin, AquaMedicEntity, SensorEntity):  # type: ignore[misc]
    """Dose program of one Reefdoser EVO 5 channel.

    The state is the volume, in ml, dosed in one day by the channel. The
    program itself is in the ``schedule`` attribute, one entry per dose::

        {"slot": 0, "time": 915, "amount_ml": 2}

    ``time`` is minutes since midnight. The pump only follows the program while
    the channel schedule switch (``timer_on`` attribute) is on. Writing goes
    through the ``aquamedic.set_doser_schedule`` service, which targets this
    entity.
    """

    _attr_device_class = SensorDeviceClass.VOLUME
    _attr_native_unit_of_measurement = UnitOfVolume.MILLILITERS
    _attr_icon = "mdi:eyedropper-variant"
    _attr_translation_key = "doser_schedule"

    def __init__(
        self,
        coordinator: AquaMedicCoordinator,
        did: str,
        channel: int,
    ) -> None:
        super().__init__(coordinator, did, f"{DOSER_SCHEDULE_KEY}_{channel}")
        self._channel = channel
        self._attr_translation_placeholders = {"channel": str(channel)}

    @property
    def did(self) -> str:
        """Gizwits device id this schedule belongs to."""
        return self._did

    @property
    def channel(self) -> int:
        """Channel number (1-5) this schedule belongs to."""
        return self._channel

    def _attrs(self) -> dict[str, Any]:
        dev = self._device
        return dev.attrs if dev else {}

    @property
    def available(self) -> bool:  # type: ignore[override]
        # The table last received is still the one stored in the pump when it
        # goes offline, so only a missing table makes this unavailable.
        return bool(self.coordinator.last_update_success) and has_table(
            self._attrs(), self._channel
        )

    @property
    def native_value(self) -> int | None:  # type: ignore[reportIncompatibleVariableOverride]
        attrs = self._attrs()
        if not has_table(attrs, self._channel):
            return None
        return daily_total_ml(decode_table(attrs[table_attr(self._channel)]))

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:  # pyright: ignore[reportIncompatibleVariableOverride]
        attrs = self._attrs()
        doses = (
            decode_table(attrs[table_attr(self._channel)])
            if has_table(attrs, self._channel)
            else []
        )
        timer = timer_attr(self._channel)
        interval = interval_attr(self._channel)
        self._attr_extra_state_attributes = {
            "schedule": doses,
            "channel": self._channel,
            "max_slots": DOSE_SLOT_COUNT,
            "timer_on": bool(attrs[timer]) if timer in attrs else None,
            "interval": attrs.get(interval),
        }
        # ReefRoleMixin adds reef_role on top of what is published here.
        return super().extra_state_attributes  # type: ignore[misc]


class AquaMedicDoserCalibrationTimeSensor(AquaMedicEntity, SensorEntity):  # type: ignore[misc]
    """Calibration time (``time1``) reported by a Reefdoser EVO 5."""

    def __init__(
        self,
        coordinator: AquaMedicCoordinator,
        did: str,
        description: SensorEntityDescription,
    ) -> None:
        super().__init__(coordinator, did, description.key)
        self.entity_description = description

    @property
    def available(self) -> bool:  # type: ignore[override]
        dev = self._device
        return bool(
            self.coordinator.last_update_success
            and dev is not None
            and dev.is_online is not False
            and "time1" in dev.attrs
        )

    @property
    def native_value(self) -> int | None:  # type: ignore[reportIncompatibleVariableOverride]
        val = self._gizwits_value("time1")
        return int(val) if val is not None else None
