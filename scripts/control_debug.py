#!/usr/bin/env python3
"""Gateway / AEP control endpoint discovery tool.

The Gizwits AEP + Gateway API is not publicly documented.  This script
brute-forces every plausible combination of host / path / HTTP-method /
request-body to find which one actually controls the device.

RECOMMENDED USAGE (avoids re-login by loading tokens from HA storage):
  python scripts/control_debug.py --ha-config /config --did <device_id>
  python scripts/control_debug.py --ha-config /config --did <device_id> \\
      --send '{"SwitchON": 0}'

MANUAL TOKEN USAGE (if running outside HA):
  python scripts/control_debug.py user@mail.com \\
      --did <device_id> \\
      --access-token <jwt_token> \\
      --api-mode aep \\
      --device-list smart_home

FULL CREDENTIAL USAGE (only if HA tokens expired):
  python scripts/control_debug.py user@mail.com [password] --did <device_id>

Other options:
  --no-stop     Keep probing even after a success (find all working combos)
  --verbose     Show response bodies for every attempt (including 404/405)
  --single "METHOD HOST PATH BODY_KEY"   Test one explicit combination
"""

from __future__ import annotations

import argparse
import asyncio
import getpass
import json
import logging
import sys
from pathlib import Path
from typing import Any

import aiohttp

# ── Add project root so we can import the integration modules ────────────────
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from custom_components.aquamedic.client import AquaMedicClient  # noqa: E402
from custom_components.aquamedic.const import (  # noqa: E402
    CONF_ACCESS_TOKEN,
    CONF_API_MODE,
    CONF_DEVICE_LIST_API,
    CONF_REGION,
    DEVICE_LIST_SMART_HOME,
    DOMAIN,
    GIZWITS_APP_KEY,
    GIZWITS_GATEWAY_API_KEY,
    GIZWITS_REGION_ENDPOINTS,
    GIZWITS_USER_AGENT,
)

# ── ANSI colours ─────────────────────────────────────────────────────────────
RESET = "\033[0m"
BOLD = "\033[1m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
DIM = "\033[2m"
MAGENTA = "\033[95m"


def _ok(msg: str) -> None:
    print(f"{GREEN}✅ {msg}{RESET}")


def _warn(msg: str) -> None:
    print(f"{YELLOW}⚠️  {msg}{RESET}")


def _err(msg: str) -> None:
    print(f"{RED}❌ {msg}{RESET}")


def _info(msg: str) -> None:
    print(f"{CYAN}🔎 {msg}{RESET}")


def _step(msg: str) -> None:
    print(f"\n{BOLD}{msg}{RESET}")


def _dim(msg: str) -> None:
    print(f"{DIM}{msg}{RESET}")


# ── Load credentials from HA storage ─────────────────────────────────────────


def load_ha_config_entry(ha_config_dir: str) -> dict | None:
    """Parse /config/.storage/core.config_entries and return the aquamedic entry data."""
    storage = Path(ha_config_dir) / ".storage" / "core.config_entries"
    if not storage.exists():
        _err(f"HA storage not found: {storage}")
        return None
    try:
        raw = json.loads(storage.read_text())
    except Exception as exc:
        _err(f"Cannot read HA storage: {exc}")
        return None

    entries = raw.get("data", {}).get("entries", [])
    aquamedic = [e for e in entries if e.get("domain") == DOMAIN]
    if not aquamedic:
        _err(f"No '{DOMAIN}' config entry found in {storage}")
        return None
    if len(aquamedic) > 1:
        _warn(f"{len(aquamedic)} aquamedic entries found — using the first one.")
        for i, e in enumerate(aquamedic):
            _dim(
                f"  [{i}] {e.get('title', '?')} — {e.get('data', {}).get('username', '?')}"
            )
    entry = aquamedic[0]
    data = entry.get("data", {})
    _ok(f"Loaded HA config entry: {entry.get('title', '?')}")
    return data


# ── Candidate endpoint matrix ─────────────────────────────────────────────────

