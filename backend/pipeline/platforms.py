"""Multi-Plattform-Export-Presets fuer den Reel-Assistenten.

Ein Reel, mehrere Zielformate: derselbe Sync/Hook/Style/Beat-Puls wird pro
Plattform in eigener Aufloesung gerendert. Der Cover-Transform in
freecut_workspace.py fuellt jedes Format automatisch formatfuellend
(Ueberstand wird beschnitten), Untertitel-Groesse/-Abstand skalieren mit der
Bildhoehe - deshalb braucht ein neues Format hier NUR Breite x Hoehe.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Platform:
    key: str
    name: str
    description: str
    width: int
    height: int


PLATFORMS: dict[str, Platform] = {
    "reel": Platform(
        key="reel",
        name="TikTok / Reels / Shorts",
        description="9:16 Hochformat - der Standard fuer Kurzvideos.",
        width=1080, height=1920,
    ),
    "feed": Platform(
        key="feed",
        name="Insta-Feed",
        description="4:5 Portrait - nutzt im Insta-Feed die volle Hoehe.",
        width=1080, height=1350,
    ),
    "square": Platform(
        key="square",
        name="Quadratisch",
        description="1:1 - Feed-Posts, funktioniert ueberall.",
        width=1080, height=1080,
    ),
    "wide": Platform(
        key="wide",
        name="YouTube",
        description="16:9 Querformat - normale YouTube-Videos.",
        width=1920, height=1080,
    ),
}

DEFAULT_PLATFORM = "reel"


def get_platform(key: str) -> Platform:
    return PLATFORMS.get(key, PLATFORMS[DEFAULT_PLATFORM])


def parse_platform_keys(raw: str) -> list[Platform]:
    """Kommagetrennte Keys -> Plattform-Liste (dedupliziert, Reihenfolge
    erhalten, unbekannte Keys ignoriert). Leer/nur Unbekanntes -> Standard."""
    seen: list[Platform] = []
    for part in raw.split(","):
        key = part.strip()
        p = PLATFORMS.get(key)
        if p and p not in seen:
            seen.append(p)
    return seen or [PLATFORMS[DEFAULT_PLATFORM]]


def platform_catalog() -> list[dict]:
    return [
        {"key": p.key, "name": p.name, "description": p.description,
         "width": p.width, "height": p.height}
        for p in PLATFORMS.values()
    ]
