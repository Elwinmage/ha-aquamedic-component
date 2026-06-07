"""Async Gizwits API client for Aqua Medic devices (AEP + Gateway, legacy fallback)."""

from __future__ import annotations

import json
import logging
import time
import uuid
from typing import Any

import aiohttp

from .const import (
    AEP_PATH_BINDINGS,
    AEP_PATH_CONTROL,
    AEP_PATH_DEVDATA,
    AEP_PATH_LOGIN_PWD,
    AEP_PATH_DATAPOINT,
    AEP_PATH_REFRESH_TOKEN,
    AEP_PATH_USER_DEVICES,
    DEVICE_LIST_BINDINGS,
    DEVICE_LIST_SMART_HOME,
    GATEWAY_PATH_DEVICE_QUERY,
    GIZWITS_API_URLS,
    GIZWITS_APP_KEY,
    GIZWITS_GATEWAY_API_KEY,
    GIZWITS_LEGACY_APP_ID,
    GIZWITS_REGION_ENDPOINTS,
    GIZWITS_USER_AGENT,
)

_LOGGER = logging.getLogger(__name__)

API_MODE_AEP = "aep"
API_MODE_LEGACY = "legacy"

# AEP error codes that should trigger token refresh or legacy fallback.
_AEP_AUTH_CODES = frozenset({505, 526, 1000033})


def _aep_code_int(code: Any) -> int | None:
    """Normalize AEP ``code`` field (API may return int or str)."""
    if code is None:
        return None
    try:
        return int(code)
    except (TypeError, ValueError):
        return None


def _aep_code_is_success(code: Any) -> bool:
    """Return True when AEP envelope code indicates success (200)."""
    code_int = _aep_code_int(code)
    return code is None or code_int == 200


def _sim_urls(host: str) -> dict[str, str]:
    """Build legacy Open API URL map for the local simulator."""
    h = host.rstrip("/")
    return {
        "LOGIN": f"{h}/app/login",
        "PROVISION": f"{h}/app/provision",
        "BINDINGS": f"{h}/app/bindings",
        "DEVDATA": f"{h}/app/devdata/{{device_id}}/latest",
        "CONTROL": f"{h}/app/control/{{device_id}}",
        "DATAPOINT": f"{h}/app/datapoint",
    }


class AquaMedicAuthError(Exception):
    """Raised when authentication fails."""


class AquaMedicConnectionError(Exception):
    """Raised when the API cannot be reached."""