CANDIDATE_PATHS: list[tuple[str, str, list[str], list[str]]] = [
    # ── Gateway controller paths ──────────────────────────────────────────────
    (
        "gateway",
        "/v2/devices-controller/devices/{did}",
        ["PUT", "PATCH", "POST", "DELETE"],
        ["attrs", "datas"],
    ),
    (
        "gateway",
        "/v2/devices-controller/devices/{did}/control",
        ["POST", "PUT", "PATCH"],
        ["attrs", "datas", "raw_attrs"],
    ),
    (
        "gateway",
        "/v2/devices-controller/devices/{did}/attrs",
        ["POST", "PUT", "PATCH"],
        ["attrs", "raw_attrs"],
    ),
    (
        "gateway",
        "/v2/devices-controller/devices/{did}/cmd",
        ["POST"],
        ["attrs", "raw_attrs"],
    ),
    (
        "gateway",
        "/v1/devices-controller/devices/{did}",
        ["POST", "PUT", "PATCH"],
        ["attrs", "datas"],
    ),
    (
        "gateway",
        "/v1/devices-controller/devices/{did}/control",
        ["POST", "PUT"],
        ["attrs", "raw_attrs"],
    ),
    (
        "gateway",
        "/v2/devices-manager/devices/{did}/control",
        ["POST", "PUT", "PATCH"],
        ["attrs", "datas"],
    ),
    (
        "gateway",
        "/v2/devices-controller/control",
        ["POST"],
        ["attrs_with_did", "datas_with_did"],
    ),
    # ── AEP host paths ────────────────────────────────────────────────────────
    ("aep", "/app/control/{did}", ["POST", "PUT"], ["attrs", "datas"]),
    (
        "aep",
        "/app/smartHome/v1/devices/{did}/control",
        ["POST", "PUT"],
        ["attrs", "datas"],
    ),
    (
        "aep",
        "/app/smartHome/v2/devices/{did}/control",
        ["POST", "PUT"],
        ["attrs", "datas"],
    ),
    (
        "aep",
        "/app/smartHome/v1/devices/{did}/attrs",
        ["POST", "PUT", "PATCH"],
        ["attrs", "raw_attrs"],
    ),
    (
        "aep",
        "/app/smartHome/v2/devices/{did}/attrs",
        ["POST", "PUT", "PATCH"],
        ["attrs", "raw_attrs"],
    ),
    ("aep", "/app/device/{did}/control", ["POST", "PUT"], ["attrs", "raw_attrs"]),
    # ── Legacy Open API host — header variants ────────────────────────────────
    # Baseline (JWT in Authorization) → known 400 "token invalid" on this account.
    ("open_api", "/app/control/{did}", ["POST"], ["attrs"]),
    # JWT placed in X-Gizwits-User-token instead of Authorization.
    ("open_api_jwt_tok", "/app/control/{did}", ["POST"], ["attrs"]),
    # Legacy app_id (iOS, GIZWITS_LEGACY_APP_ID) + JWT as Authorization.
    ("open_api_leg_id", "/app/control/{did}", ["POST"], ["attrs"]),
    # Legacy app_id + JWT as X-Gizwits-User-token.
    ("open_api_leg_tok", "/app/control/{did}", ["POST"], ["attrs"]),
    # JWT in BOTH headers simultaneously.
    ("open_api_both", "/app/control/{did}", ["POST"], ["attrs"]),
    # No Authorization at all — only X-Gizwits-User-token with JWT.
    ("open_api_tok_only", "/app/control/{did}", ["POST"], ["attrs"]),
    # AEP host /app/control with JWT as X-Gizwits-User-token instead of Authorization.
    ("aep_jwt_tok", "/app/control/{did}", ["POST"], ["attrs"]),
]


def _build_bodies(attrs: dict, did: str) -> dict[str, dict]:
    return {
        "attrs": {"attrs": attrs},
        "datas": {"datas": [{"attrs": attrs}]},
        "raw_attrs": attrs,
        "attrs_with_did": {"did": did, "attrs": attrs},
        "datas_with_did": {"did": did, "datas": [{"attrs": attrs}]},
    }


# ── Raw HTTP probe ────────────────────────────────────────────────────────────


async def _probe(
    session: aiohttp.ClientSession,
    method: str,
    url: str,
    headers: dict[str, str],
    body: dict,
    timeout: int = 10,
) -> tuple[int, Any]:
    """Return (http_status, parsed_body).  Never raises."""
    try:
        async with session.request(
            method,
            url,
            headers=headers,
            json=body,
            timeout=aiohttp.ClientTimeout(total=timeout),
            ssl=False,
        ) as resp:
            text = await resp.text()
            try:
                data = json.loads(text) if text.strip() else {}
            except json.JSONDecodeError:
                data = text[:300]
            return resp.status, data
    except aiohttp.ClientConnectorError as exc:
        return -1, f"Connection error: {exc}"
    except asyncio.TimeoutError:
        return -2, "Timeout"
    except Exception as exc:  # noqa: BLE001
        return -3, f"Error: {exc}"


