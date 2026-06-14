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
from .entity import AquaMedicEntity

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
        if (
            dev.product_key != SMARTDRIFT_PRODUCT_KEY
            and dev.product_key != DC_SKIMMER_PRODUCT_KEY
        ):
            continue
        entities.append(AquaMedicRefreshButton(coordinator, did, REFRESH_DESCRIPTION))
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
