"""Tests for const.py."""

from custom_components.aquamedic.const import (
    CONF_PASSWORD,
    CONF_REGION,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_REGION,
    DOMAIN,
    GIZWITS_API_URLS,
    GIZWITS_APP_ID,
    GIZWITS_REGIONS,
    LANGUAGE_TO_REGION,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
    SMARTDRIFT_PRODUCT_KEY,
    UPDATE_INTERVAL,
)


def test_domain():
    assert DOMAIN == "aquamedic"


def test_app_id_format():
    assert len(GIZWITS_APP_ID) == 32
    assert GIZWITS_APP_ID == "07452c4f036a4be3acedf8dbeef38320"


def test_smartdrift_product_key():
    assert SMARTDRIFT_PRODUCT_KEY == "63632f4902094055ab3fd994c0d612fa"


def test_conf_keys():
    assert CONF_USERNAME      == "username"
    assert CONF_PASSWORD      == "password"
    assert CONF_REGION        == "region"
    assert CONF_SCAN_INTERVAL == "scan_interval"


def test_scan_interval_bounds():
    assert MIN_SCAN_INTERVAL == 5
    assert MAX_SCAN_INTERVAL == 300
    assert MIN_SCAN_INTERVAL <= DEFAULT_SCAN_INTERVAL <= MAX_SCAN_INTERVAL


def test_update_interval():
    from datetime import timedelta
    assert UPDATE_INTERVAL == timedelta(seconds=DEFAULT_SCAN_INTERVAL)


def test_regions_defined():
    assert set(GIZWITS_REGIONS.keys()) == {"eu", "us", "cn"}
    assert DEFAULT_REGION == "eu"


def test_api_urls_complete():
    required = {"LOGIN", "PROVISION", "BINDINGS", "DEVDATA", "CONTROL", "DATAPOINT"}
    for region, urls in GIZWITS_API_URLS.items():
        assert required <= set(urls.keys()), f"Region {region} missing keys"


def test_devdata_url_template():
    url = GIZWITS_API_URLS["eu"]["DEVDATA"]
    assert "{device_id}" in url


def test_language_to_region_eu():
    for lang in ["fr", "de", "es", "it", "nl", "pl", "en"]:
        assert LANGUAGE_TO_REGION[lang] == "eu"


def test_language_to_region_cn():
    assert LANGUAGE_TO_REGION["zh"] == "cn"


def test_language_to_region_us():
    assert LANGUAGE_TO_REGION["ja"] == "us"
