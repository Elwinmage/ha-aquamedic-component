"""Constants for the Aquamedic integration."""

from __future__ import annotations

import logging
from datetime import timedelta

_LOGGER = logging.getLogger(__package__)

# ── Integration identity ──────────────────────────────────────────────────────
DOMAIN = "aquamedic"

# ── Gizwits App ID (Aqua Medic official app) ─────────────────────────────────
GIZWITS_APP_ID = "07452c4f036a4be3acedf8dbeef38320"
GIZWITS_USER_AGENT = "gizwitssuperapprn/154300000 CFNetwork/3826.500.131 Darwin/24.5.0"

# ── Config entry keys ─────────────────────────────────────────────────────────
CONF_REGION = "region"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_SCAN_INTERVAL = "scan_interval"

# ── Update interval ───────────────────────────────────────────────────────────
DEFAULT_SCAN_INTERVAL = 30  # seconds
MIN_SCAN_INTERVAL = 5
MAX_SCAN_INTERVAL = 300
UPDATE_INTERVAL = timedelta(seconds=DEFAULT_SCAN_INTERVAL)

# ── Gizwits regions and their API endpoints ───────────────────────────────────
GIZWITS_REGIONS: dict[str, str] = {
    "eu": "Europe  (euapi.gizwits.com)",
    "us": "USA / Asia  (usapi.gizwits.com)",
    "cn": "China  (api.gizwits.com)",
}

GIZWITS_API_URLS: dict[str, dict[str, str]] = {
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
# SmartDrift x.1 / x.3 series (confirmed via datapoint discovery)
SMARTDRIFT_PRODUCT_KEY = "63632f4902094055ab3fd994c0d612fa"
