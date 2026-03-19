"""Async Gizwits API client for Aqua Medic devices."""

from __future__ import annotations

import json
import logging
import uuid

import aiohttp

from .const import (
    GIZWITS_API_URLS,
    GIZWITS_APP_ID,
    GIZWITS_USER_AGENT,
)


def _sim_urls(host: str) -> dict[str, str]:
    """Build Gizwits API URL map for the local simulator at *host*.

    Args:
        host: Base URL of the simulator, e.g. ``http://192.168.100.10:8080``.
    """
    h = host.rstrip("/")
    return {
        "LOGIN": f"{h}/app/login",
        "PROVISION": f"{h}/app/provision",
        "BINDINGS": f"{h}/app/bindings",
        "DEVDATA": f"{h}/app/devdata/{{device_id}}/latest",
        "CONTROL": f"{h}/app/control/{{device_id}}",
        "DATAPOINT": f"{h}/app/datapoint",
    }


_LOGGER = logging.getLogger(__name__)


class AquaMedicAuthError(Exception):
    """Raised when authentication fails."""


class AquaMedicConnectionError(Exception):
    """Raised when the API cannot be reached."""


class AquaMedicClient:
    """Thin async wrapper around the Gizwits REST API."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        username: str,
        password: str,
        region: str = "eu",
        sim_host: str | None = None,
    ) -> None:
        self._session = session
        self._username = username
        self._password = password
        if region == "sim" and sim_host:
            self._urls = _sim_urls(sim_host)
        else:
            self._urls = GIZWITS_API_URLS[region]
        self._token: str | None = None

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _headers(self, authenticated: bool = False) -> dict[str, str]:
        """Return base headers, optionally including the user token."""
        h: dict[str, str] = {
            "X-Gizwits-Application-Id": GIZWITS_APP_ID,
            "Content-Type": "application/json",
            "User-Agent": GIZWITS_USER_AGENT,
        }
        if authenticated and self._token:
            h["X-Gizwits-User-token"] = self._token
        return h

    async def _post(
        self,
        url: str,
        payload: dict,
        authenticated: bool = False,
    ) -> dict:
        """POST helper — returns parsed JSON or raises."""
        try:
            async with self._session.post(
                url,
                json=payload,
                headers=self._headers(authenticated),
            ) as resp:
                text = await resp.text()
                try:
                    data = json.loads(text)
                except json.JSONDecodeError:
                    raise AquaMedicConnectionError(
                        f"Invalid JSON from {url}: {text[:200]}"
                    )
                if resp.status >= 400:
                    raise AquaMedicAuthError(f"HTTP {resp.status} from {url}: {data}")
                return data
        except aiohttp.ClientError as exc:
            raise AquaMedicConnectionError(str(exc)) from exc

    async def _get(self, url: str, params: dict | None = None) -> dict:
        """GET helper — returns parsed JSON or raises."""
        try:
            async with self._session.get(
                url,
                params=params,
                headers=self._headers(authenticated=True),
            ) as resp:
                text = await resp.text()
                try:
                    data = json.loads(text)
                except json.JSONDecodeError:
                    raise AquaMedicConnectionError(
                        f"Invalid JSON from {url}: {text[:200]}"
                    )
                if resp.status >= 400:
                    raise AquaMedicConnectionError(
                        f"HTTP {resp.status} from {url}: {data}"
                    )
                return data
        except aiohttp.ClientError as exc:
            raise AquaMedicConnectionError(str(exc)) from exc

    # ── Public API ────────────────────────────────────────────────────────────

    async def provision(self) -> None:
        """Provision a virtual mobile client (required before first login)."""
        phone_id = str(uuid.uuid4()).upper()
        _LOGGER.debug("Provisioning with phone_id %s…", phone_id[:8])
        try:
            await self._post(
                self._urls["PROVISION"],
                {
                    "phone_id": phone_id,
                    "os": "Linux",
                    "os_ver": "5.4",
                    "sdk_version": "2.23.23.01613",
                    "phone_model": "Home Assistant",
                },
            )
            _LOGGER.debug("Provisioning succeeded.")
        except Exception as exc:  # noqa: BLE001
            # Provisioning failure is non-fatal; log and continue.
            _LOGGER.warning("Provisioning failed (non-fatal): %s", exc)

    async def authenticate(self) -> None:
        """Login and store the user token.

        Raises:
            AquaMedicAuthError: if credentials are rejected.
            AquaMedicConnectionError: on network/server errors.
        """
        await self.provision()
        _LOGGER.debug("Authenticating user %s…", self._username)
        data = await self._post(
            self._urls["LOGIN"],
            {"username": self._username, "password": self._password},
        )
        token = data.get("token")
        if not token:
            raise AquaMedicAuthError(f"No token in login response: {data}")
        self._token = token
        _LOGGER.debug("Authentication successful.")

    async def get_devices(self) -> list[dict]:
        """Return all devices bound to the account.

        Returns:
            List of device dicts as returned by Gizwits /bindings.
        """
        data = await self._get(self._urls["BINDINGS"], params={"limit": 20})
        return data.get("devices", [])

    async def get_device_data(self, device_id: str) -> dict:
        """Return the latest reported attribute values for *device_id*."""
        url = self._urls["DEVDATA"].format(device_id=device_id)
        return await self._get(url)

    async def get_datapoints(self, product_key: str) -> dict:
        """Return the datapoint schema (attribute catalogue) for a product."""
        return await self._get(
            self._urls["DATAPOINT"], params={"product_key": product_key}
        )

    async def control_device(self, device_id: str, attrs: dict) -> None:
        """Send a control command to *device_id*.

        Args:
            device_id: Gizwits device identifier.
            attrs: dict of attribute names → values to set,
                   e.g. ``{"SwitchON": 1, "Motor_Speed": 75}``.
        """
        url = self._urls["CONTROL"].format(device_id=device_id)
        await self._post(url, {"attrs": attrs}, authenticated=True)
        _LOGGER.debug("Control sent to %s: %s", device_id, attrs)
