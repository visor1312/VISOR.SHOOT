"""Bearbeitungs-Styles fuer die HOOKCUT-All-in-One-Pipeline.

Ein Style ist ein Stapel FreeCut-GPU-Effekte (gpu-effect-IDs aus
editor/src/infrastructure/gpu-effects/), der beim Hintergrund-Rendern auf den
Video-Clip gelegt wird. So bekommt der Nutzer per Knopfdruck verschiedene
Looks, ohne je den Editor zu sehen.

Bewusst konservativer Start: nur Effekte mit VERIFIZIERTER Parameter-Form
(gpu-contrast/saturation/vibrance/exposure - key jeweils wie im Shader).
Reichere Looks (VHS, CRT, Glitch, Grain, Scanlines) kommen dazu, sobald der
headless-Render-Weg auf einem echten Rechner bestaetigt ist - dann ziehe ich
deren exakte Parameter-Keys nach, statt sie hier zu raten.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Style:
    key: str
    name: str
    description: str
    # Liste von (gpu_effect_type, params) - wird pro Clip zu ItemEffect[].
    effects: list[tuple[str, dict[str, float]]]


STYLES: dict[str, Style] = {
    "clean": Style(
        key="clean",
        name="Clean",
        description="Natuerlicher Look, nur dezent aufgehuebscht.",
        effects=[
            ("gpu-contrast", {"amount": 1.08}),
            ("gpu-saturation", {"amount": 1.08}),
        ],
    ),
    "vibrant": Style(
        key="vibrant",
        name="Vibrant",
        description="Kraeftige, poppige Farben fuer Social Media.",
        effects=[
            ("gpu-contrast", {"amount": 1.15}),
            ("gpu-saturation", {"amount": 1.25}),
            ("gpu-vibrance", {"amount": 0.3}),
        ],
    ),
    "cinematic": Style(
        key="cinematic",
        name="Cinematic",
        description="Kontrastreich, leicht entsaettigt - filmischer Look.",
        effects=[
            ("gpu-contrast", {"amount": 1.2}),
            ("gpu-saturation", {"amount": 0.9}),
            ("gpu-exposure", {"exposure": -0.1, "offset": 0.0, "gamma": 1.05}),
        ],
    ),
    "warm": Style(
        key="warm",
        name="Warm",
        description="Warmer, sonniger Grundton.",
        effects=[
            ("gpu-exposure", {"exposure": 0.1, "offset": 0.02, "gamma": 1.0}),
            ("gpu-saturation", {"amount": 1.15}),
            ("gpu-vibrance", {"amount": 0.2}),
        ],
    ),
}

DEFAULT_STYLE = "clean"


def get_style(key: str) -> Style:
    return STYLES.get(key, STYLES[DEFAULT_STYLE])


def style_catalog() -> list[dict]:
    return [
        {"key": s.key, "name": s.name, "description": s.description}
        for s in STYLES.values()
    ]