def _classify(status: int, body: Any) -> str:
    if status in range(200, 300):
        return f"{GREEN}{BOLD}SUCCESS{RESET}"
    if status == 404:
        return f"{DIM}NOT FOUND (404){RESET}"
    if status == 405:
        return f"{YELLOW}METHOD NOT ALLOWED (405){RESET}"
    if status in (401, 403):
        return f"{RED}AUTH ERROR ({status}){RESET}"
    if status < 0:
        return f"{DIM}NETWORK ERROR ({status}){RESET}"
    if status == 500 and isinstance(body, dict):
        inner = str(body.get("code", ""))
        if inner == "405":
            return f"{YELLOW}METHOD NOT ALLOWED (500/405){RESET}"
        if inner == "404":
            return f"{DIM}NOT FOUND (500/404){RESET}"
    return f"{MAGENTA}UNEXPECTED ({status}){RESET}"


def _is_success(status: int) -> bool:
    return 200 <= status < 300


def _is_interesting(status: int, body: Any) -> bool:
    if _is_success(status):
        return True
    if status < 0 or status == 404 or status == 405:
        return False
    if status == 500 and isinstance(body, dict):
        if str(body.get("code", "")) in ("404", "405"):
            return False
    return True


# ── Main probe loop ───────────────────────────────────────────────────────────


def _build_header_sets(jwt: str, legacy_token: str, region: str) -> dict[str, dict]:
    from custom_components.aquamedic.const import GIZWITS_LEGACY_APP_ID

    aep_h = {
        "Content-Type": "application/json",
        "Version": "1.0",
        "X-Gizwits-Application-Id": GIZWITS_APP_KEY,
        "User-Agent": GIZWITS_USER_AGENT,
        "Authorization": jwt,
    }
    gw_h = dict(aep_h)
    gw_h["X-Gizwits-Api-Key"] = GIZWITS_GATEWAY_API_KEY

    # baseline: JWT in Authorization (was already tried → 400 "token invalid")
    open_api_h = {
        "Content-Type": "application/json",
        "X-Gizwits-Application-Id": GIZWITS_APP_KEY,
        "User-Agent": GIZWITS_USER_AGENT,
        "Authorization": jwt,
    }
    if legacy_token:
        open_api_h["X-Gizwits-User-token"] = legacy_token

    # JWT as X-Gizwits-User-token, no Authorization
    open_api_jwt_tok = {
        "Content-Type": "application/json",
        "X-Gizwits-Application-Id": GIZWITS_APP_KEY,
        "User-Agent": GIZWITS_USER_AGENT,
        "X-Gizwits-User-token": jwt,
    }
    # Legacy iOS app_id + JWT as Authorization
    open_api_leg_id = {
        "Content-Type": "application/json",
        "X-Gizwits-Application-Id": GIZWITS_LEGACY_APP_ID,
        "User-Agent": GIZWITS_USER_AGENT,
        "Authorization": jwt,
    }
    # Legacy iOS app_id + JWT as X-Gizwits-User-token
    open_api_leg_tok = {
        "Content-Type": "application/json",
        "X-Gizwits-Application-Id": GIZWITS_LEGACY_APP_ID,
        "User-Agent": GIZWITS_USER_AGENT,
        "X-Gizwits-User-token": jwt,
    }
    # JWT in BOTH Authorization AND X-Gizwits-User-token
    open_api_both = {
        "Content-Type": "application/json",
        "X-Gizwits-Application-Id": GIZWITS_APP_KEY,
        "User-Agent": GIZWITS_USER_AGENT,
        "Authorization": jwt,
        "X-Gizwits-User-token": jwt,
    }
    # Only X-Gizwits-User-token (JWT), no Authorization at all
    open_api_tok_only = {
        "Content-Type": "application/json",
        "X-Gizwits-Application-Id": GIZWITS_APP_KEY,
        "User-Agent": GIZWITS_USER_AGENT,
        "X-Gizwits-User-token": jwt,
    }
    # AEP host /app/control with JWT as X-Gizwits-User-token
    aep_jwt_tok = {
        "Content-Type": "application/json",
        "Version": "1.0",
        "X-Gizwits-Application-Id": GIZWITS_APP_KEY,
        "User-Agent": GIZWITS_USER_AGENT,
        "X-Gizwits-User-token": jwt,
    }

    return {
        "aep": aep_h,
        "gateway": gw_h,
        "open_api": open_api_h,
        "open_api_jwt_tok": open_api_jwt_tok,
        "open_api_leg_id": open_api_leg_id,
        "open_api_leg_tok": open_api_leg_tok,
        "open_api_both": open_api_both,
        "open_api_tok_only": open_api_tok_only,
        "aep_jwt_tok": aep_jwt_tok,
    }


