"""Tests fuer die Multi-Plattform-Export-Presets."""
from __future__ import annotations

from backend.pipeline.platforms import (
    DEFAULT_PLATFORM,
    PLATFORMS,
    get_platform,
    parse_platform_keys,
    platform_catalog,
)


def test_catalog_has_reel_as_default():
    assert DEFAULT_PLATFORM == "reel"
    assert PLATFORMS["reel"].width == 1080 and PLATFORMS["reel"].height == 1920
    keys = {p["key"] for p in platform_catalog()}
    assert {"reel", "feed", "square", "wide"} <= keys
    for p in platform_catalog():
        assert p["name"] and p["description"]
        assert p["width"] > 0 and p["height"] > 0


def test_get_platform_falls_back_to_default():
    assert get_platform("nope").key == DEFAULT_PLATFORM
    assert get_platform("wide").key == "wide"


def test_parse_platform_keys():
    assert [p.key for p in parse_platform_keys("reel,square")] == ["reel", "square"]
    # dedupliziert, Reihenfolge erhalten, Leerzeichen tolerant
    assert [p.key for p in parse_platform_keys(" square , reel ,square")] == ["square", "reel"]
    # leer / nur Unbekanntes -> Standard
    assert [p.key for p in parse_platform_keys("")] == [DEFAULT_PLATFORM]
    assert [p.key for p in parse_platform_keys("bogus,unsinn")] == [DEFAULT_PLATFORM]
