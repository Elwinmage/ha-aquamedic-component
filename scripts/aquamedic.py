import requests
import argparse
import uuid
import sys
import json
import os
import getpass

# ── ANSI color helpers ────────────────────────────────────────────────────────
RESET = "\033[0m"
BOLD = "\033[1m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
DIM = "\033[2m"
MAGENTA = "\033[95m"


def ok(msg):
    print(f"{GREEN}✅ {msg}{RESET}")


def warn(msg):
    print(f"{YELLOW}⚠️  {msg}{RESET}")


def err(msg):
    print(f"{RED}❌ {msg}{RESET}")


def info(msg):
    print(f"{CYAN}🔎 {msg}{RESET}")


def step(msg):
    print(f"{BOLD}{msg}{RESET}")


# ── Confirmed Identifiers ────────────────────────────────────────────────────
# Android app key — used for AEP + Gateway (primary API path, mirrors const.py).
GIZWITS_APP_KEY = "b45f1f4f31f546378fcfaed7775c4d12"
# iOS app id — legacy Open API fallback only.
GIZWITS_LEGACY_APP_ID = "07452c4f036a4be3acedf8dbeef38320"
GIZWITS_USER_AGENT = "gizwitssuperapprn/154300000 CFNetwork/3826.500.131 Darwin/24.5.0"

# ── Gizwits regional servers ─────────────────────────────────────────────────
# Mirrors GIZWITS_REGION_ENDPOINTS in const.py (both AEP and legacy Open API).
GIZWITS_SERVERS = {
    "eu": {
        "label": "Europe",
        "aep_base": "https://euaepapp.gizwits.com",
        "open_api_base": "https://euapi.gizwits.com",
    },
    "us": {
        "label": "USA / Asia",
        "aep_base": "https://usaepapp.gizwits.com",
        "open_api_base": "https://usapi.gizwits.com",
    },
    "cn": {
        "label": "China",
        "aep_base": "https://aep-app.gizwits.com",
        "open_api_base": "https://api.gizwits.com",
    },
}

# Order used by auto-detection: EU first (most common for Aqua Medic users)
AUTO_TRY_ORDER = ["eu", "us", "cn"]

# ── AEP path suffixes (same across regions) ──────────────────────────────────
AEP_PATH_LOGIN_PWD = "/app/smart_home/login/pwd"
AEP_PATH_BINDINGS = "/app/bindings"
AEP_PATH_USER_DEVICES = "/app/smartHome/v2/users/devices"
AEP_PATH_DEVDATA = "/app/devdata/{device_id}/latest"
AEP_PATH_DATAPOINT = "/app/datapoint"

# ── Legacy Open API path suffixes ────────────────────────────────────────────
LEGACY_PATH_PROVISION = "/app/provision"
LEGACY_PATH_LOGIN = "/app/login"
LEGACY_PATH_BINDINGS = "/app/bindings"
LEGACY_PATH_DEVDATA = "/app/devdata/{device_id}/latest"
LEGACY_PATH_DATAPOINT = "/app/datapoint"


def build_urls(server_conf: dict) -> dict:
    """Return all API URLs derived from a regional server config.

    Bundles AEP and Open API endpoints so the caller can transparently switch
    between the two, exactly like the HA client does.
    """
    aep = server_conf["aep_base"].rstrip("/")
    legacy = server_conf["open_api_base"].rstrip("/")
    return {
        # AEP endpoints (primary)
        "aep_login": f"{aep}{AEP_PATH_LOGIN_PWD}",
        "aep_bindings": f"{aep}{AEP_PATH_BINDINGS}",
        "aep_user_devices": f"{aep}{AEP_PATH_USER_DEVICES}",
        "aep_devdata": f"{aep}{AEP_PATH_DEVDATA}",
        "aep_datapoint": f"{aep}{AEP_PATH_DATAPOINT}",
        # Legacy Open API endpoints (fallback)
        "legacy_provision": f"{legacy}{LEGACY_PATH_PROVISION}",
        "legacy_login": f"{legacy}{LEGACY_PATH_LOGIN}",
        "legacy_bindings": f"{legacy}{LEGACY_PATH_BINDINGS}",
        "legacy_devdata": f"{legacy}{LEGACY_PATH_DEVDATA}",
        "legacy_datapoint": f"{legacy}{LEGACY_PATH_DATAPOINT}",
    }