class AquaMedicClient:
    """Async client: AEP (official app API) with legacy Open API fallback."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        username: str,
        password: str,
        region: str = "eu",
        sim_host: str | None = None,
        lang: str = "en",
        access_token: str | None = None,
        refresh_token: str | None = None,
        token_created_at: int | None = None,
        token_expired_at: int | None = None,
        device_list_api: str | None = None,
    ) -> None:
        self._session = session
        self._username = username
        self._password = password
        self._region = region
        self._lang = lang.split("-")[0] if lang else "en"

        if region == "sim" and sim_host:
            host = sim_host.rstrip("/")
            self._aep_base = host
            self._gateway_base = host
            self._open_api_base = host
            self._legacy_urls = _sim_urls(host)
        elif region in GIZWITS_REGION_ENDPOINTS:
            endpoints = GIZWITS_REGION_ENDPOINTS[region]
            self._aep_base = endpoints["aep_base"]
            self._gateway_base = endpoints["gateway_base"]
            self._open_api_base = endpoints["open_api_base"]
            self._legacy_urls = GIZWITS_API_URLS[region]
        else:
            raise ValueError(f"Unknown region: {region}")

        self._api_mode: str = API_MODE_AEP
        self._jwt: str | None = access_token
        self._refresh_token: str | None = refresh_token
        self._uid: str | None = None
        self._token_created_at: int | None = token_created_at
        self._token_expired_at: int | None = token_expired_at
        # Legacy Open API user token
        self._token: str | None = None
        # Per-account device list endpoint (smart_home vs bindings); None = auto-detect.
        self._device_list_api: str | None = device_list_api
        # False after legacy login 9026 (migrated account — no Open API 2.0 login).
        self._legacy_available: bool | None = None

    @property
    def device_list_api(self) -> str | None:
        """Detected AEP device-list variant (``smart_home`` or ``bindings``)."""
        return self._device_list_api

    @property
    def legacy_available(self) -> bool | None:
        """Whether legacy Open API login works for this account."""
        return self._legacy_available

    @property
    def api_mode(self) -> str:
        """Return active API stack: ``aep`` or ``legacy``."""
        return self._api_mode

    @property
    def access_token(self) -> str | None:
        """Current JWT for AEP/Gateway (for config entry persistence)."""
        return self._jwt

    @property
    def refresh_token(self) -> str | None:
        """Refresh token from last AEP login (for config entry persistence)."""
        return self._refresh_token

    @property
    def token_expired_at(self) -> int | None:
        """JWT expiry timestamp (Unix seconds)."""
        return self._token_expired_at

    @property
    def token_created_at(self) -> int | None:
        """JWT creation timestamp (Unix seconds)."""
        return self._token_created_at

    # ── URL builders ──────────────────────────────────────────────────────────

    def _aep_url(self, path: str) -> str:
        return f"{self._aep_base.rstrip('/')}{path}"

    def _gateway_url(self, path: str) -> str:
        return f"{self._gateway_base.rstrip('/')}{path}"

    def _open_api_url(self, path: str) -> str:
        return f"{self._open_api_base.rstrip('/')}{path}"

    def _is_gateway_url(self, url: str) -> bool:
        return url.startswith(self._gateway_base.rstrip("/"))

    # ── Request wrappers ──────────────────────────────────────────────────────

    def _wrap_aep(self, data: dict[str, Any]) -> dict[str, Any]:
        return {"appKey": GIZWITS_APP_KEY, "data": data, "version": "1.0"}

    def _aep_headers(self) -> dict[str, str]:
        h: dict[str, str] = {
            "Content-Type": "application/json",
            "Version": "1.0",
            "X-Gizwits-Application-Id": GIZWITS_APP_KEY,
            "User-Agent": GIZWITS_USER_AGENT,
        }
        if self._jwt:
            h["Authorization"] = self._jwt
        return h

    def _gateway_headers(self) -> dict[str, str]:
        h = self._aep_headers()
        h["X-Gizwits-Api-Key"] = GIZWITS_GATEWAY_API_KEY
        return h

    def _open_api_headers(self) -> dict[str, str]:
        """Headers for Open API host paths (datapoint schema, etc.)."""
        return {
            "Content-Type": "application/json",
            "X-Gizwits-Application-Id": GIZWITS_APP_KEY,
            "User-Agent": GIZWITS_USER_AGENT,
        }

    def _control_headers_aep(self) -> dict[str, str]:
        """Headers for POST /app/control on the Legacy Open API host.

        Discovery finding: migrated (smart_home) accounts accept AEP JWT tokens
        when placed in X-Gizwits-User-token — NOT in Authorization.
        The Gateway /v2/devices-controller returns 405 for all methods.
        The AEP host /app/control returns 404.
        """
        return {
            "Content-Type": "application/json",
            "X-Gizwits-Application-Id": GIZWITS_APP_KEY,
            "User-Agent": GIZWITS_USER_AGENT,
            "X-Gizwits-User-token": self._jwt or "",
        }

    def _legacy_headers(self, authenticated: bool = False) -> dict[str, str]:
        h: dict[str, str] = {
            "X-Gizwits-Application-Id": GIZWITS_LEGACY_APP_ID,
            "Content-Type": "application/json",
            "User-Agent": GIZWITS_USER_AGENT,
        }
        if authenticated and self._token:
            h["X-Gizwits-User-token"] = self._token
        return h

    async def _request_json(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str],
        json_body: dict | None = None,
        params: dict | None = None,
        auth_error: type[Exception] = AquaMedicConnectionError,
        ssl: bool | None = None,
    ) -> dict:
        request_kwargs: dict[str, Any] = {
            "json": json_body,
            "params": params,
            "headers": headers,
        }
        if ssl is not None:
            request_kwargs["ssl"] = ssl
        elif self._is_gateway_url(url):
            request_kwargs["ssl"] = False

        try:
            async with self._session.request(method, url, **request_kwargs) as resp:
                text = await resp.text()
                try:
                    data = json.loads(text) if text else {}
                except json.JSONDecodeError as exc:
                    raise AquaMedicConnectionError(
                        f"Invalid JSON from {url}: {text[:200]}"
                    ) from exc
                if resp.status >= 400:
                    raise auth_error(f"HTTP {resp.status} from {url}: {data}")
                return data
        except aiohttp.ClientError as exc:
            raise AquaMedicConnectionError(str(exc)) from exc

    def _parse_aep_envelope(self, body: dict) -> dict[str, Any]:
        """Extract inner ``data`` from AEP response; raise on error codes."""
        code = body.get("code")
        code_int = _aep_code_int(code)
        if code is not None and not _aep_code_is_success(code):
            if code_int in _AEP_AUTH_CODES:
                raise AquaMedicAuthError(
                    f"AEP error {code}: {body.get('message', body)}"
                )
            raise AquaMedicConnectionError(
                f"AEP error {code}: {body.get('message', body)}"
            )
        inner = body.get("data")
        if isinstance(inner, dict):
            return inner
        if inner is not None:
            return {"data": inner}
        return body

    # ── Token lifecycle ─────────────────────────────────────────────────────────

    async def ensure_valid_token(self) -> None:
        """Refresh JWT when past half lifetime (AEP mode only)."""
        if self._api_mode != API_MODE_AEP or not self._jwt:
            return
        if not self._token_expired_at or not self._token_created_at:
            return
        now = int(time.time())
        lifetime = self._token_expired_at - self._token_created_at
        if lifetime <= 0:
            return
        if now < self._token_created_at + lifetime // 2:
            return
        if not self._refresh_token:
            return
        try:
            await self._refresh_aep_token()
        except (AquaMedicAuthError, AquaMedicConnectionError) as exc:
            _LOGGER.warning("Token refresh failed, re-login: %s", exc)
            await self._authenticate_aep()

    def _store_aep_tokens(self, data: dict[str, Any]) -> None:
        jwt_block = data.get("jwtAuthenticationDto") or {}
        token = jwt_block.get("token") or data.get("token")
        if not token:
            raise AquaMedicAuthError(f"No JWT in AEP login response: {data}")
        self._jwt = token
        self._uid = data.get("uid")
        self._refresh_token = data.get("refreshToken") or data.get("refresh_token")
        self._token_created_at = data.get("createdAt") or data.get("created_at")
        self._token_expired_at = data.get("expiredAt") or data.get("expired_at")
        if not self._token_created_at:
            self._token_created_at = int(time.time())
        if not self._token_expired_at:
            self._token_expired_at = self._token_created_at + 86400

    async def _refresh_aep_token(self) -> None:
        if not self._refresh_token:
            raise AquaMedicAuthError("No refresh token available")
        if not self._jwt:
            raise AquaMedicAuthError("No JWT for refresh request")
        body = await self._request_json(
            "POST",
            self._aep_url(AEP_PATH_REFRESH_TOKEN),
            headers=self._aep_headers(),
            json_body=self._wrap_aep(
                {
                    "clientId": GIZWITS_APP_KEY,
                    "refresh": True,
                    "refresh_token": self._refresh_token,
                }
            ),
            auth_error=AquaMedicAuthError,
        )
        data = self._parse_aep_envelope(body)
        token = data.get("token")
        if not token:
            raise AquaMedicAuthError(f"No token in refresh response: {data}")
        self._jwt = token
        self._refresh_token = data.get("refresh_token") or data.get("refreshToken")
        self._token_created_at = data.get("created_at") or data.get("createdAt")
        self._token_expired_at = data.get("expired_at") or data.get("expiredAt")
        _LOGGER.debug("AEP token refreshed.")

    async def _authenticate_aep(self) -> None:
        _LOGGER.debug("AEP login for %s on %s…", self._username, self._aep_base)
        body = await self._request_json(
            "POST",
            self._aep_url(AEP_PATH_LOGIN_PWD),
            headers={
                "Content-Type": "application/json",
                "X-Gizwits-Application-Id": GIZWITS_APP_KEY,
                "User-Agent": GIZWITS_USER_AGENT,
            },
            json_body=self._wrap_aep(
                {
                    "account": self._username,
                    "password": self._password,
                    "lang": self._lang,
                    "refreshToken": True,
                }
            ),
            auth_error=AquaMedicAuthError,
        )
        data = self._parse_aep_envelope(body)
        self._store_aep_tokens(data)
        _LOGGER.info("AEP authentication successful (region=%s).", self._region)

    async def _switch_to_legacy(self) -> None:
        if not self._can_use_legacy():
            raise AquaMedicAuthError(
                "Legacy Open API unavailable for this account (migrated to AEP)."
            )
        _LOGGER.info("Falling back to legacy Open API (region=%s).", self._region)
        await self._authenticate_legacy()
        self._api_mode = API_MODE_LEGACY

    # ── Legacy Open API ─────────────────────────────────────────────────────────

    async def _post_legacy(
        self,
        url: str,
        payload: dict,
        authenticated: bool = False,
    ) -> dict:
        return await self._request_json(
            "POST",
            url,
            headers=self._legacy_headers(authenticated),
            json_body=payload,
            auth_error=AquaMedicAuthError,
        )

    async def _get_legacy(self, url: str, params: dict | None = None) -> dict:
        return await self._request_json(
            "GET",
            url,
            headers=self._legacy_headers(authenticated=True),
            params=params,
            auth_error=AquaMedicConnectionError,
        )

    async def provision(self) -> None:
        """Provision a virtual mobile client (legacy only, non-fatal)."""
        phone_id = str(uuid.uuid4()).upper()
        _LOGGER.debug("Provisioning with phone_id %s…", phone_id[:8])
        try:
            await self._post_legacy(
                self._legacy_urls["PROVISION"],
                {
                    "phone_id": phone_id,
                    "os": "Linux",
                    "os_ver": "5.4",
                    "sdk_version": "2.23.23.01613",
                    "phone_model": "Home Assistant",
                },
            )
        except Exception as exc:  # noqa: BLE001
            _LOGGER.warning("Provisioning failed (non-fatal): %s", exc)

    async def _authenticate_legacy(self) -> None:
        await self.provision()
        try:
            data = await self._post_legacy(
                self._legacy_urls["LOGIN"],
                {"username": self._username, "password": self._password},
            )
        except AquaMedicAuthError as exc:
            if "9026" in str(exc):
                self._legacy_available = False
            raise
        token = data.get("token")
        if not token:
            raise AquaMedicAuthError(f"No token in legacy login response: {data}")
        self._token = token
        self._legacy_available = True
        _LOGGER.debug("Legacy authentication successful.")

    def _can_use_legacy(self) -> bool:
        """Return False when this account cannot use Open API 2.0 (migrated)."""
        return self._legacy_available is not False

    async def _aep_request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        json_body: dict | None = None,
        params: dict | None = None,
        allow_refresh: bool = True,
    ) -> dict:
        """AEP/Gateway request with one refresh+retry on auth errors."""
        hdrs = headers or self._aep_headers()
        auth_error = (
            AquaMedicConnectionError
            if self._is_gateway_url(url)
            else AquaMedicAuthError
        )
        try:
            body = await self._request_json(
                method,
                url,
                headers=hdrs,
                json_body=json_body,
                params=params,
                auth_error=auth_error,
            )
        except AquaMedicAuthError as exc:
            if "HTTP 404" in str(exc):
                raise AquaMedicConnectionError(str(exc)) from exc
            if allow_refresh and self._refresh_token and self._jwt:
                _LOGGER.debug(
                    "AEP HTTP auth error, refreshing token and retrying once."
                )
                await self._refresh_aep_token()
                return await self._aep_request(
                    method,
                    url,
                    headers=headers,
                    json_body=json_body,
                    params=params,
                    allow_refresh=False,
                )
            raise

        code = body.get("code")
        code_int = _aep_code_int(code)
        if code is not None and not _aep_code_is_success(code):
            if code_int in _AEP_AUTH_CODES:
                if allow_refresh and self._refresh_token and self._jwt:
                    _LOGGER.debug(
                        "AEP error %s, refreshing token and retrying once.", code
                    )
                    await self._refresh_aep_token()
                    return await self._aep_request(
                        method,
                        url,
                        headers=headers,
                        json_body=json_body,
                        params=params,
                        allow_refresh=False,
                    )
                raise AquaMedicAuthError(
                    f"AEP error {code}: {body.get('message', body)}"
                )
            raise AquaMedicConnectionError(
                f"AEP error {code}: {body.get('message', body)}"
            )
        return body

    async def _probe_aep_session(self) -> None:
        """Verify stored JWT via the account's device-list endpoint."""
        await self.ensure_valid_token()
        if self._device_list_api == DEVICE_LIST_BINDINGS:
            await self._fetch_bindings_aep()
        elif self._device_list_api == DEVICE_LIST_SMART_HOME:
            await self._fetch_user_devices_aep()
        else:
            await self._detect_device_list_api()

    async def _fetch_user_devices_aep(self) -> list[dict]:
        """smartHome/v2/users/devices (current app API, migrated accounts)."""
        body = await self._aep_request(
            "GET",
            self._aep_url(AEP_PATH_USER_DEVICES),
        )
        if "code" in body:
            inner = self._parse_aep_envelope(body)
            return self._normalize_bindings(inner)
        return self._normalize_bindings(body)

    async def _fetch_bindings_aep(self) -> list[dict]:
        """Legacy AEP /app/bindings (older accounts)."""
        body = await self._aep_request(
            "GET",
            self._aep_url(AEP_PATH_BINDINGS),
            params={"limit": 50, "skip": 0},
        )
        if "code" in body:
            inner = self._parse_aep_envelope(body)
            return self._normalize_bindings(inner)
        return self._normalize_bindings(body)

    async def _detect_device_list_api(self) -> str:
        """Probe endpoints once and remember which API this account uses."""
        await self.ensure_valid_token()

        smart_home_error: Exception | None = None
        try:
            await self._fetch_user_devices_aep()
        except (AquaMedicAuthError, AquaMedicConnectionError) as exc:
            smart_home_error = exc
            _LOGGER.debug("smartHome device list unavailable (%s).", exc)
        else:
            try:
                await self._fetch_bindings_aep()
            except (AquaMedicAuthError, AquaMedicConnectionError) as exc:
                if "HTTP 404" in str(exc):
                    _LOGGER.info(
                        "Device list API: smartHome (migrated account, bindings 404)."
                    )
                else:
                    _LOGGER.debug(
                        "Device list API: smartHome (bindings also failed: %s).", exc
                    )
            else:
                _LOGGER.info(
                    "Device list API: smartHome (both endpoints work; preferring app API)."
                )
            self._device_list_api = DEVICE_LIST_SMART_HOME
            if self._legacy_available is not False:
                self._legacy_available = False
            return DEVICE_LIST_SMART_HOME

        try:
            await self._fetch_bindings_aep()
        except (AquaMedicAuthError, AquaMedicConnectionError) as exc:
            if smart_home_error is not None:
                raise AquaMedicConnectionError(
                    "Neither smartHome nor bindings device list is available."
                ) from exc
            raise

        _LOGGER.info("Device list API: AEP bindings (legacy account).")
        self._device_list_api = DEVICE_LIST_BINDINGS
        return DEVICE_LIST_BINDINGS

    async def _get_devices_aep(self) -> list[dict]:
        await self.ensure_valid_token()
        api = self._device_list_api or await self._detect_device_list_api()
        if api == DEVICE_LIST_SMART_HOME:
            raw = await self._fetch_user_devices_aep()
        else:
            raw = await self._fetch_bindings_aep()
        return self._normalize_device_list(raw)

    def _uses_smart_home_api(self) -> bool:
        """True when this account uses the smartHome device-list API (migrated)."""
        return (
            self._device_list_api == DEVICE_LIST_SMART_HOME
            or self._legacy_available is False
        )

    async def _query_device_gateway(self, device_id: str) -> dict:
        """Gateway status (official app: queryDeviceStatus / thirdDeviceGetStatus)."""
        gw_url = self._gateway_url(
            GATEWAY_PATH_DEVICE_QUERY.format(device_id=device_id)
        )
        gw_body = await self._aep_request(
            "GET",
            gw_url,
            headers=self._gateway_headers(),
        )
        return self._normalize_gateway_query(gw_body)

    async def _fetch_devdata_aep(self, device_id: str) -> dict:
        """Latest attrs on AEP host (official app: deviceLatestData)."""
        url = self._aep_url(AEP_PATH_DEVDATA.format(device_id=device_id))
        body = await self._aep_request(
            "GET",
            url,
            params={"show_expected_status": 1},
        )
        if "code" in body:
            inner = self._parse_aep_envelope(body)
            return self._normalize_devdata(inner)
        return self._normalize_devdata(body)

    async def _fetch_devdata_open_api(self, device_id: str) -> dict:
        """Latest attrs on Open API host (fallback when AEP devdata fails)."""
        url = self._open_api_url(AEP_PATH_DEVDATA.format(device_id=device_id))
        headers = self._open_api_headers()
        if self._jwt:
            headers = {
                **headers,
                "Authorization": self._jwt,
                "X-Gizwits-User-token": self._jwt,
            }
        body = await self._request_json(
            "GET",
            url,
            headers=headers,
            params={"show_expected_status": 1},
        )
        if "code" in body and not _aep_code_is_success(body.get("code")):
            raise AquaMedicConnectionError(
                f"Open API devdata error {body.get('code')}: {body.get('message', body)}"
            )
        if "code" in body:
            inner = body.get("data")
            if isinstance(inner, dict):
                return self._normalize_devdata(inner)
        return self._normalize_devdata(body)

    async def _fetch_device_data_with_fallbacks(
        self,
        device_id: str,
        *,
        fetchers: tuple,
        label: str,
    ) -> dict:
        """Try fetchers in order; return first result with attrs or online hint."""
        errors: list[str] = []
        for fetch in fetchers:
            try:
                result = await fetch(device_id)
            except AquaMedicConnectionError as exc:
                errors.append(str(exc))
                _LOGGER.debug("%s failed for %s: %s", fetch.__name__, device_id, exc)
                continue
            if result.get("attr") or result.get("is_online") is not None:
                return result
        detail = "; ".join(errors) if errors else "no data returned"
        raise AquaMedicConnectionError(
            f"Could not read device status for {device_id} ({label}): {detail}"
        )

    async def _get_device_data_aep(self, device_id: str) -> dict:
        await self.ensure_valid_token()

        if self._uses_smart_home_api():
            # SmartDrift uses WIFI (not THIRD_CLOUD). State via deviceLatestData
            # (AEP devdata); gateway queryDeviceStatus is for THIRD_CLOUD only.
            return await self._fetch_device_data_with_fallbacks(
                device_id,
                fetchers=(
                    self._fetch_devdata_aep,
                    self._fetch_devdata_open_api,
                    self._query_device_gateway,
                ),
                label="smart_home",
            )

        try:
            result = await self._fetch_devdata_aep(device_id)
        except AquaMedicConnectionError as exc:
            if "HTTP 404" not in str(exc):
                raise
            _LOGGER.debug(
                "AEP devdata unavailable for %s (404), using gateway.", device_id
            )
            return await self._query_device_gateway(device_id)

        if result.get("attr"):
            return result
        return await self._query_device_gateway(device_id)

    async def _control_device_aep(self, device_id: str, attrs: dict) -> None:
        await self.ensure_valid_token()

        # Body format is the same on every control path.
        control_body = {"attrs": attrs}

        if self._uses_smart_home_api():
            # Confirmed via endpoint discovery: migrated accounts accept
            # POST /app/control/{id} on the Legacy Open API host
            # (euapi.gizwits.com) with the AEP JWT placed in
            # X-Gizwits-User-token.  The Gateway /v2/devices-controller
            # returns 405 for all methods; the AEP /app/control returns 404.
            oa_url = self._open_api_url(f"/app/control/{device_id}")
            await self._request_json(
                "POST",
                oa_url,
                headers=self._control_headers_aep(),
                json_body=control_body,
                auth_error=AquaMedicConnectionError,
            )
            _LOGGER.debug("Control sent to %s: %s", device_id, attrs)
            return

        # Bindings (non-migrated AEP) accounts: /app/control on the AEP host.
        await self._aep_request(
            "POST",
            self._aep_url(AEP_PATH_CONTROL.format(device_id=device_id)),
            json_body=control_body,
        )
        _LOGGER.debug("AEP control sent to %s: %s", device_id, attrs)

    # ── Public API ────────────────────────────────────────────────────────────

    async def authenticate(self) -> None:
        """Restore AEP session, login, or fall back to legacy Open API."""
        if (
            self._jwt
            and self._refresh_token
            and self._token_expired_at
            and self._token_expired_at > int(time.time())
        ):
            try:
                self._api_mode = API_MODE_AEP
                await self._probe_aep_session()
                _LOGGER.info(
                    "AEP session restored from config (region=%s).", self._region
                )
                return
            except (AquaMedicAuthError, AquaMedicConnectionError) as exc:
                _LOGGER.debug("Stored AEP session invalid (%s), re-login.", exc)

        try:
            await self._authenticate_aep()
            self._api_mode = API_MODE_AEP
        except (AquaMedicAuthError, AquaMedicConnectionError) as exc:
            _LOGGER.warning("AEP login failed (%s), trying legacy API.", exc)
            await self._switch_to_legacy()

    @staticmethod
    def _normalize_device_record(device: dict) -> dict:
        """Map smartHome / bindings records to coordinator field names."""
        pk = device.get("product_key") or device.get("productKey") or ""
        name = (
            device.get("dev_alias")
            or device.get("product_name")
            or device.get("name")
            or ""
        )
        online = device.get("is_online")
        if online is None:
            online = device.get("isOnline")
        if online is None:
            online = device.get("online")
        if online is None and device.get("wifiOnline") is not None:
            online = bool(device.get("wifiOnline"))
        if online is None and device.get("netStatus") is not None:
            online = device.get("netStatus") == 2
        normalized = dict(device)
        normalized["did"] = device.get("did", "")
        normalized["product_key"] = pk
        if name:
            normalized["dev_alias"] = name
            if not normalized.get("product_name"):
                normalized["product_name"] = name
        if online is not None:
            normalized["is_online"] = bool(online)
        return normalized

    @classmethod
    def _normalize_device_list(cls, devices: list[dict]) -> list[dict]:
        return [cls._normalize_device_record(d) for d in devices]

    @staticmethod
    def _normalize_bindings(raw: dict) -> list[dict]:
        if "devices" in raw:
            devices = raw["devices"]
            return devices if isinstance(devices, list) else []
        inner = raw.get("data")
        if isinstance(inner, dict) and "devices" in inner:
            devices = inner["devices"]
            return devices if isinstance(devices, list) else []
        if isinstance(inner, list):
            return inner
        if isinstance(raw, list):
            return raw
        return []

    @staticmethod
    def resolve_is_online(device: dict, latest: dict | None = None) -> bool | None:
        """Return online state when known; ``None`` means unknown (not offline)."""
        latest = latest or {}
        if latest.get("is_online") is not None:
            return bool(latest["is_online"])
        if device.get("is_online") is not None:
            return bool(device["is_online"])
        attrs = latest.get("attr")
        if isinstance(attrs, dict) and attrs:
            return True
        return None

    @staticmethod
    def _normalize_devdata(raw: dict) -> dict:
        def _with_online(result: dict, source: dict) -> dict:
            online = source.get("is_online")
            if online is None:
                online = source.get("isOnline")
            if online is not None:
                result["is_online"] = bool(online)
            elif isinstance(result.get("attr"), dict) and result["attr"]:
                result["is_online"] = True
            return result

        if "attr" in raw:
            return _with_online(dict(raw), raw)
        inner = raw.get("data")
        if isinstance(inner, dict):
            if "attr" in inner:
                return _with_online(dict(inner), inner)
            attrs = inner.get("attrs") or inner.get("attributes")
            if attrs is not None:
                return _with_online(
                    {
                        "attr": attrs,
                        "updated_at": inner.get("updated_at") or inner.get("updatedAt"),
                    },
                    inner,
                )
        attrs = raw.get("attrs")
        if attrs is not None:
            return _with_online(
                {"attr": attrs, "updated_at": raw.get("updated_at")},
                raw,
            )
        return _with_online(dict(raw), raw) if raw else raw

    @staticmethod
    def _normalize_gateway_query(raw: dict) -> dict:
        """Map Gateway query response to coordinator ``{attr, is_online, …}`` shape."""
        # Use explicit intermediates so Pyright can narrow the type after isinstance.
        _outer = raw.get("data")
        inner: dict = _outer if isinstance(_outer, dict) else raw
        _inner = inner.get("data")
        payload: dict = _inner if isinstance(_inner, dict) else inner
        attrs = payload.get("attrs") or payload.get("attr")
        is_online = payload.get("is_online")
        if is_online is None:
            is_online = payload.get("isOnline")

        if isinstance(attrs, dict):
            result: dict[str, Any] = {
                "attr": attrs,
                "updated_at": payload.get("updated_at") or payload.get("updatedAt"),
            }
        else:
            result = AquaMedicClient._normalize_devdata(raw)

        if is_online is not None:
            result["is_online"] = bool(is_online)
        return result

    async def get_devices(self) -> list[dict]:
        """Return all devices bound to the account."""
        if self._api_mode == API_MODE_AEP:
            try:
                return await self._get_devices_aep()
            except AquaMedicAuthError as exc:
                if self._should_fallback_to_legacy(exc) and self._can_use_legacy():
                    await self._switch_to_legacy()
                    return await self.get_devices()
                raise
        data = await self._get_legacy(
            self._legacy_urls["BINDINGS"], params={"limit": 50}
        )
        return self._normalize_device_list(self._normalize_bindings(data))

    @staticmethod
    def _should_fallback_to_legacy(exc: AquaMedicAuthError) -> bool:
        """Only fall back when auth failed — not for missing endpoints (404)."""
        msg = str(exc)
        if "HTTP 404" in msg:
            return False
        return any(
            token in msg for token in ("505", "526", "1000033", "9004", "9020", "9026")
        )

    async def get_device_data(self, device_id: str) -> dict:
        """Return the latest reported attribute values for *device_id*."""
        if self._api_mode == API_MODE_AEP:
            try:
                return await self._get_device_data_aep(device_id)
            except AquaMedicAuthError as exc:
                if self._should_fallback_to_legacy(exc) and self._can_use_legacy():
                    await self._switch_to_legacy()
                    return await self.get_device_data(device_id)
                raise
        data = await self._get_legacy(
            self._legacy_urls["DEVDATA"].format(device_id=device_id)
        )
        return self._normalize_devdata(data)

    async def get_datapoints(self, product_key: str) -> dict:
        """Return the datapoint schema for a product."""
        if self._api_mode == API_MODE_AEP:
            await self.ensure_valid_token()
            try:
                body = await self._aep_request(
                    "GET",
                    self._aep_url(AEP_PATH_DATAPOINT),
                    params={"product_key": product_key},
                )
            except AquaMedicConnectionError as exc:
                if "HTTP 404" not in str(exc):
                    raise
                _LOGGER.debug(
                    "AEP datapoint unavailable for %s, using Open API host.",
                    product_key,
                )
                body = await self._request_json(
                    "GET",
                    self._open_api_url(AEP_PATH_DATAPOINT),
                    headers=self._open_api_headers(),
                    params={"product_key": product_key},
                )
            if "code" in body:
                inner = self._parse_aep_envelope(body)
                return inner if isinstance(inner, dict) else {"data": inner}
            return body
        return await self._get_legacy(
            self._legacy_urls["DATAPOINT"], params={"product_key": product_key}
        )

    async def control_device(self, device_id: str, attrs: dict) -> None:
        """Send a control command to *device_id*."""
        if self._api_mode == API_MODE_AEP:
            try:
                await self._control_device_aep(device_id, attrs)
                return
            except AquaMedicAuthError:
                if self._can_use_legacy():
                    await self._switch_to_legacy()
                    await self.control_device(device_id, attrs)
                    return
                raise

        url = self._legacy_urls["CONTROL"].format(device_id=device_id)
        await self._post_legacy(url, {"attrs": attrs}, authenticated=True)
        _LOGGER.debug("Legacy control sent to %s: %s", device_id, attrs)
