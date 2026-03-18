"""DataUpdateCoordinator for Aqua Medic / Gizwits devices."""

from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .client import AquaMedicClient, AquaMedicConnectionError
from .const import DOMAIN, UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)


class AquaMedicDeviceData:
    """Holds parsed state for one device."""

    def __init__(self, device: dict, latest: dict) -> None:
        self.did = device.get("did", "")
        self.product_key = device.get("product_key", "")
        self.name = device.get("dev_alias") or device.get("product_name") or "AquaMedic"
        self.is_online = device.get("is_online", False)
        # Flat dict of attribute name → value
        self.attrs: dict = latest.get("attr", {})
        self.updated_at = latest.get("updated_at")

    def get(self, attr: str, default=None):
        """Convenience getter for a single attribute value."""
        return self.attrs.get(attr, default)


class AquaMedicCoordinator(DataUpdateCoordinator[dict[str, AquaMedicDeviceData]]):
    """Fetch data from all Gizwits devices every UPDATE_INTERVAL.

    ``data`` is a dict keyed by device_id (did) → AquaMedicDeviceData.
    """

    def __init__(self, hass: HomeAssistant, client: AquaMedicClient) -> None:
        self._client = client
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
        )

    async def _async_update_data(self) -> dict[str, AquaMedicDeviceData]:
        """Pull fresh data from the Gizwits API.

        Raises:
            UpdateFailed: on any API error so HA can display the correct status.
        """
        try:
            devices = await self._client.get_devices()
        except AquaMedicConnectionError as exc:
            raise UpdateFailed(f"Failed to fetch device list: {exc}") from exc

        result: dict[str, AquaMedicDeviceData] = {}

        for device in devices:
            did = device.get("did")
            if not did:
                continue
            try:
                latest = await self._client.get_device_data(did)
            except AquaMedicConnectionError as exc:
                _LOGGER.warning("Could not fetch data for device %s: %s", did, exc)
                latest = {}

            result[did] = AquaMedicDeviceData(device, latest)
            _LOGGER.debug(
                "Updated %s (%s): %s",
                result[did].name,
                did,
                result[did].attrs,
            )

        return result