def build_sim_urls(base: str) -> dict:
    """Build URL map for the local simulator (legacy Open API shape only)."""
    b = base.rstrip("/")
    return {
        "aep_login": None,
        "aep_bindings": None,
        "aep_user_devices": None,
        "aep_devdata": None,
        "aep_datapoint": None,
        "legacy_provision": f"{b}/provision",
        "legacy_login": f"{b}/login",
        "legacy_bindings": f"{b}/bindings",
        "legacy_devdata": f"{b}/devdata/{{device_id}}/latest",
        "legacy_datapoint": f"{b}/datapoint",
    }


# ── AEP helpers ──────────────────────────────────────────────────────────────


def aep_headers(jwt: str | None = None) -> dict:
    """Build headers for AEP requests (with optional JWT for authenticated calls)."""
    h = {
        "Content-Type": "application/json",
        "Version": "1.0",
        "X-Gizwits-Application-Id": GIZWITS_APP_KEY,
        "User-Agent": GIZWITS_USER_AGENT,
    }
    if jwt:
        h["Authorization"] = jwt
    return h


def wrap_aep(data: dict) -> dict:
    """Wrap payload in the AEP envelope required by /app/smart_home endpoints."""
    return {"appKey": GIZWITS_APP_KEY, "data": data, "version": "1.0"}


def parse_aep_envelope(body: dict) -> dict:
    """Extract inner 'data' from AEP response; return the whole body otherwise."""
    inner = body.get("data")
    if isinstance(inner, dict):
        return inner
    return body


def aep_code_is_success(code) -> bool:
    """Return True when AEP envelope code indicates success (200 or missing)."""
    if code is None:
        return True
    try:
        return int(code) == 200
    except (TypeError, ValueError):
        return False


def aep_login(session, username, password, urls, lang="fr"):
    """Try AEP login.

    Returns (jwt, None) on success, or (None, detail) on failure. The detail
    string is designed to be actionable — the caller can decide whether to
    fall back to legacy or stop.
    """
    try:
        res = session.post(
            urls["aep_login"],
            headers=aep_headers(),
            json=wrap_aep(
                {
                    "account": username,
                    "password": password,
                    "lang": lang,
                    "refreshToken": True,
                }
            ),
            timeout=10,
        )
    except requests.RequestException as exc:
        return None, f"network: {exc}"

    if res.status_code != 200:
        try:
            body = res.json()
            code = body.get("code", "")
            message = body.get("message") or res.text
            return None, f"HTTP {res.status_code} (code={code}): {message}"
        except ValueError:
            return None, f"HTTP {res.status_code}: {res.text[:200]}"

    try:
        body = res.json()
    except ValueError:
        return None, "Invalid JSON in AEP login response"

    code = body.get("code")
    if not aep_code_is_success(code):
        return None, f"AEP error {code}: {body.get('message', body)}"

    data = parse_aep_envelope(body)
    jwt_block = data.get("jwtAuthenticationDto") or {}
    jwt = jwt_block.get("token") or data.get("token")
    if not jwt:
        return None, f"No JWT in AEP response: {data}"
    return jwt, None