async def run_probe(
    session: aiohttp.ClientSession,
    jwt: str,
    legacy_token: str,
    did: str,
    attrs: dict,
    region: str,
    verbose: bool = False,
    stop_on_success: bool = True,
) -> bool:
    endpoints = GIZWITS_REGION_ENDPOINTS.get(region, GIZWITS_REGION_ENDPOINTS["eu"])
    _aep = endpoints["aep_base"].rstrip("/")
    _gw = endpoints["gateway_base"].rstrip("/")
    _oa = endpoints["open_api_base"].rstrip("/")
    base_map = {
        "aep": _aep,
        "gateway": _gw,
        "open_api": _oa,
        "open_api_jwt_tok": _oa,
        "open_api_leg_id": _oa,
        "open_api_leg_tok": _oa,
        "open_api_both": _oa,
        "open_api_tok_only": _oa,
        "aep_jwt_tok": _aep,
    }
    headers_map = _build_header_sets(jwt, legacy_token, region)
    bodies = _build_bodies(attrs, did)

    total = sum(len(m) * len(b) for _, _, m, b in CANDIDATE_PATHS)
    _step(f"Probing {total} combinations → device {BOLD}{did}{RESET}")
    _dim(f"Attrs payload : {attrs}")
    _dim(f"Region        : {region}")
    _dim(f"JWT present   : {'yes' if jwt else 'NO — auth will likely fail!'}")
    print()

    done = 0
    interesting: list[tuple[str, str, str, int, Any]] = []
    success_found = False

    for host_key, path_tpl, methods, body_keys in CANDIDATE_PATHS:
        base = base_map[host_key]
        path = path_tpl.format(did=did)
        url = f"{base}{path}"
        hdrs = headers_map[host_key]

        for method in methods:
            for bk in body_keys:
                body = bodies[bk]
                done += 1
                label = (
                    f"[{done:>3}/{total}] "
                    f"{method:<6} {host_key:>8}  "
                    f"{path_tpl.replace('{did}', '…'):55}  body={bk}"
                )

                status, resp_body = await _probe(session, method, url, hdrs, body)
                verdict = _classify(status, resp_body)

                if _is_success(status):
                    _ok(label)
                    print(
                        f"\n         {GREEN}{BOLD}══ WORKING COMBINATION FOUND ══{RESET}"
                    )
                    print(f"         Method : {BOLD}{method}{RESET}")
                    print(f"         Host   : {host_key}  →  {base}")
                    print(f"         Path   : {path_tpl}")
                    print(
                        f"         Body   : {BOLD}{bk}{RESET}  →  {json.dumps(body, ensure_ascii=False)}"
                    )
                    print(f"         Status : {status}")
                    print(f"         Resp   : {resp_body}\n")
                    success_found = True
                    if stop_on_success:
                        return True
                elif _is_interesting(status, resp_body):
                    print(f"  {MAGENTA}?{RESET} {label}  →  {verdict}")
                    print(f"    Response: {resp_body}")
                    interesting.append((method, url, bk, status, resp_body))
                else:
                    if verbose:
                        print(f"    {label}  →  {verdict}")
                        _dim(f"    Response: {resp_body}")

    print()
    if success_found:
        _ok("Probe complete — working combination found above.")
    else:
        _err("No working control endpoint found across all 72 combinations.")
        if interesting:
            _warn(f"\n{len(interesting)} 'interesting' (non-404/405) response(s):")
            for method, url, bk, status, resp_body in interesting:
                print(f"  {method}  {url}  body={bk}  →  {status}")
                print(f"    {resp_body}")
        print()
        _dim(
            "Next step: capture the mobile app traffic with mitmproxy or Charles Proxy"
        )
        _dim("to find the actual control endpoint used by the official app.")

    return success_found


