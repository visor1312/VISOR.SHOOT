"""Bearbeitungs-Styles fuer die selfsign-All-in-One-Pipeline.

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
    # --- Intensive Looks (Parameter-Keys aus den GPU-Effekt-Defs verifiziert) ---
    "vhs": Style(
        key="vhs",
        name="VHS Retro",
        description="90er-Kassetten-Look: Farbbluten, Rauschen, Wellen.",
        effects=[
            ("gpu-vhs", {"bleed": 0.45, "waviness": 0.25, "noise": 0.25, "scanline": 0.35, "speed": 1}),
            ("gpu-saturation", {"amount": 1.1}),
            ("gpu-vignette", {"amount": 0.35, "size": 0.55, "softness": 0.6, "roundness": 1}),
        ],
    ),
    "crt": Style(
        key="crt",
        name="CRT TV",
        description="Alter Roehrenfernseher: Woelbung, Scanlines, Farbsaum.",
        effects=[
            ("gpu-crt", {"curvature": 0.25, "scanlines": 0.35, "vignette": 0.3, "chroma": 0.4}),
            ("gpu-grain", {"amount": 0.08, "size": 1, "speed": 1}),
        ],
    ),
    "hype": Style(
        key="hype",
        name="Hype / Glitch",
        description="Aggressiver Digital-Look: Glitches, RGB-Split, Punch.",
        effects=[
            ("gpu-color-glitch", {"intensity": 0.35, "speed": 1.2}),
            ("gpu-block-glitch", {"coverage": 0.18, "intensity": 0.5, "blockSize": 36, "speed": 1.2}),
            ("gpu-rgb-split", {"amount": 0.006, "angle": 0}),
            ("gpu-contrast", {"amount": 1.18}),
            ("gpu-saturation", {"amount": 1.2}),
        ],
    ),
    "film": Style(
        key="film",
        name="Film Look",
        description="Kino-Korn, sanfte Vignette, gedeckte Farben.",
        effects=[
            ("gpu-grain", {"amount": 0.14, "size": 1.4, "speed": 1}),
            ("gpu-vignette", {"amount": 0.45, "size": 0.5, "softness": 0.65, "roundness": 1}),
            ("gpu-contrast", {"amount": 1.12}),
            ("gpu-saturation", {"amount": 0.88}),
            ("gpu-exposure", {"exposure": -0.05, "offset": 0.0, "gamma": 1.06}),
        ],
    ),
    "neon": Style(
        key="neon",
        name="Neon Glow",
        description="Leuchtende Highlights, satte Farben - Club-Vibe.",
        effects=[
            ("gpu-glow", {"amount": 1.4, "threshold": 0.55, "radius": 26, "softness": 0.6,
                          "rings": 4, "samplesPerRing": 16}),
            ("gpu-saturation", {"amount": 1.35}),
            ("gpu-contrast", {"amount": 1.12}),
            ("gpu-vignette", {"amount": 0.3, "size": 0.55, "softness": 0.6, "roundness": 1}),
        ],
    ),
    "noir": Style(
        key="noir",
        name="Schwarz-Weiss",
        description="Harter Kontrast, monochrom - zeitlos.",
        effects=[
            ("gpu-grayscale", {"amount": 1}),
            ("gpu-contrast", {"amount": 1.3}),
            ("gpu-grain", {"amount": 0.1, "size": 1.2, "speed": 1}),
            ("gpu-vignette", {"amount": 0.4, "size": 0.5, "softness": 0.6, "roundness": 1}),
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