def aep_get_devices(session, jwt, urls):
    """Fetch devices via AEP: smartHome first, /app/bindings only on real failure.

    Mirrors client.py::_detect_device_list_api logic — a smartHome success
    (even with zero devices) means this is a migrated account and bindings
    is expected to return 404.
    """
    info("Fetching devices via AEP /smartHome/v2/users/devices...")
    res = session.get(urls["aep_user_devices"], headers=aep_headers(jwt), timeout=10)

    smart_home_reachable = False
    smart_home_body = None
    if res.status_code == 200:
        try:
            smart_home_body = res.json()
        except ValueError:
            smart_home_body = None
        if smart_home_body is not None:
            code = smart_home_body.get("code")
            if aep_code_is_success(code):
                smart_home_reachable = True
                data = (
                    parse_aep_envelope(smart_home_body)
                    if "code" in smart_home_body
                    else smart_home_body
                )
                devices = _extract_devices(data)
                if devices:
                    ok(f"smartHome returned {len(devices)} device(s).")
                    return devices
                # Successful response but nothing extracted — dump raw payload
                # so the user can see whether it is truly empty or in an
                # unrecognized shape.
                warn(
                    "smartHome responded successfully but no devices were "
                    "extracted. Raw response follows:"
                )
                print(json.dumps(smart_home_body, indent=2, ensure_ascii=False))
            else:
                warn(
                    f"smartHome AEP error code={code}: "
                    f"{smart_home_body.get('message', smart_home_body)}"
                )
    else:
        warn(f"smartHome HTTP {res.status_code}: {res.text[:200]}")

    # Only try bindings when smartHome truly errored out — a migrated account
    # returns 404 on bindings and we do not want to muddle the diagnosis.
    if smart_home_reachable:
        info(
            "smartHome responded — skipping /app/bindings "
            "(returns 404 on migrated accounts by design)."
        )
        return []

    info("smartHome unavailable, trying AEP /app/bindings...")
    res = session.get(
        urls["aep_bindings"],
        headers=aep_headers(jwt),
        params={"limit": 50, "skip": 0},
        timeout=10,
    )
    if res.status_code == 404:
        err("AEP bindings also returned 404 — cannot list devices on AEP.")
        return []
    if res.status_code != 200:
        err(f"AEP bindings error ({res.status_code}): {res.text[:200]}")
        return []
    try:
        body = res.json()
    except ValueError:
        return []
    if not aep_code_is_success(body.get("code")):
        warn(f"AEP bindings code={body.get('code')}: {body.get('message')}")
        return []
    data = parse_aep_envelope(body) if "code" in body else body
    devices = _extract_devices(data)
    if devices:
        ok(f"bindings returned {len(devices)} device(s).")
    return devices


def _extract_devices(data) -> list:
    """Normalize device list from various AEP / smartHome / bindings shapes.

    Handles: raw list, {devices|deviceList|list|records|items: [...]},
    and one level of {data|result: <same shapes>} nesting.
    """
    device_keys = ("devices", "deviceList", "list", "records", "items")

    if isinstance(data, list):
        return data
    if not isinstance(data, dict):
        return []

    # Direct keys.
    for key in device_keys:
        val = data.get(key)
        if isinstance(val, list):
            return val

    # One level of nesting under data/result.
    for wrapper in ("data", "result"):
        inner = data.get(wrapper)
        if isinstance(inner, list):
            return inner
        if isinstance(inner, dict):
            for key in device_keys:
                val = inner.get(key)
                if isinstance(val, list):
                    return val
    return []


def aep_get_device_latest(session, jwt, device_id, urls):
    """Fetch latest attrs for a device on the AEP host."""
    url = urls["aep_devdata"].format(device_id=device_id)
    res = session.get(
        url,
        headers=aep_headers(jwt),
        params={"show_expected_status": 1},
        timeout=10,
    )
    if res.status_code != 200:
        warn(f"AEP devdata unavailable ({res.status_code}): {res.text[:120]}")
        return None
    try:
        body = res.json()
    except ValueError:
        return None
    if "code" in body:
        if not aep_code_is_success(body.get("code")):
            warn(f"AEP devdata error {body.get('code')}: {body.get('message')}")
            return None
        return parse_aep_envelope(body)
    return body


def aep_get_datapoints(session, jwt, product_key, urls):
    """Fetch datapoint schema via AEP (with Open API host fallback on 404)."""
    res = session.get(
        urls["aep_datapoint"],
        headers=aep_headers(jwt),
        params={"product_key": product_key},
        timeout=10,
    )
    if res.status_code == 404:
        # Some product keys are only served by the legacy Open API host.
        res = session.get(
            urls["legacy_datapoint"],
            headers={
                "Content-Type": "application/json",
                "X-Gizwits-Application-Id": GIZWITS_APP_KEY,
                "User-Agent": GIZWITS_USER_AGENT,
            },
            params={"product_key": product_key},
            timeout=10,
        )
    if res.status_code != 200:
        warn(f"Datapoints not available ({res.status_code}): {res.text[:120]}")
        return None
    try:
        body = res.json()
    except ValueError:
        return None
    if "code" in body:
        return parse_aep_envelope(body)
    return body


# ── Legacy Open API helpers (fallback for non-migrated accounts) ─────────────


def legacy_headers(token=None):
    """Build headers for legacy Open API requests."""
    h = {
        "X-Gizwits-Application-Id": GIZWITS_LEGACY_APP_ID,
        "Content-Type": "application/json",
        "User-Agent": GIZWITS_USER_AGENT,
    }
    if token:
        h["X-Gizwits-User-token"] = token
    return h


