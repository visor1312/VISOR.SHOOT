"""Editing-Presets: benannte Kombinationen aus Color Grading, beat-synchronen
Effekten, Finish-Filtern und Schnitt-Rhythmus fuer das fertige Snippet-Video.

Ein Preset buendelt vier Dimensionen:
- color:        Farb-Look (COLOR_PRESETS aus effects_grading.py, eq-basiert)
- effects:      beat-synchrone Effekte (Zoom-Kick, Flash, Shake, RGB-Split)
- extra_filters: statische Finish-Filter (Vignette, Filmkorn, Schaerfe,
                 Weichzeichnung, curves-Looks) - laufen NACH den Effekten
- beat_stride:  Schnitt-Rhythmus - Effekt auf jedem Beat (1), jedem zweiten
                 (2) oder jedem vierten (4). Halbe/viertel Frequenz fuehlt
                 sich wie ruhigerer Schnitt an, jeder Beat wie schneller.

Die Preset-Liste ist die eine Quelle der Wahrheit fuer Backend UND Frontend
(GET /presets liefert sie ans React-UI).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from backend.pipeline.effects_grading import BeatEffectConfig, render_with_beat_effects


@dataclass(frozen=True)
class EditPreset:
    id: str
    label: str
    description: str  # eine Zeile, wird im UI unter dem Namen angezeigt
    color: str | None = None  # Key aus effects_grading.COLOR_PRESETS
    effects: BeatEffectConfig = field(default_factory=BeatEffectConfig)
    extra_filters: tuple[str, ...] = ()
    beat_stride: int = 1  # Effekt auf jedem n-ten Beat


# Wiederverwendete Finish-Filter (ffmpeg):
_VIGNETTE = "vignette=PI/4.5"
_GRAIN = "noise=alls=10:allf=t+u"          # lebendiges Filmkorn
_GRAIN_FINE = "noise=alls=6:allf=t"        # feines, ruhiges Korn
_SHARPEN = "unsharp=5:5:0.8:5:5:0.0"
_SOFT_BLUR = "gblur=sigma=1.1"
_VHS_BLUR = "gblur=sigma=0.7"
_VINTAGE_CURVES = "curves=preset=vintage"  # eingebauter Retro-Look von ffmpeg


PRESETS: dict[str, EditPreset] = {p.id: p for p in [
    EditPreset(
        id="clean",
        label="Pur",
        description="Nur sauberer Sync, natürliche Farben, keine Effekte.",
        color="natural",
    ),
    EditPreset(
        id="golden_hour",
        label="Golden Hour",
        description="Warmes, goldenes Grading mit weicher Vignette.",
        color="warm_gold",
        extra_filters=(_VIGNETTE,),
    ),
    EditPreset(
        id="urban_ice",
        label="Urban Ice",
        description="Kühler Street-Look, knackige Schärfe, Vignette.",
        color="cold_urban",
        extra_filters=(_SHARPEN, _VIGNETTE),
    ),
    EditPreset(
        id="noir",
        label="Noir",
        description="Hartes Schwarzweiß mit Filmkorn — maximaler Drama-Faktor.",
        color="high_contrast_mono",
        extra_filters=(_GRAIN_FINE, _VIGNETTE),
    ),
    EditPreset(
        id="beat_pulse",
        label="Beat Pulse",
        description="Zoom-Kick auf jedem Beat — pumpt im Takt deines Songs.",
        color="natural",
        effects=BeatEffectConfig(zoom=0.5),
    ),
    EditPreset(
        id="flash_bang",
        label="Flash",
        description="Heller Blitz auf jedem zweiten Beat, leicht erhöhter Kontrast.",
        color="punchy_trap",
        effects=BeatEffectConfig(flash=0.35),
        beat_stride=2,
    ),
    EditPreset(
        id="handheld",
        label="Shake",
        description="Kamera-Wackeln im Takt + warmes Grading — roher Live-Vibe.",
        color="warm_gold",
        effects=BeatEffectConfig(shake=0.6),
        beat_stride=2,
    ),
    EditPreset(
        id="glitch",
        label="Glitch",
        description="RGB-Split-Kicks auf jedem Beat, kühler Look, digitales Flackern.",
        color="cold_urban",
        effects=BeatEffectConfig(rgb_split=0.8),
        extra_filters=(_GRAIN_FINE,),
    ),
    EditPreset(
        id="vhs",
        label="VHS Retro",
        description="Ausgeblichene Farben, starkes Korn, leichte Unschärfe — 90s-Tape.",
        color="vhs_faded",
        extra_filters=(_VHS_BLUR, _GRAIN, _VIGNETTE),
    ),
    EditPreset(
        id="vintage",
        label="Vintage Film",
        description="Analoger Kino-Look (curves) mit Korn und Vignette.",
        extra_filters=(_VINTAGE_CURVES, _GRAIN_FINE, _VIGNETTE),
    ),
    EditPreset(
        id="dreamy",
        label="Dreamy",
        description="Weichgezeichnet, hell, satte Farben — verträumter Soft-Look.",
        color="dreamy_soft",
        extra_filters=(_SOFT_BLUR,),
    ),
    EditPreset(
        id="hard_trap",
        label="Hard Trap",
        description="Alles auf 11: Zoom + Flash + Glitch auf jedem Beat, harter Kontrast.",
        color="punchy_trap",
        effects=BeatEffectConfig(zoom=0.45, flash=0.3, rgb_split=0.6),
        extra_filters=(_VIGNETTE,),
    ),
]}


def preset_catalog() -> list[dict[str, str]]:
    """Kompakte Liste fuer das Frontend (GET /presets)."""
    return [
        {"id": p.id, "label": p.label, "description": p.description}
        for p in PRESETS.values()
    ]


def preset_is_noop(preset_id: str) -> bool:
    """True, wenn das Preset am Bild nichts veraendern wuerde ausser dem
    Standard-Grading - dann kann der teure Render-Schritt entfallen."""
    p = PRESETS[preset_id]
    e = p.effects
    return (
        p.color in (None, "natural")
        and not p.extra_filters
        and not any((e.zoom, e.flash, e.shake, e.rgb_split))
    )


def apply_preset(
    video_path: str | Path,
    beat_times: list[float],
    out_path: str | Path,
    preset_id: str,
    crf: int = 19,
) -> Path:
    """Rendert `video_path` mit dem gewaehlten Preset nach `out_path`.

    `beat_times` muessen im Zeitrahmen von `video_path` liegen (bei uns:
    per beat_detect auf der Audiospur des fertig gesyncten Videos erkannt).
    """
    if preset_id not in PRESETS:
        raise ValueError(f"Unbekanntes Preset: {preset_id}. Verfuegbar: {list(PRESETS)}")
    p = PRESETS[preset_id]
    strided_beats = beat_times[:: max(1, p.beat_stride)]
    return render_with_beat_effects(
        video_path,
        strided_beats,
        out_path,
        color_preset=p.color,
        effects=p.effects,
        extra_filters=list(p.extra_filters),
        crf=crf,
    )
