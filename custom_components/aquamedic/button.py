"""Button platform for Aqua Medic SmartDrift pumps — force data refresh."""

from __future__ import annotations

import logging

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DC_SKIMMER_PRODUCT_KEY, DOMAIN, SMARTDRIFT_PRODUCT_KEY
from .coordinator import AquaMedicCoordinator
from .entity import AquaMedicEntity, AquaMedicMaintenanceEntity
from .maintenance import (
    MaintenanceTask,
    compute_days_left,
    get_store,
    tasks_for_device,
)

_LOGGER = logging.getLogger(__name__)

REFRESH_DESCRIPTION = ButtonEntityDescription(
    key="refresh",
    translation_key="refresh",
    icon="mdi:refresh",
    entity_category=EntityCategory.DIAGNOSTIC,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: AquaMedicCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[ButtonEntity] = []
    for did, dev in (coordinator.data or {}).items():
        if dev.product_key in (SMARTDRIFT_PRODUCT_KEY, DC_SKIMMER_PRODUCT_KEY):
            entities.append(
                AquaMedicRefreshButton(coordinator, did, REFRESH_DESCRIPTION)
            )
        # One action button per applicable maintenance task. The list depends
        # on the declared pump role, so an undeclared DC Runner gets none.
        role = get_store(coordinator).get_role(did)
        for task in tasks_for_device(dev.product_key, role):
            entities.append(AquaMedicMaintenanceButton(coordinator, did, task))
    async_add_entities(entities)


class AquaMedicRefreshButton(AquaMedicEntity, ButtonEntity):  # type: ignore[misc]
    """Button that forces an immediate coordinator refresh."""

    def __init__(
        self,
        coordinator: AquaMedicCoordinator,
        did: str,
        description: ButtonEntityDescription,
    ) -> None:
        super().__init__(coordinator, did, description.key)
        self.entity_description = description

    @property
    def available(self) -> bool:  # type: ignore[override]
        # Available even offline so user can force a status check.
        return self.coordinator.last_update_success

    async def async_press(self) -> None:
        _LOGGER.debug("Manual refresh requested for device %s", self._did)
        await self.coordinator.async_request_refresh()


class AquaMedicMaintenanceButton(AquaMedicMaintenanceEntity, ButtonEntity):  # type: ignore[misc]
    """Button that records a user-confirmed maintenance event.

    Pressing it stamps "now" as the last_reset of the (device, task) pair in
    the persistent MaintenanceStore. Every derived value is exposed as a state
    attribute, so this single entity is enough for both the alert blueprint
    and the ha-reef-card maintenance view:

      reef_role     : "maint_<task>"   (added by ReefRoleMixin)
      task_key      : catalogue key
      interval_days : configured interval, in days
      days_left     : remaining days, negative when overdue, None when never reset
      overdue       : boolean
      last_reset    : ISO-8601 timestamp, or None
      notify        : mirror of the companion notification switch
    """

    def __init__(
        self,
        coordinator: AquaMedicCoordinator,
        did: str,
        task: MaintenanceTask,
    ) -> None:
        super().__init__(
            coordinator,
            did,
            task,
            f"maint_{task.key}",
            task.translation_key,
        )
        self._attr_icon = task.icon

    @property
    def available(self) -> bool:  # type: ignore[override]
        # Local bookkeeping: usable even when the pump is offline.
        return True

    def _compute_attrs(self) -> dict[str, object]:
        store = self._store
        last = store.get_last_reset(self._did, self._task.key)
        interval = store.get_interval(
            self._did, self._task.key, self._task.default_days
        )
        days_left = compute_days_left(last, interval)
        return {
            "last_reset": last.isoformat() if last is not None else None,
            "interval_days": interval,
            "days_left": days_left,
            "overdue": (days_left is not None and days_left < 0),
            "task_key": self._task.key,
            "notify": store.get_notify(self._did, self._task.key),
        }

    @property
    def extra_state_attributes(self) -> dict[str, object] | None:  # pyright: ignore[reportIncompatibleVariableOverride]
        # ReefRoleMixin adds reef_role on top of whatever we publish here.
        self._attr_extra_state_attributes = self._compute_attrs()
        return super().extra_state_attributes  # type: ignore[misc]

    async def async_press(self) -> None:
        """Record a reset event for this maintenance instance."""
        await self._store.async_reset(self._did, self._task.key)
        # The store notifies our listener, which writes the new state.
