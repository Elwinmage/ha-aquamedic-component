"""Select platform for Aqua Medic SmartDrift pumps."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, SMARTDRIFT_PRODUCT_KEY
from .coordinator import AquaMedicCoordinator
from .entity import AquaMedicEntity

_LOGGER = logging.getLogger(__name__)

MODE_OPTIONS = ["classic_wave", "sine_wave", "random_wave", "constant_flow"]
LINKAGE_OPTIONS = ["independent", "master", "slave"]

MODE_RAW_MAP: dict[str, str] = {
    "经典造浪": "classic_wave",
    "正弦造浪": "sine_wave",
    "随机造浪": "random_wave",
    "恒流造浪": "constant_flow",
}
LINKAGE_RAW_MAP: dict[str, str] = {
    "独立": "independent",
    "主机": "master",
    "从机": "slave",
}


@dataclass(frozen=True, kw_only=True)
class AquaMedicSelectDescription(SelectEntityDescription):
    attr: str = ""
    options_list: list[str] = field(default_factory=list)
    raw_map: dict[str, str] = field(default_factory=dict)


SELECT_DESCRIPTIONS: tuple[AquaMedicSelectDescription, ...] = (
    AquaMedicSelectDescription(
        key="mode",
        translation_key="mode",
        attr="Mode",
        options=MODE_OPTIONS,
        options_list=MODE_OPTIONS,
        raw_map=MODE_RAW_MAP,
        icon="mdi:waves",
        entity_category=EntityCategory.CONFIG,
    ),
    AquaMedicSelectDescription(
        key="linkage",
        translation_key="linkage",
        attr="Linkage",
        options=LINKAGE_OPTIONS,
        options_list=LINKAGE_OPTIONS,
        raw_map=LINKAGE_RAW_MAP,
        icon="mdi:link-variant",
        entity_category=EntityCategory.CONFIG,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: AquaMedicCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[SelectEntity] = []
    for did, dev in (coordinator.data or {}).items():
        if dev.product_key != SMARTDRIFT_PRODUCT_KEY:
            continue
        for desc in SELECT_DESCRIPTIONS:
            entities.append(AquaMedicSelectEntity(coordinator, did, desc))
    async_add_entities(entities)


class AquaMedicSelectEntity(AquaMedicEntity, SelectEntity):  # type: ignore[misc]
    """Select entity backed by a Gizwits enum attribute."""

    def __init__(
        self,
        coordinator: AquaMedicCoordinator,
        did: str,
        description: AquaMedicSelectDescription,
    ) -> None:
        super().__init__(coordinator, did, description.key)
        self.entity_description = description
        self._desc = description

    @property
    def available(self) -> bool:  # type: ignore[override]
        dev = self._device
        return (
            self.coordinator.last_update_success and dev is not None and dev.is_online
        )

    @property
    def current_option(self) -> str | None:  # type: ignore[reportIncompatibleVariableOverride]
        val = self._gizwits_value(self._desc.attr)
        if val is None:
            return None
        if isinstance(val, str) and val in self._desc.raw_map:
            return self._desc.raw_map[val]
        try:
            return self._desc.options_list[int(val)]
        except (IndexError, ValueError, TypeError):
            _LOGGER.warning(
                "Unknown %s value: %s (device %s)", self._desc.attr, val, self._did
            )
            return None

    async def async_select_option(self, option: str) -> None:
        try:
            idx = self._desc.options_list.index(option)
        except ValueError:
            _LOGGER.error("Invalid option '%s' for %s", option, self._desc.key)
            return
        await self.coordinator._client.control_device(self._did, {self._desc.attr: idx})
        await self.coordinator.async_request_refresh()
