"""Tests for bundled SmartDrift display labels."""

from custom_components.aquamedic.labels import (
    build_ha_entity_translations,
    translate_attr_name,
    translate_attr_value,
    translate_cloud_enum,
)


def test_translate_cloud_enum_de():
    assert translate_cloud_enum("恒流造浪", "de") == "Konstante Strömung"
    assert translate_cloud_enum("独立", "de") == "Unabhängig"


def test_translate_cloud_enum_en():
    assert translate_cloud_enum("正弦造浪", "en") == "Sine Wave Mode"


def test_translate_attr_value_mode():
    assert translate_attr_value("Mode", "经典造浪", "de") == "Klassische Welle"


def test_translate_attr_name_de():
    assert translate_attr_name("Flow", "de") == "Durchfluss"
    assert translate_attr_name("UnknownAttr", "de") == "UnknownAttr"


def test_translate_bool_switch():
    assert translate_attr_value("SwitchON", True, "de") == "Ein"
    assert translate_attr_value("SwitchON", False, "en") == "Off"
    assert translate_attr_value("SwitchON", 1, "de") == "Ein"
    assert translate_attr_value("SwitchON", 0, "en") == "Off"


def test_build_ha_entity_translations_de():
    entity = build_ha_entity_translations("de")
    assert entity["select"]["mode"]["state"]["constant_flow"] == "Konstante Strömung"
    assert entity["select"]["linkage"]["state"]["independent"] == "Unabhängig"
    assert entity["number"]["flow"]["name"] == "Durchfluss"


# ── translate_cloud_enum edge cases ───────────────────────────────────────────


def test_translate_cloud_enum_returns_none_for_non_string():
    """L171: non-string raw value → None."""
    assert translate_cloud_enum(123, "de") is None
    assert translate_cloud_enum(None, "en") is None


def test_translate_cloud_enum_returns_none_for_unknown_value():
    """L174: raw string not in i18n table → None."""
    assert translate_cloud_enum("UNKNOWN_CLOUD_VALUE", "de") is None


# ── ha_select_state_label ─────────────────────────────────────────────────────


def test_ha_select_state_label_known_option():
    """L108-112: option_key found in map → localized label."""
    from custom_components.aquamedic.labels import ha_select_state_label

    # "classic_wave" is the key for "经典造浪" in mode map
    result = ha_select_state_label("classic_wave", "mode", "de")
    assert result == "Klassische Welle"


def test_ha_select_state_label_unknown_option():
    """L112 (return None): option_key not in map."""
    from custom_components.aquamedic.labels import ha_select_state_label

    result = ha_select_state_label("nonexistent_key", "mode", "de")
    assert result is None


def test_ha_select_state_label_unknown_select_key():
    """L108: select_key not in HA_SELECT_OPTION_MAPS → empty map → None."""
    from custom_components.aquamedic.labels import ha_select_state_label

    result = ha_select_state_label("classic_wave", "no_such_select", "de")
    assert result is None


# ── translate_attr_value float / enum paths ───────────────────────────────────


def test_translate_attr_value_float_is_integer():
    """L195-196: float with .is_integer() → str(int(value))."""
    result = translate_attr_value("Flow", 75.0, "en")
    assert result == "75"


def test_translate_attr_value_float_not_integer():
    """L197: float without .is_integer() → str(float)."""
    result = translate_attr_value("Flow", 75.5, "en")
    assert result == "75.5"


def test_translate_attr_value_string_in_enum_map():
    """L202-205: string value found in _ATTR_ENUM_MAP → localized label via _option_label."""
    # "经典造浪" is a raw Mode value; Mode is in _ATTR_ENUM_MAP
    result = translate_attr_value("Mode", "经典造浪", "de")
    assert result == "Klassische Welle"


def test_translate_attr_value_int_enum_index():
    """L207-213: integer used as index into _ATTR_ENUM_MAP options list."""
    # Mode index 0 → first option in MODE_RAW_MAP
    result = translate_attr_value("Mode", 0, "de")
    # Should return a non-empty string (the first mode label in German)
    assert isinstance(result, str) and len(result) > 0


def test_translate_attr_value_int_enum_out_of_range():
    """L211-212: IndexError on out-of-range int → str(value)."""
    result = translate_attr_value("Mode", 9999, "de")
    assert result == "9999"


# ── _option_label (L226-230) via translate_attr_value ────────────────────────


def test_option_label_returns_none_for_unknown_key():
    """L230 (return None): option_key not in any raw_map entry."""
    from custom_components.aquamedic.labels import _option_label

    result = _option_label("Mode", "nonexistent_option_key", "de")
    assert result is None


# ── i18n_label fallback (L101) ────────────────────────────────────────────────


def test_i18n_label_returns_fallback_when_entry_none():
    """L101: entry is None → returns fallback string."""
    from custom_components.aquamedic.labels import i18n_label

    assert i18n_label(None, "de", fallback="default") == "default"


def test_i18n_label_returns_fallback_when_entry_empty():
    """L101: entry is {} (falsy dict) → returns fallback."""
    from custom_components.aquamedic.labels import i18n_label

    assert i18n_label({}, "de", fallback="fb") == "fb"


# ── translate_attr_value: string enum without cloud label (L202-205) ──────────


def test_translate_attr_value_string_in_enum_map_cloud_returns_none():
    """L202-205: string in _ATTR_ENUM_MAP but translate_cloud_enum → None."""
    from unittest.mock import patch

    import custom_components.aquamedic.labels as labels_mod

    # Patch translate_cloud_enum so it always returns None
    with patch.object(labels_mod, "translate_cloud_enum", return_value=None):
        # "经典造浪" is in MODE_RAW_MAP → option_key found → _option_label → None
        # → falls back to returning value itself
        result = translate_attr_value("Mode", "经典造浪", "de")
    assert result == "经典造浪"


# ── translate_attr_value: final str(value) fallback (L214) ───────────────────


def test_translate_attr_value_none_value_final_fallback():
    """L214: value is None (not bool/str/int/float) → str(value)."""
    result = translate_attr_value("Flow", None, "en")
    assert result == "None"
