"""Select platform for Aqua Medic SmartDrift pumps."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DC_SKIMMER_PRODUCT_KEY, DOMAIN, SMARTDRIFT_PRODUCT_KEY
from .coordinator import AquaMedicCoordinator
from .entity import AquaMedicEntity, ReefRoleMixin
from .maintenance import (
    PUMP_ROLE_OPTIONS,
    PUMP_ROLE_UNKNOWN,
    get_store,
    role_is_user_defined,
)

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
            descs: tuple[AquaMedicSelectDescription, ...] = SELECT_DESCRIPTIONS
        elif dev.product_key == DC_SKIMMER_PRODUCT_KEY:
            descs = DC_SKIMMER_SELECT_DESCRIPTIONS
        else:
            # No `continue`: the legacy DC Runner product key exposes no
            # Gizwits select but still needs its pump role select below.
            descs = ()
        for desc in descs:
            entities.append(AquaMedicSelectEntity(coordinator, did, desc))
        # The DC Runner return pump and the DC Skimmer share one product key,
        # so the role can only come from the user (see maintenance.py).
        if role_is_user_defined(dev.product_key):
            entities.append(AquaMedicPumpRoleSelect(coordinator, did))
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


class AquaMedicPumpRoleSelect(ReefRoleMixin, AquaMedicEntity, SelectEntity):  # type: ignore[misc]
    """Local select declaring what a DC Runner series pump actually is.

    The return pump and the skimmer pump share the same firmware and the same
    Gizwits product key, and expose a byte-identical datapoint set, so the API
    cannot tell them apart. The user declares it once here and the maintenance
    catalogue follows (needle wheel and cup tasks for a skimmer, strainer and
    impeller tasks for a return pump).

    The value is persisted in the MaintenanceStore rather than restored from
    the entity state: the three maintenance platforms read the role at setup
    time, before any entity exists. Changing the role therefore reloads the
    config entry so the task entities are rebuilt.
    """

    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:pump"
    _attr_translation_key = "pump_role"

    def __init__(self, coordinator: AquaMedicCoordinator, did: str) -> None:
        super().__init__(coordinator, did, "pump_role")
        self._attr_options = list(PUMP_ROLE_OPTIONS)
        self._unsub = None

    @property
    def available(self) -> bool:  # type: ignore[override]
        # Purely local setting: usable even when the pump is offline.
        return True

    @property
    def current_option(self) -> str | None:  # type: ignore[reportIncompatibleVariableOverride]
        return get_store(self.coordinator).get_role(self._did)

    async def async_select_option(self, option: str) -> None:
        if option not in PUMP_ROLE_OPTIONS:
            _LOGGER.error("Invalid pump role '%s' for %s", option, self._did)
            return

        store = get_store(self.coordinator)
        if store.get_role(self._did) == option:
            return

        await store.async_set_role(self._did, option)
        self.async_write_ha_state()

        entry_id = getattr(self.coordinator, "entry_id", None)
        if not entry_id:
            _LOGGER.warning(
                "Pump role saved for %s but the config entry id is unknown; "
                "reload the integration to apply the maintenance tasks",
                self._did,
            )
            return

        if option == PUMP_ROLE_UNKNOWN:
            _LOGGER.info(
                "Pump role cleared for %s; removing maintenance tasks", self._did
            )

        # Scheduled, never awaited: awaiting a reload from an entity action
        # deadlocks, since the reload tears down the very platform we run in.
        self.hass.async_create_task(
            self.hass.config_entries.async_reload(entry_id),
            eager_start=False,
        )

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()

        @callback
        def _role_changed() -> None:
            self.async_write_ha_state()

        self._unsub = get_store(self.coordinator).async_add_role_listener(
            self._did, _role_changed
        )

    async def async_will_remove_from_hass(self) -> None:
        if self._unsub is not None:
            self._unsub()
            self._unsub = None
        await super().async_will_remove_from_hass()
