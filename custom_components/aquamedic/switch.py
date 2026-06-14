"""Switch platform for Aqua Medic SmartDrift pumps."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum, auto
from functools import cached_property
from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DC_RUNNER_PRODUCT_KEY,
    DC_SKIMMER_PRODUCT_KEY,
    DOMAIN,
    SMARTDRIFT_PRODUCT_KEY,
)
from .coordinator import AquaMedicCoordinator
from .entity import AquaMedicEntity

_LOGGER = logging.getLogger(__name__)


class _SwitchKind(Enum):
    GIZWITS = auto()
    LOCAL = auto()


@dataclass(frozen=True, kw_only=True)
class AquaMedicSwitchDescription(SwitchEntityDescription):
    attr: str = ""
    icon_off: str = ""
    kind: _SwitchKind = _SwitchKind.GIZWITS


SWITCH_DESCRIPTIONS: tuple[AquaMedicSwitchDescription, ...] = (
    AquaMedicSwitchDescription(
        key="power",
        translation_key="power",
        attr="SwitchON",
        icon="mdi:power",
        icon_off="mdi:power-off",
    ),
    AquaMedicSwitchDescription(
        key="pulse_tide",
        translation_key="pulse_tide",
        attr="PulseTide",
        icon="mdi:wave",
        icon_off="mdi:sine-wave",
        entity_category=EntityCategory.CONFIG,
    ),
    AquaMedicSwitchDescription(
        key="feed_switch",
        translation_key="feed_switch",
        attr="FeedSwitch",
        icon="mdi:fish-off",
        icon_off="mdi:fish",
        entity_category=EntityCategory.CONFIG,
    ),
    AquaMedicSwitchDescription(
        key="timer_on",
        translation_key="timer_on",
        attr="TimerON",
        icon="mdi:timer",
        icon_off="mdi:timer-off",
        entity_category=EntityCategory.CONFIG,
    ),
    AquaMedicSwitchDescription(
        key="control_0_10v",
        translation_key="control_0_10v",
        attr="",
        kind=_SwitchKind.LOCAL,
        icon="mdi:tune-variant",
        icon_off="mdi:tune-variant",
        entity_category=EntityCategory.CONFIG,
    ),
)

# DC Runner return pump: power, feeding mode and 0-10V control
DC_RUNNER_SWITCH_DESCRIPTIONS: tuple[AquaMedicSwitchDescription, ...] = (
    AquaMedicSwitchDescription(
        key="power",
        translation_key="power",
        attr="SwitchON",
        icon="mdi:power",
        icon_off="mdi:power-off",
    ),
    AquaMedicSwitchDescription(
        key="feed_switch",
        translation_key="feed_switch",
        attr="FeedSwitch",
        icon="mdi:fish-off",
        icon_off="mdi:fish",
        entity_category=EntityCategory.CONFIG,
    ),
    AquaMedicSwitchDescription(
        key="control_0_10v",
        translation_key="control_0_10v",
        attr="",
        kind=_SwitchKind.LOCAL,
        icon="mdi:tune-variant",
        icon_off="mdi:tune-variant",
        entity_category=EntityCategory.CONFIG,
    ),
)

# DC Skimmer exposes power, feeding mode, timer/pause and 0-10V control
DC_SKIMMER_SWITCH_DESCRIPTIONS: tuple[AquaMedicSwitchDescription, ...] = (
    AquaMedicSwitchDescription(
        key="power",
        translation_key="power",
        attr="SwitchON",
        icon="mdi:power",
        icon_off="mdi:power-off",
    ),
    AquaMedicSwitchDescription(
        key="feed_switch",
        translation_key="feed_switch",
        attr="FeedSwitch",
        icon="mdi:fish-off",
        icon_off="mdi:fish",
        entity_category=EntityCategory.CONFIG,
    ),
    AquaMedicSwitchDescription(
        key="timer_on",
        translation_key="timer_on",
        attr="TimerON",
        icon="mdi:timer",
        icon_off="mdi:timer-off",
        entity_category=EntityCategory.CONFIG,
    ),
    AquaMedicSwitchDescription(
        key="control_0_10v",
        translation_key="control_0_10v",
        attr="",
        kind=_SwitchKind.LOCAL,
        icon="mdi:tune-variant",
        icon_off="mdi:tune-variant",
        entity_category=EntityCategory.CONFIG,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: AquaMedicCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[SwitchEntity] = []
    for did, dev in (coordinator.data or {}).items():
        if dev.product_key == SMARTDRIFT_PRODUCT_KEY:
            descs = SWITCH_DESCRIPTIONS
        elif dev.product_key == DC_RUNNER_PRODUCT_KEY:
            descs = DC_RUNNER_SWITCH_DESCRIPTIONS
        elif dev.product_key == DC_SKIMMER_PRODUCT_KEY:
            descs = DC_SKIMMER_SWITCH_DESCRIPTIONS
        else:
            continue
        for desc in descs:
            if desc.kind is _SwitchKind.LOCAL:
                entities.append(AquaMedicLocalSwitchEntity(coordinator, did, desc))
            else:
                entities.append(AquaMedicSwitchEntity(coordinator, did, desc))
    async_add_entities(entities)


# ── Gizwits switch ────────────────────────────────────────────────────────────


class AquaMedicSwitchEntity(AquaMedicEntity, SwitchEntity):  # type: ignore[misc]
    """Boolean switch backed by a Gizwits bool attribute."""

    def __init__(
        self,
        coordinator: AquaMedicCoordinator,
        did: str,
        description: AquaMedicSwitchDescription,
    ) -> None:
        super().__init__(coordinator, did, description.key)
        self.entity_description = description
        self._desc = description

    @property
    def available(self) -> bool:  # type: ignore[override]
        dev = self._device
        # is_online is bool | None: None means "unknown" → treat as available (optimistic).
        return bool(
            self.coordinator.last_update_success
            and dev is not None
            and dev.is_online is not False
        )

    @property
    def is_on(self) -> bool | None:  # type: ignore[reportIncompatibleVariableOverride]
        val = self._gizwits_value(self._desc.attr)
        return bool(val) if val is not None else None

    @property
    def icon(self) -> str | None:  # type: ignore[reportIncompatibleVariableOverride]
        if self.is_on:
            return self._desc.icon or None
        return self._desc.icon_off or self._desc.icon or None

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator._client.control_device(self._did, {self._desc.attr: 1})
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator._client.control_device(self._did, {self._desc.attr: 0})
        await self.coordinator.async_request_refresh()


# ── Local 0-10V switch ────────────────────────────────────────────────────────


class AquaMedicLocalSwitchEntity(  # type: ignore[misc, reportIncompatibleVariableOverride]
    CoordinatorEntity[AquaMedicCoordinator], RestoreEntity, SwitchEntity
):
    """Local switch stored in coordinator — not sent to Gizwits.

    Inherits directly from CoordinatorEntity + RestoreEntity + SwitchEntity
    to avoid the MRO conflicts that occur via AquaMedicEntity.

    ON  → 0-10V external control → Flow rate number entity disabled.
    OFF → normal API control     → Flow rate number entity enabled.
    """

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: AquaMedicCoordinator,
        did: str,
        description: AquaMedicSwitchDescription,
    ) -> None:
        CoordinatorEntity.__init__(self, coordinator)  # type: ignore[arg-type]
        self._did = did
        self._desc = description
        self._attr_unique_id = f"{did}_{description.key}"
        self.entity_description = description

    @property
    def available(self) -> bool:  # type: ignore[override]
        return True

    @property
    def is_on(self) -> bool | None:  # type: ignore[reportIncompatibleVariableOverride]
        return self.coordinator.get_control_0_10v(self._did)

    @property
    def icon(self) -> str | None:  # type: ignore[reportIncompatibleVariableOverride]
        return self._desc.icon or "mdi:tune-variant"

    @cached_property
    def device_info(self) -> DeviceInfo:  # type: ignore[reportIncompatibleVariableOverride]
        from .const import DC_RUNNER_PRODUCT_KEY, DC_SKIMMER_PRODUCT_KEY

        dev = self.coordinator.data.get(self._did) if self.coordinator.data else None
        name = dev.name if dev else self._did
        if dev and dev.product_key == DC_RUNNER_PRODUCT_KEY:
            model = "DC Runner"
        elif dev and dev.product_key == DC_SKIMMER_PRODUCT_KEY:
            model = "DC Skimmer"
        else:
            model = "SmartDrift"
        return DeviceInfo(
            identifiers={(DOMAIN, self._did)},
            name=name,
            manufacturer="Aqua Medic",
            model=model,
        )

    async def async_added_to_hass(self) -> None:
        """Restore last state on HA restart."""
        await super().async_added_to_hass()
        last = await self.async_get_last_state()
        if last and last.state not in ("unknown", "unavailable"):
            self.coordinator.set_control_0_10v(self._did, last.state == "on")

    async def async_turn_on(self, **kwargs: Any) -> None:
        self.coordinator.set_control_0_10v(self._did, True)
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        self.coordinator.set_control_0_10v(self._did, False)
        self.async_write_ha_state()