def legacy_provision(session, phone_id, urls):
    """Provision a virtual mobile client — legacy prerequisite for login."""
    step(f"Provisioning legacy client (Phone ID: {phone_id[:8]}...)...")
    res = session.post(
        urls["legacy_provision"],
        headers=legacy_headers(),
        json={
            "phone_id": phone_id,
            "os": "Linux",
            "os_ver": "5.4",
            "sdk_version": "2.23.23.01613",
            "phone_model": "Python-Client",
        },
        timeout=10,
    )
    if res.status_code == 200:
        ok("Provisioning successful.")
    else:
        warn(f"Provisioning ignored or failed ({res.status_code})")


def legacy_login(session, username, password, urls):
    """Authenticate against the legacy Open API and return the token."""
    try:
        res = session.post(
            urls["legacy_login"],
            headers=legacy_headers(),
            json={"username": username, "password": password},
            timeout=10,
        )
    except requests.RequestException as exc:
        return None, f"network: {exc}"
    if res.status_code != 200:
        try:
            body = res.json()
            code = body.get("error_code", "")
            detail = body.get("detail") or body.get("error_message") or res.text
            return None, f"HTTP {res.status_code} (code={code}): {detail}"
        except ValueError:
            return None, f"HTTP {res.status_code}: {res.text[:200]}"
    return res.json().get("token"), None


def legacy_get_devices(session, token, urls):
    """Fetch all devices via legacy /bindings."""
    info("Fetching devices via legacy /bindings...")
    res = session.get(
        f"{urls['legacy_bindings']}?limit=20",
        headers=legacy_headers(token),
        timeout=10,
    )
    if res.status_code != 200:
        err(f"Bindings error ({res.status_code}): {res.text}")
        return []
    return res.json().get("devices", [])


def legacy_get_device_latest(session, token, device_id, urls):
    """Fetch latest attrs for a device (legacy Open API)."""
    url = urls["legacy_devdata"].format(device_id=device_id)
    res = session.get(url, headers=legacy_headers(token), timeout=10)
    if res.status_code == 200:
        return res.json()
    warn(f"Unable to fetch status ({res.status_code}): {res.text[:120]}")
    return None


def legacy_get_datapoints(session, token, product_key, urls):
    """Fetch datapoint schema (legacy Open API)."""
    res = session.get(
        urls["legacy_datapoint"],
        headers=legacy_headers(token),
        params={"product_key": product_key},
        timeout=10,
    )
    if res.status_code == 200:
        return res.json()
    warn(f"Datapoints not available ({res.status_code}): {res.text[:120]}")
    return None


# ── Auto-detect: AEP first per region, then legacy per region ────────────────


def auto_detect_server(session, username, password, lang="fr"):
    """Try AEP on every region first, then legacy on every region.

    Returns (region, urls, api_mode, token) on success, or None-tuple on failure.
    api_mode is either "aep" or "legacy" and token is the JWT (AEP) or
    legacy token accordingly.
    """
    step(f"\n{MAGENTA}🌍 Auto-detect: trying AEP on all regions first...{RESET}\n")

    # Phase 1 — AEP login (primary, migrated accounts).
    for region in AUTO_TRY_ORDER:
        srv = GIZWITS_SERVERS[region]
        urls = build_urls(srv)
        label = srv["label"]
        info(f"AEP {label} ({region})...")
        jwt, error = aep_login(session, username, password, urls, lang=lang)
        if jwt:
            ok(f"  AEP success on {BOLD}{label} ({region}){RESET}")
            return region, urls, "aep", jwt
        # 500/526/1000033 = auth errors (bad credentials or unknown account
        # on this region). Try next region rather than stopping — the same
        # account might live on another AEP region.
        warn(f"  AEP {label}: {error}")

    # Phase 2 — Legacy Open API fallback (older / non-migrated accounts).
    step(f"\n{MAGENTA}🌍 AEP failed on every region — trying legacy...{RESET}\n")
    phone_id = str(uuid.uuid4()).upper()
    for region in AUTO_TRY_ORDER:
        srv = GIZWITS_SERVERS[region]
        urls = build_urls(srv)
        label = srv["label"]
        info(f"Legacy {label} ({region})...")

        # Provision is legacy-only and non-fatal.
        try:
            session.post(
                urls["legacy_provision"],
                headers=legacy_headers(),
                json={
                    "phone_id": phone_id,
                    "os": "Linux",
                    "os_ver": "5.4",
                    "sdk_version": "2.23.23.01613",
                    "phone_model": "Python-Client",
                },
                timeout=10,
            )
        except requests.RequestException:
            warn(f"  Legacy {label}: server unreachable, skipping.")
            continue

        token, error = legacy_login(session, username, password, urls)
        if token:
            ok(f"  Legacy success on {BOLD}{label} ({region}){RESET}")
            return region, urls, "legacy", token

        # 9004 (wrong password) / 9020 (unknown user) / 9026 (migrated account)
        # are definitive on a reachable server — stop right there.
        if error and any(c in error for c in ("9004", "9020", "9026")):
            err(f"  Legacy {label}: credentials rejected — {error}")
            if "9020" in error:
                err(
                    "  Account not found on legacy Open API. This usually means "
                    "the account exists only on AEP but AEP login also failed — "
                    "check the password (special characters need quoting)."
                )
            return None, None, None, None
        warn(f"  Legacy {label}: {error}")

    return None, None, None, None


