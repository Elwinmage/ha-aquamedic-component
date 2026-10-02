"""Sensor platform for Aqua Medic pumps — time-slot schedule."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import AquaMedicCoordinator
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


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: AquaMedicCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[SensorEntity] = []
    for did, dev in (coordinator.data or {}).items():
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
