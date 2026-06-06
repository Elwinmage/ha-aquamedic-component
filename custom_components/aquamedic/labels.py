"""Display labels for SmartDrift cloud values (bundled i18n data)."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

_DATA_FILE = Path(__file__).with_name("data") / "smartdrift_i18n.json"

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
AUTO_MODE_RAW_MAP: dict[str, str] = {
    **MODE_RAW_MAP,
    "停机": "stop",
    "喂食": "feeding",
}

_ATTR_ENUM_MAP: dict[str, dict[str, str]] = {
    "Mode": MODE_RAW_MAP,
    "Linkage": LINKAGE_RAW_MAP,
    "AutoMode": AUTO_MODE_RAW_MAP,
}

# Home Assistant entity translation_key → Gizwits attr / enum map
HA_ENTITY_ATTRS: dict[tuple[str, str], str] = {
    ("switch", "power"): "SwitchON",
    ("switch", "pulse_tide"): "PulseTide",
    ("switch", "feed_switch"): "FeedSwitch",
    ("switch", "timer_on"): "TimerON",
    ("switch", "control_0_10v"): "Control0_10V",
    ("select", "mode"): "Mode",
    ("select", "linkage"): "Linkage",
    ("number", "flow"): "Flow",
    ("number", "frequency"): "Frequency",
    ("number", "feed_time"): "FeedTime",
}

HA_SELECT_OPTION_MAPS: dict[str, dict[str, str]] = {
    "mode": MODE_RAW_MAP,
    "linkage": LINKAGE_RAW_MAP,
}

# Overrides where app UI strings differ from HA entity naming conventions.
HA_ENTITY_NAME_OVERRIDES: dict[tuple[str, str], dict[str, str]] = {
    ("switch", "power"): {"en": "Power", "de": "Ein/Aus"},
    ("select", "mode"): {"en": "Wave mode", "de": "Wellenmodus"},
    ("select", "linkage"): {"en": "Linkage", "de": "Verknüpfung"},
    ("switch", "control_0_10v"): {"en": "0-10V control mode", "de": "0–10-V-Steuerung"},
}

HA_MANUAL_ENTITY_NAMES: dict[tuple[str, str], dict[str, str]] = {
    ("button", "refresh"): {"en": "Refresh", "de": "Aktualisieren"},
    ("binary_sensor", "fault_overcurrent"): {
        "en": "Overcurrent fault",
        "de": "Überstrom-Fehler",
    },
    ("binary_sensor", "fault_overvoltage"): {
        "en": "Overvoltage fault",
        "de": "Überspannungs-Fehler",
    },
    ("binary_sensor", "fault_overtemp"): {
        "en": "Overtemperature fault",
        "de": "Übertemperatur-Fehler",
    },
    ("binary_sensor", "fault_undervoltage"): {
        "en": "Undervoltage fault",
        "de": "Unterspannungs-Fehler",
    },
    ("binary_sensor", "fault_lockedrotor"): {
        "en": "Locked rotor fault",
        "de": "Rotor blockiert",
    },
    ("binary_sensor", "fault_no_liveload"): {
        "en": "No load fault",
        "de": "Keine Last",
    },
    ("binary_sensor", "fault_uart"): {
        "en": "UART communication fault",
        "de": "UART-Kommunikationsfehler",
    },
}


def i18n_label(entry: dict[str, str] | None, lang: str, *, fallback: str = "") -> str:
    """Pick a localized string from a bundled i18n row."""
    if not entry:
        return fallback
    code = _normalize_lang(lang)
    return entry.get(code) or entry.get("en") or fallback


def ha_select_state_label(option_key: str, select_key: str, lang: str) -> str | None:
    """Localized label for a select option (e.g. classic_wave)."""
    raw_map = HA_SELECT_OPTION_MAPS.get(select_key, {})
    for raw, key in raw_map.items():
        if key == option_key:
            return translate_cloud_enum(raw, lang)
    return None


def build_ha_entity_translations(lang: str) -> dict:
    """Build the ``entity`` section for HA translation JSON from bundled i18n."""
    data = _load_i18n()
    attrs = data.get("attrs", {})
    entity: dict = {
        "button": {},
        "switch": {},
        "select": {},
        "number": {},
        "binary_sensor": {},
    }

    for (platform, key), attr in HA_ENTITY_ATTRS.items():
        overrides = HA_ENTITY_NAME_OVERRIDES.get((platform, key), {})
        name = overrides.get(_normalize_lang(lang)) or overrides.get("en")
        if not name:
            name = i18n_label(
                attrs.get(attr), lang, fallback=key.replace("_", " ").title()
            )
        block: dict = {"name": name}
        if platform == "select":
            raw_map = HA_SELECT_OPTION_MAPS.get(key, {})
            states = {}
            for raw, option_key in raw_map.items():
                label = translate_cloud_enum(raw, lang)
                if label:
                    states[option_key] = label
            if states:
                block["state"] = states
        entity[platform][key] = block

    for (platform, key), names in HA_MANUAL_ENTITY_NAMES.items():
        label = names.get(_normalize_lang(lang)) or names.get("en", key)
        entity[platform][key] = {"name": label}

    return entity


_BOOL_ATTRS = frozenset(
    {"SwitchON", "FeedSwitch", "PulseTide", "TimerON", "Control0_10V"}
)


@lru_cache(maxsize=1)
def _load_i18n() -> dict:
    with _DATA_FILE.open(encoding="utf-8") as handle:
        return json.load(handle)


def _normalize_lang(lang: str) -> str:
    return (lang or "en").split("-")[0].lower()


def translate_cloud_enum(raw: str, lang: str = "en") -> str | None:
    """Return a localized label for a Chinese cloud enum value, if known."""
    if not isinstance(raw, str):
        return None
    entry = _load_i18n().get("enum_values", {}).get(raw)
    if not entry:
        return None
    code = _normalize_lang(lang)
    return entry.get(code) or entry.get("en")


def translate_attr_name(attr: str, lang: str = "en") -> str:
    """Return a localized attribute label (falls back to the raw attr name)."""
    entry = _load_i18n().get("attrs", {}).get(attr)
    if not entry:
        return attr
    code = _normalize_lang(lang)
    return entry.get(code) or entry.get("en") or attr


def translate_attr_value(attr: str, value: Any, lang: str = "en") -> str:
    """Format a device attribute value for display."""
    if isinstance(value, bool):
        return _bool_label(value, lang)
    if attr in _BOOL_ATTRS and value in (0, 1, "0", "1"):
        return _bool_label(bool(int(value)), lang)
    if isinstance(value, (int, float)) and attr not in _ATTR_ENUM_MAP:
        if isinstance(value, float) and value.is_integer():
            return str(int(value))
        return str(value)
    if isinstance(value, str):
        mapped = translate_cloud_enum(value, lang)
        if mapped:
            return mapped
        raw_map = _ATTR_ENUM_MAP.get(attr, {})
        option_key = raw_map.get(value)
        if option_key:
            return _option_label(attr, option_key, lang) or value
    if isinstance(value, (int, float)):
        raw_map = _ATTR_ENUM_MAP.get(attr, {})
        options = list(raw_map.values())
        try:
            option_key = options[int(value)]
        except (IndexError, ValueError, TypeError):
            return str(value)
        return _option_label(attr, option_key, lang) or str(value)
    return str(value)


def _bool_label(value: bool, lang: str) -> str:
    code = _normalize_lang(lang)
    if code == "de":
        return "Ein" if value else "Aus"
    return "On" if value else "Off"


def _option_label(attr: str, option_key: str, lang: str) -> str | None:
    """Map internal option keys to localized labels via reverse raw lookup."""
    raw_map = _ATTR_ENUM_MAP.get(attr, {})
    for raw, key in raw_map.items():
        if key == option_key:
            return translate_cloud_enum(raw, lang)
    return None