# ── Display helpers ──────────────────────────────────────────────────────────


def save_datapoints(device, schema, output_dir):
    """Save the raw datapoint schema to a JSON file in output_dir."""
    os.makedirs(output_dir, exist_ok=True)

    name = device.get("dev_alias") or device.get("product_name") or "unknown"
    safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in name)
    product_key = device.get("product_key", "unknown")
    filename = f"{safe_name}_{product_key}.json"
    filepath = os.path.join(output_dir, filename)

    payload = {
        "device": {
            "dev_alias": device.get("dev_alias"),
            "product_name": device.get("product_name"),
            "did": device.get("did"),
            "product_key": product_key,
            "is_online": device.get("is_online"),
        },
        "datapoints": schema,
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=4, ensure_ascii=False)

    ok(f"Datapoints saved -> {filepath}")


def describe_datapoint(dp):
    """Return a human-readable one-liner for a single datapoint."""
    name = dp.get("name", "?")
    display = dp.get("display_name", name)
    rw_raw = dp.get("rw", "?")
    rw = "R/W" if rw_raw == "rw" else ("R" if rw_raw == "ro" else "W")
    dp_type = dp.get("type", "?")
    unit = dp.get("unit", "")

    extra = ""
    if dp_type == "enum":
        extra = f"  values: {dp.get('enum', [])}"
    elif dp_type in ("uint8", "uint16", "uint32", "int8", "int16", "int32"):
        lo, hi = dp.get("min", "?"), dp.get("max", "?")
        extra = f"  range: {lo}-{hi}{(' ' + unit) if unit else ''}"
    elif dp_type == "bool":
        extra = "  values: 0 (off) / 1 (on)"

    rw_color = GREEN if "W" in rw else DIM
    return (
        f"    {rw_color}[{rw}]{RESET} "
        f"{BOLD}{display}{RESET} "
        f"{DIM}(attr: {name}, type: {dp_type}){RESET}"
        f"{CYAN}{extra}{RESET}"
    )


def _normalize_device(device: dict) -> dict:
    """Normalize AEP/legacy device records to a common shape for display."""
    # AEP smartHome uses camelCase, legacy uses snake_case — merge both.
    normalized = dict(device)
    normalized["did"] = device.get("did") or device.get("deviceId") or "?"
    normalized["product_key"] = (
        device.get("product_key") or device.get("productKey") or ""
    )
    name = (
        device.get("dev_alias")
        or device.get("product_name")
        or device.get("name")
        or "Unknown"
    )
    normalized["dev_alias"] = name
    if not normalized.get("product_name"):
        normalized["product_name"] = name
    online = device.get("is_online")
    if online is None:
        online = device.get("isOnline")
    if online is None and device.get("wifiOnline") is not None:
        online = bool(device.get("wifiOnline"))
    if online is None and device.get("netStatus") is not None:
        online = device.get("netStatus") == 2
    normalized["is_online"] = bool(online) if online is not None else False
    return normalized


