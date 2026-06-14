"""Select platform for Aqua Medic SmartDrift pumps."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DC_SKIMMER_PRODUCT_KEY, DOMAIN, SMARTDRIFT_PRODUCT_KEY
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

# DC Runner AutoMode (timer mode): 停机=stop, 自动=auto, 喂食=feeding.
# Index order matches the device enum so the value can also be read as an int.
DC_RUNNER_AUTO_MODE_OPTIONS = ["stop", "auto", "feeding"]
DC_RUNNER_AUTO_MODE_RAW_MAP: dict[str, str] = {
    "停机": "stop",
    "自动": "auto",
    "喂食": "feeding",
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


# DC Skimmer exposes a single AutoMode (timer mode) select.
DC_SKIMMER_SELECT_DESCRIPTIONS: tuple[AquaMedicSelectDescription, ...] = (
    AquaMedicSelectDescription(
        key="auto_mode",
        translation_key="auto_mode",
        attr="AutoMode",
        options=DC_RUNNER_AUTO_MODE_OPTIONS,
        options_list=DC_RUNNER_AUTO_MODE_OPTIONS,
        raw_map=DC_RUNNER_AUTO_MODE_RAW_MAP,
        icon="mdi:clock-outline",
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
        if dev.product_key == SMARTDRIFT_PRODUCT_KEY:
            descs = SELECT_DESCRIPTIONS
        elif dev.product_key == DC_SKIMMER_PRODUCT_KEY:
            descs = DC_SKIMMER_SELECT_DESCRIPTIONS
        else:
            continue
        for desc in descs:
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
        # is_online is bool | None: None means "unknown" → treat as available (optimistic).
        return bool(
            self.coordinator.last_update_success
            and dev is not None
            and dev.is_online is not False
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