async def run_single(
    session: aiohttp.ClientSession,
    jwt: str,
    legacy_token: str,
    did: str,
    attrs: dict,
    region: str,
    method: str,
    host_key: str,
    path_tpl: str,
    body_key: str,
) -> None:
    endpoints = GIZWITS_REGION_ENDPOINTS.get(region, GIZWITS_REGION_ENDPOINTS["eu"])
    base_map = {
        "aep": endpoints["aep_base"].rstrip("/"),
        "gateway": endpoints["gateway_base"].rstrip("/"),
        "open_api": endpoints["open_api_base"].rstrip("/"),
    }
    base = base_map.get(host_key, endpoints["aep_base"]).rstrip("/")
    path = path_tpl.format(did=did)
    url = f"{base}{path}"
    hdrs = _build_header_sets(jwt, legacy_token, region)[host_key]
    body = _build_bodies(attrs, did).get(body_key, {"attrs": attrs})

    _step(f"Single probe: {method} {url}")
    print(f"  Body   : {json.dumps(body, ensure_ascii=False)}")
    status, resp = await _probe(session, method, url, hdrs, body)
    verdict = _classify(status, resp)
    print(f"  Status : {status}  →  {verdict}")
    print(f"  Resp   : {json.dumps(resp, ensure_ascii=False, indent=2)}")


# ── Credential resolution ─────────────────────────────────────────────────────


async def resolve_credentials(
    args: argparse.Namespace,
    session: aiohttp.ClientSession,
) -> tuple[str, str, str, str, str] | None:
    """
    Return (jwt, legacy_token, region, api_mode, device_list_api) or None on failure.
    Sources tried in order:
      1. --ha-config  → load from HA storage (best: no re-login needed)
      2. --access-token CLI arg
      3. Fresh login via AquaMedicClient.authenticate()
    """
    # ── 1. Load from HA storage ───────────────────────────────────────────────
    if args.ha_config:
        entry_data = load_ha_config_entry(args.ha_config)
        if entry_data is None:
            return None
        jwt = entry_data.get(CONF_ACCESS_TOKEN, "")
        region = entry_data.get(CONF_REGION, "eu")
        api_mode = entry_data.get(CONF_API_MODE, "aep")
        dev_list_api = entry_data.get(CONF_DEVICE_LIST_API, DEVICE_LIST_SMART_HOME)
        _info(f"Region={region}  api_mode={api_mode}  device_list={dev_list_api}")
        if not jwt:
            _warn("No access_token in HA entry — token may have been stripped.")
            _warn(
                "Use --access-token to pass it manually, or restart HA first to refresh."
            )
        return jwt, "", region, api_mode, dev_list_api

    # ── 2. Explicit token on CLI ──────────────────────────────────────────────
    if args.access_token:
        region = args.server
        api_mode = args.api_mode or "aep"
        dev_list_api = args.device_list or DEVICE_LIST_SMART_HOME
        _info(f"Using provided access token (region={region}, api_mode={api_mode})")
        return args.access_token, "", region, api_mode, dev_list_api

    # ── 3. Fresh login ────────────────────────────────────────────────────────
    username = args.username
    if not username:
        _err("Provide --ha-config, --access-token, or a username argument.")
        return None
    password = args.password or getpass.getpass(f"Password for {username}: ")
    region = args.server

    _info(f"Authenticating as {username} on {region}…")
    client = AquaMedicClient(
        session,
        username,
        password,
        region,
        lang="en",
        refresh_token=args.refresh_token,
    )
    try:
        await client.authenticate()
    except Exception as exc:  # noqa: BLE001
        _err(f"Authentication failed: {exc}")
        _warn("Tip: use --ha-config /config to load tokens directly from HA storage.")
        return None

    jwt = client.access_token or ""
    legacy_token = client._token or ""
    api_mode = client.api_mode
    dev_list_api = client.device_list_api or DEVICE_LIST_SMART_HOME
    _ok(f"Authenticated! api_mode={api_mode}  device_list={dev_list_api}")
    return jwt, legacy_token, region, api_mode, dev_list_api


# ── Entry point ───────────────────────────────────────────────────────────────