def print_device_info(session, token, device, urls, api_mode, save_dir=None):
    """Print full info for one device: metadata, live state and datapoints."""
    device = _normalize_device(device)
    name = device.get("dev_alias")
    did = device.get("did")
    product_key = device.get("product_key", "")
    is_online = device.get("is_online", False)
    status_str = f"{GREEN}ONLINE{RESET}" if is_online else f"{RED}OFFLINE{RESET}"

    print("=" * 60)
    print(f"{BOLD}Name    :{RESET} {name}")
    print(f"{BOLD}ID      :{RESET} {did}")
    print(f"{BOLD}PK      :{RESET} {DIM}{product_key}{RESET}")
    print(f"{BOLD}Status  :{RESET} {status_str}")

    # Current state — dispatch on api_mode.
    if api_mode == "aep":
        latest = aep_get_device_latest(session, token, did, urls)
    else:
        latest = legacy_get_device_latest(session, token, did, urls)

    if latest:
        attrs = latest.get("attr", {}) or latest.get("attrs", {})
        updated = latest.get("updated_at", "?")
        print(f"\n  {CYAN}Current state{RESET} {DIM}(updated at: {updated}){RESET}")
        if attrs:
            for key, val in attrs.items():
                print(f"    {BOLD}{key}{RESET} = {GREEN}{val}{RESET}")
        else:
            print(f"    {DIM}(no data available){RESET}")

    # Datapoint schema.
    schema = None
    if product_key:
        print(f"\n  {CYAN}Supported Datapoints{RESET}")
        if api_mode == "aep":
            schema = aep_get_datapoints(session, token, product_key, urls)
        else:
            schema = legacy_get_datapoints(session, token, product_key, urls)
        if schema:
            entities = schema.get("entities", [])
            dps = []
            for entity in entities:
                dps.extend(entity.get("attrs", []))
            if dps:
                for dp in dps:
                    print(describe_datapoint(dp))
            else:
                warn("Unexpected structure - raw dump:")
                print(json.dumps(schema, indent=4, ensure_ascii=False))
        else:
            print(f"    {DIM}(datapoints not accessible for this product){RESET}")

    if save_dir is not None and schema is not None:
        save_datapoints(device, schema, save_dir)

    print("-" * 60)


def get_gizwits_devices(session, token, urls, api_mode, save_dir=None):
    """Main entry: list devices then print each one."""
    try:
        if api_mode == "aep":
            devices = aep_get_devices(session, token, urls)
        else:
            devices = legacy_get_devices(session, token, urls)

        if not devices:
            print(f"{YELLOW}No devices found.{RESET}")
            return

        print(f"\n{BOLD}{len(devices)} device(s) found:{RESET}\n")
        for d in devices:
            print_device_info(session, token, d, urls, api_mode, save_dir=save_dir)

    except Exception as e:
        err(f"System error: {e}")


# ── Single-region explicit modes ─────────────────────────────────────────────


def login_single_region(session, region, username, password, lang="fr"):
    """Try AEP then legacy on a single explicit region.

    Returns (urls, api_mode, token) or (None, None, None).
    """
    srv = GIZWITS_SERVERS[region]
    urls = build_urls(srv)
    label = srv["label"]

    step(f"AEP login on {label} ({region})...")
    jwt, error = aep_login(session, username, password, urls, lang=lang)
    if jwt:
        ok(f"AEP authenticated on {label}.")
        return urls, "aep", jwt
    warn(f"AEP failed: {error}")

    step(f"Falling back to legacy Open API on {label}...")
    phone_id = str(uuid.uuid4()).upper()
    legacy_provision(session, phone_id, urls)
    token, error = legacy_login(session, username, password, urls)
    if token:
        ok(f"Legacy authenticated on {label}.")
        return urls, "legacy", token
    err(f"Legacy failed: {error}")
    return None, None, None


