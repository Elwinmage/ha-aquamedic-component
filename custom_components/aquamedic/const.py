"""Constants for the Aquamedic integration."""

from __future__ import annotations

import logging
from datetime import timedelta

_LOGGER = logging.getLogger(__package__)

# ── Integration identity ──────────────────────────────────────────────────────
DOMAIN = "aquamedic"

# ── Gizwits App credentials (Aqua Medic official mobile app) ──────────────────
# Android app key — used for AEP + Gateway (primary API path).
GIZWITS_APP_KEY = "b45f1f4f31f546378fcfaed7775c4d12"
# iOS app id — legacy Open API fallback only.
GIZWITS_LEGACY_APP_ID = "07452c4f036a4be3acedf8dbeef38320"
# Backward-compatible alias kept so older tests / external references still work.
GIZWITS_APP_ID = GIZWITS_APP_KEY

GIZWITS_GATEWAY_API_KEY = "abb2243e83d341a3b75058134c236ab1"
GIZWITS_USER_AGENT = "gizwitssuperapprn/154300000 CFNetwork/3826.500.131 Darwin/24.5.0"

# ── Config entry keys ─────────────────────────────────────────────────────────
CONF_REGION = "region"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_SIM_HOST = "sim_host"  # only stored when region == "sim"

# Token / API state persisted across HA restarts (allows session restore).
CONF_ACCESS_TOKEN = "access_token"
CONF_REFRESH_TOKEN = "refresh_token"
CONF_TOKEN_EXPIRED_AT = "token_expired_at"
CONF_TOKEN_CREATED_AT = "token_created_at"
CONF_API_MODE = "api_mode"
CONF_DEVICE_LIST_API = "device_list_api"

# AEP device-list variants (auto-detected per account after first login).
DEVICE_LIST_SMART_HOME = "smart_home"  # migrated / current official app accounts
DEVICE_LIST_BINDINGS = "bindings"  # legacy AEP /app/bindings accounts

# ── Simulator defaults ────────────────────────────────────────────────────────
SIM_DEFAULT_HOST = "http://localhost:8080"

# ── Update interval ───────────────────────────────────────────────────────────
DEFAULT_SCAN_INTERVAL = 30  # seconds
MIN_SCAN_INTERVAL = 5
MAX_SCAN_INTERVAL = 300
UPDATE_INTERVAL = timedelta(seconds=DEFAULT_SCAN_INTERVAL)

# ── Gizwits regions (labels for config flow) ─────────────────────────────────
GIZWITS_REGIONS: dict[str, str] = {
    "eu": "Europe  (euaepapp + euapi.gizwitsapi.com)",
    "us": "USA / Asia  (usaepapp + usapi.gizwitsapi.com)",
    "cn": "China  (aep-app + api.gizwitsapi.com)",
    "sim": "Simulator  (local server)",
}

# ── Regional cloud endpoints (AEP + Gateway + legacy Open API) ────────────────
GIZWITS_REGION_ENDPOINTS: dict[str, dict[str, str]] = {
    "eu": {
        "aep_base": "https://euaepapp.gizwits.com",
        "gateway_base": "https://euapi.gizwitsapi.com",
        "open_api_base": "https://euapi.gizwits.com",
    },
    "us": {
        "aep_base": "https://usaepapp.gizwits.com",
        "gateway_base": "https://usapi.gizwitsapi.com",
        "open_api_base": "https://usapi.gizwits.com",
    },
    "cn": {
        "aep_base": "https://aep-app.gizwits.com",
        "gateway_base": "https://api.gizwitsapi.com",
        "open_api_base": "https://api.gizwits.com",
    },
}

# ── AEP path suffixes (same on every regional AEP host) ──────────────────────
AEP_PATH_LOGIN_PWD = "/app/smart_home/login/pwd"
AEP_PATH_REFRESH_TOKEN = "/app/user/refresh_token"
AEP_PATH_BINDINGS = "/app/bindings"
AEP_PATH_USER_DEVICES = "/app/smartHome/v2/users/devices"
AEP_PATH_DEVDATA = "/app/devdata/{device_id}/latest"
AEP_PATH_CONTROL = "/app/control/{device_id}"
AEP_PATH_DATAPOINT = "/app/datapoint"

# ── Gateway path suffixes (same on every regional Gateway host) ───────────────
GATEWAY_PATH_DEVICE_CONTROL = "/v2/devices-controller/devices/{device_id}"
GATEWAY_PATH_DEVICE_QUERY = "/v1/devices-manager/devices/{device_id}/query"

