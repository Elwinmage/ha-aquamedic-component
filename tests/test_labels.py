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