if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    default_output = os.path.join(script_dir, "devices_datapoints")

    # Build server choices list for help text
    server_choices = ["auto"] + list(GIZWITS_SERVERS.keys()) + ["sim"]
    server_help_lines = [
        "auto   - try all servers automatically (default)",
    ]
    for key, srv in GIZWITS_SERVERS.items():
        server_help_lines.append(
            f"{key:<6s} - {srv['label']}  (AEP: {srv['aep_base']})"
        )
    server_help_lines.append("sim    - local simulator (legacy Open API shape)")

    parser = argparse.ArgumentParser(
        description="Gizwits Device Explorer -- Aqua Medic (AEP + Legacy)",
        epilog=(
            "Server regions:\n"
            + "\n".join(f"  {line}" for line in server_help_lines)
            + "\n\n"
            "Examples:\n"
            "  python aquamedic.py user@mail.com password                # auto-detect\n"
            "  python aquamedic.py user@mail.com password --server eu    # force Europe\n"
            "  python aquamedic.py user@mail.com password --server us    # force USA/Asia\n"
            "  python aquamedic.py user@mail.com password --server cn    # force China\n"
            "  python aquamedic.py user@mail.com password --server sim   # local simulator\n"
            "  python aquamedic.py user@mail.com password --sim --sim-url http://192.168.100.10:8080\n"
            "  python aquamedic.py user@mail.com password --save\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("username", help="Gizwits / Aqua Medic email")
    parser.add_argument(
        "password",
        nargs="?",
        default=None,
        help="Password (prompted securely if omitted — recommended when password contains special chars)",
    )

    # Server selection
    server_group = parser.add_argument_group("server")
    server_group.add_argument(
        "--server",
        choices=server_choices,
        default="auto",
        metavar="REGION",
        help=(
            "Gizwits server region: " + ", ".join(server_choices) + " (default: auto)"
        ),
    )
    server_group.add_argument(
        "--lang",
        default="fr",
        metavar="LANG",
        help="Language sent to AEP login (default: fr)",
    )

    # Simulator options
    sim_group = parser.add_argument_group("simulator")
    sim_group.add_argument(
        "--sim",
        action="store_true",
        help="Shorthand for --server sim",
    )
    sim_group.add_argument(
        "--sim-url",
        default="http://localhost:8080",
        metavar="URL",
        help="Base URL of the simulator (default: http://localhost:8080)",
    )

    # Save options
    save_group = parser.add_argument_group("save")
    save_group.add_argument(
        "--save",
        action="store_true",
        help=f"Save JSON datapoints in {default_output}/",
    )
    save_group.add_argument(
        "--output-dir",
        default=default_output,
        metavar="DIR",
        help=f"Output folder for --save (default: {default_output})",
    )

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    args = parser.parse_args()

    # Resolve password: prompt securely if not provided on the command line.
    # This avoids shell interpretation of special characters (!, $, &, etc.)
    # that would corrupt the password before Python even receives it.
    password = args.password or getpass.getpass(f"Password for {args.username}: ")

    # --sim flag is a shorthand for --server sim
    server = "sim" if args.sim else args.server

    save_dir = args.output_dir if args.save else None

    session = requests.Session()

    # ── Simulator mode (legacy Open API shape) ────────────────────────────────
    if server == "sim":
        base = args.sim_url.rstrip("/")
        api_base = base if base.endswith("/app") else f"{base}/app"
        urls = build_sim_urls(api_base)
        print(f"\n{YELLOW}[SIM] Simulator mode -> {api_base}{RESET}\n")
        phone_id = str(uuid.uuid4()).upper()
        legacy_provision(session, phone_id, urls)
        token, error = legacy_login(session, args.username, password, urls)
        if not token:
            err(f"Simulator login failed: {error}")
            sys.exit(1)
        get_gizwits_devices(session, token, urls, "legacy", save_dir=save_dir)

    # ── Auto-detect mode ──────────────────────────────────────────────────────
    elif server == "auto":
        region, urls, api_mode, token = auto_detect_server(
            session, args.username, password, lang=args.lang
        )
        if region is None:
            err("Auto-detection failed: could not login on any server.")
            err("Check your credentials or specify --server manually.")
            sys.exit(1)

        print(
            f"\n{GREEN}🌍 Using server: {BOLD}"
            f"{GIZWITS_SERVERS[region]['label']} ({region}, {api_mode}){RESET}\n"
        )
        get_gizwits_devices(session, token, urls, api_mode, save_dir=save_dir)

    # ── Explicit region ───────────────────────────────────────────────────────
    else:
        srv = GIZWITS_SERVERS[server]
        print(f"\n{CYAN}🌍 Server: {BOLD}{srv['label']} ({server}){RESET}\n")
        urls, api_mode, token = login_single_region(
            session, server, args.username, password, lang=args.lang
        )
        # login_single_region returns (None, None, None) on failure: narrow
        # api_mode too, it is used right below.
        if urls is None or api_mode is None:
            err("Login failed on both AEP and legacy for this region.")
            sys.exit(1)
        print(f"{GREEN}Using {api_mode.upper()} API on {srv['label']}.{RESET}\n")
        get_gizwits_devices(session, token, urls, api_mode, save_dir=save_dir)