# ── Legacy Open API URLs (fallback for older / non-migrated accounts) ─────────
# Note: "sim" URLs are built at runtime from CONF_SIM_HOST (see client.py).
GIZWITS_API_URLS: dict[str, dict[str, str]] = {
    "sim": {
        "LOGIN": "http://localhost:8080/app/login",
        "PROVISION": "http://localhost:8080/app/provision",
        "BINDINGS": "http://localhost:8080/app/bindings",
        "DEVDATA": "http://localhost:8080/app/devdata/{device_id}/latest",
        "CONTROL": "http://localhost:8080/app/control/{device_id}",
        "DATAPOINT": "http://localhost:8080/app/datapoint",
    },
    "eu": {
        "LOGIN": "https://euapi.gizwits.com/app/login",
        "PROVISION": "https://euapi.gizwits.com/app/provision",
        "BINDINGS": "https://euapi.gizwits.com/app/bindings",
        "DEVDATA": "https://euapi.gizwits.com/app/devdata/{device_id}/latest",
        "CONTROL": "https://euapi.gizwits.com/app/control/{device_id}",
        "DATAPOINT": "https://euapi.gizwits.com/app/datapoint",
    },
    "us": {
        "LOGIN": "https://usapi.gizwits.com/app/login",
        "PROVISION": "https://usapi.gizwits.com/app/provision",
        "BINDINGS": "https://usapi.gizwits.com/app/bindings",
        "DEVDATA": "https://usapi.gizwits.com/app/devdata/{device_id}/latest",
        "CONTROL": "https://usapi.gizwits.com/app/control/{device_id}",
        "DATAPOINT": "https://usapi.gizwits.com/app/datapoint",
    },
    "cn": {
        "LOGIN": "https://api.gizwits.com/app/login",
        "PROVISION": "https://api.gizwits.com/app/provision",
        "BINDINGS": "https://api.gizwits.com/app/bindings",
        "DEVDATA": "https://api.gizwits.com/app/devdata/{device_id}/latest",
        "CONTROL": "https://api.gizwits.com/app/control/{device_id}",
        "DATAPOINT": "https://api.gizwits.com/app/datapoint",
    },
}

# Backward-compatible alias (used in legacy code paths).
LEGACY_API_URLS = GIZWITS_API_URLS

# ── Home Assistant language → Gizwits region ─────────────────────────────────
LANGUAGE_TO_REGION: dict[str, str] = {
    "fr": "eu",
    "de": "eu",
    "es": "eu",
    "it": "eu",
    "nl": "eu",
    "pl": "eu",
    "pt": "eu",
    "ru": "eu",
    "sv": "eu",
    "da": "eu",
    "fi": "eu",
    "nb": "eu",
    "cs": "eu",
    "sk": "eu",
    "hu": "eu",
    "ro": "eu",
    "bg": "eu",
    "hr": "eu",
    "sl": "eu",
    "et": "eu",
    "lv": "eu",
    "lt": "eu",
    "uk": "eu",
    "el": "eu",
    "en": "eu",
    "zh": "cn",
    "zh-hans": "cn",
    "zh-hant": "cn",
    "ja": "us",
    "ko": "us",
}

DEFAULT_REGION = "eu"

# ── Known product keys ────────────────────────────────────────────────────────
# SmartDrift / EcoDrift x.1 / x.3 series (confirmed via datapoint discovery)
SMARTDRIFT_PRODUCT_KEY = "63632f4902094055ab3fd994c0d612fa"

# DC Runner series — return pump AND skimmer variants share the same firmware.
# Confirmed via two independent real captures with byte-identical schemas:
#   - scripts/devices_datapoints/DC_RUNNER_00276aa006684c05805c297f60058c3d.json
#     (dev_alias "Abschäumer" — a DC Skimmer)
#   - scripts/devices_datapoints/AQD_032A44_00276aa006684c05805c297f60058c3d.json
#     (dev_alias "AQD_032A44" — a DC Runner return pump)
# Schema exposes motor speed, feeding / timer / auto modes, 48-slot scheduler
# and 7 fault flags. Model shown in HA is "DC Runner" for both variants — the
# actual pump role (skimmer vs return) is not readable from the API.
DC_RUNNER_SERIES_PRODUCT_KEY = "00276aa006684c05805c297f60058c3d"

# Backward-compatible alias — the original name incorrectly implied this key
# was skimmer-only. Kept so external references (older tests, community
# blueprints) keep working without changes.
DC_SKIMMER_PRODUCT_KEY = DC_RUNNER_SERIES_PRODUCT_KEY

# Speculative simpler DC Runner variant — the schema was authored before any
# real capture existed and has never been observed on a device in the wild.
# Kept in place because a few accounts may still advertise it and we want them
# to land on a valid code path rather than falling through the setup.
DC_RUNNER_PRODUCT_KEY = "8879684725d14066922374e50889f893"