async def async_main(args: argparse.Namespace) -> int:
    if args.send:
        try:
            attrs = json.loads(args.send)
        except json.JSONDecodeError as exc:
            _err(f"--send payload is not valid JSON: {exc}")
            return 1
        _warn(f"CAUTION: payload will be sent to the device: {attrs}")
    else:
        attrs = {"SwitchON": 1}
        _info("No --send payload given.  Default probe payload: " + str(attrs))

    async with aiohttp.ClientSession() as session:
        creds = await resolve_credentials(args, session)
        if creds is None:
            return 1
        jwt, legacy_token, region, api_mode, dev_list_api = creds

        if not jwt:
            _warn("JWT is empty — unauthenticated probes will likely return 401/403.")

        if args.single:
            parts = args.single.split(maxsplit=3)
            if len(parts) != 4:
                _err("--single expects: METHOD HOST PATH BODY_KEY")
                _dim(
                    '  e.g.  --single "POST gateway /v2/devices-controller/devices/{did} attrs"'
                )
                return 1
            m, h, p, bk = parts
            await run_single(
                session, jwt, legacy_token, args.did, attrs, region, m, h, p, bk
            )
        else:
            found = await run_probe(
                session,
                jwt,
                legacy_token,
                did=args.did,
                attrs=attrs,
                region=region,
                verbose=args.verbose,
                stop_on_success=not args.no_stop,
            )
            return 0 if found else 1

    return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Gizwits Gateway / AEP control endpoint discovery",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
RECOMMENDED — load tokens directly from HA (no re-login):
  python scripts/control_debug.py --ha-config /config --did uIiXekjC3ZpPtz0sXfdVZk
  python scripts/control_debug.py --ha-config /config --did uIiXekjC3ZpPtz0sXfdVZk \\
      --send '{"SwitchON": 0}'

Use explicit token (get it from HA storage or logs):
  python scripts/control_debug.py --access-token <jwt> \\
      --did uIiXekjC3ZpPtz0sXfdVZk --api-mode aep --device-list smart_home

Full credential login (only if HA tokens are expired):
  python scripts/control_debug.py user@mail.com --did uIiXekjC3ZpPtz0sXfdVZk

Test a single specific combination:
  python scripts/control_debug.py --ha-config /config --did uIiXekjC3ZpPtz0sXfdVZk \\
      --single "POST gateway /v2/devices-controller/devices/{did} attrs"

Body key reference:
  attrs          {"attrs": payload}
  datas          {"datas": [{"attrs": payload}]}
  raw_attrs      payload (bare dict)
  attrs_with_did {"did": ..., "attrs": payload}
  datas_with_did {"did": ..., "datas": [...]}
        """,
    )

    # Credential sources (mutually exclusive groups)
    cred = parser.add_argument_group("credentials (use one of these three approaches)")
    cred.add_argument(
        "--ha-config",
        metavar="DIR",
        help="HA config dir, e.g. /config  (reads .storage/core.config_entries)",
    )
    cred.add_argument(
        "--access-token",
        metavar="JWT",
        help="JWT access token (from HA storage or logs)",
    )
    cred.add_argument(
        "--refresh-token",
        metavar="TOKEN",
        default=None,
        help="AEP refresh token (optional, used with fresh login)",
    )
    cred.add_argument(
        "username", nargs="?", default=None, help="Email (only needed for fresh login)"
    )
    cred.add_argument(
        "password",
        nargs="?",
        default=None,
        help="Password (prompted securely if omitted)",
    )

    # Target
    tgt = parser.add_argument_group("target")
    tgt.add_argument(
        "--did", required=True, metavar="DEVICE_ID", help="Device ID to probe"
    )
    tgt.add_argument(
        "--server",
        default="eu",
        choices=list(GIZWITS_REGION_ENDPOINTS.keys()),
        help="Gizwits region (default: eu)",
    )
    tgt.add_argument(
        "--api-mode",
        default=None,
        choices=["aep", "legacy"],
        help="Force API mode (default: from token source)",
    )
    tgt.add_argument(
        "--device-list",
        default=None,
        choices=["smart_home", "bindings"],
        help="Force device list API (default: from token source)",
    )

    # Probe options
    probe = parser.add_argument_group("probe options")
    probe.add_argument(
        "--send",
        default=None,
        metavar="JSON",
        help="Attrs payload to send, e.g. '{\"SwitchON\": 0}'",
    )
    probe.add_argument(
        "--no-stop", action="store_true", help="Continue probing after first success"
    )
    probe.add_argument(
        "--verbose", action="store_true", help="Show all responses including 404/405"
    )
    probe.add_argument(
        "--single",
        default=None,
        metavar='"METHOD HOST PATH BODY"',
        help="Test one combination explicitly",
    )

    args = parser.parse_args()

    log_level = logging.DEBUG if args.verbose else logging.WARNING
    logging.basicConfig(level=log_level, format="%(levelname)s %(name)s: %(message)s")

    sys.exit(asyncio.run(async_main(args)))


if __name__ == "__main__":
    main()
