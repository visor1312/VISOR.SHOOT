"""Schritt 07 (Phase 3): Farbkorrektur-Presets und beat-synchrone Effekte
fuer Einzelclips.

Farbpresets nutzen ffmpeg's `eq`-Filter (statisch). Die Beat-Effekte (Zoom-
Pulse, Flash, Shake, RGB-Split-Kick) nutzen zeitvariable Filterausdruecke
(`eval=frame`), die auf den tatsaechlich erkannten Taktschlaegen (siehe
beat_detect.py) basieren - kein blosses Tempo-Sinus-Approximat, sondern echte
Treffer auf jeden erkannten Takt. Wie in Phase 2 werden die Beat-Zeitstempel
auf der bereits synchronisierten Output-Audiospur erkannt, liegen also schon
im Zeitrahmen des fertigen Videos.

RGB-Split-Kick ist ein Sonderfall: `rgbashift`s Parameter sind reine Integer
(keine Ausdruecke), daher wird er per `sendcmd`-Filter zu den Takt-Zeitpunkten
an-/ausgeschaltet.
"""
from __future__ import annotations

import argparse
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

COLOR_PRESETS: dict[str, dict[str, float]] = {
    "natural": {"contrast": 1.05, "saturation": 1.08, "brightness": 0.0, "gamma_r": 1.0, "gamma_b": 1.0},
    "warm_gold": {"contrast": 1.08, "saturation": 1.2, "brightness": 0.01, "gamma_r": 1.08, "gamma_b": 0.92},
    "cold_urban": {"contrast": 1.12, "saturation": 0.88, "brightness": -0.01, "gamma_r": 0.94, "gamma_b": 1.1},
    "high_contrast_mono": {"contrast": 1.35, "saturation": 0.0, "brightness": 0.0, "gamma_r": 1.0, "gamma_b": 1.0},
}


@dataclass
class BeatEffectConfig:
    zoom: Optional[float] = None       # Intensitaet 0..1 (Zoom-Pulse-Amplitude)
    flash: Optional[float] = None      # Intensitaet 0..1 (Helligkeits-Spitze)
    shake: Optional[float] = None      # Intensitaet 0..1 (Pixel-Wackeln)
    rgb_split: Optional[float] = None  # Intensitaet 0..1 (Kanal-Versatz in Pixeln, skaliert)


def _color_preset_filter(preset: str) -> str:
    if preset not in COLOR_PRESETS:
        raise ValueError(f"Unbekanntes Farbpreset: {preset}. Verfuegbar: {list(COLOR_PRESETS)}")
    p = COLOR_PRESETS[preset]
    return (
        f"eq=contrast={p['contrast']}:saturation={p['saturation']}:brightness={p['brightness']}:"
        f"gamma_r={p['gamma_r']}:gamma_b={p['gamma_b']}"
    )


def _beat_pulse_expr(beat_times: list[float], pulse_width: float = 0.12) -> str:
    """Summe dreieckfoermiger Impulse, je einer pro Taktschlag, Wert in [0,1]."""
    if not beat_times:
        return "0"
    terms = [f"max(0,1-abs(t-{b:.3f})/{pulse_width})" for b in beat_times]
    return "(" + "+".join(terms) + ")"


def apply_color_preset(video_path: str | Path, preset: str, out_path: str | Path, crf: int = 19) -> Path:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y", "-i", str(video_path),
        "-vf", _color_preset_filter(preset),
        "-c:v", "libx264", "-preset", "medium", "-crf", str(crf), "-pix_fmt", "yuv420p",
        "-c:a", "copy",
        "-movflags", "+faststart",
        str(out_path),
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True)
    return out_path


def _kick_lines(target: str, param: str, rest_value: str, kick_value: str, beat_times: list[float], kick_dur: float) -> list[str]:
    """Baut sendcmd-Zeilen, die einen Filterparameter zu jedem Taktschlag kurz
    auf `kick_value` setzen und danach auf `rest_value` zurueckspringen lassen.

    Noetig fuer Parameter, die (anders als z.B. eq/crop x/y) keine per-Frame-
    Ausdruecke mit `t` unterstuetzen, aber laut ffmpeg als Laufzeit-Parameter
    (per sendcmd aenderbar) markiert sind - z.B. crop w/h und rgbashift rh/bh.
    """
    lines = [f"0.0 {target} {param} {rest_value};"]
    for b in beat_times:
        lines.append(f"{b:.3f} {target} {param} {kick_value};")
        lines.append(f"{b + kick_dur:.3f} {target} {param} {rest_value};")
    return lines


def _write_sendcmd_script(lines: list[str], out_path: Path) -> Path:
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out_path


def _escape_ffmpeg_filter_path(path: str | Path) -> str:
    p = str(Path(path).resolve())
    return p.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")


def _probe_dimensions(video_path: str | Path) -> tuple[int, int]:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height", "-of", "csv=s=x:p=0", str(video_path)],
        check=True, capture_output=True, text=True,
    )
    width_str, height_str = result.stdout.strip().split("x")
    return int(width_str), int(height_str)


def render_with_beat_effects(
    video_path: str | Path,
    beat_times: list[float],
    out_path: str | Path,
    color_preset: Optional[str] = None,
    effects: Optional[BeatEffectConfig] = None,
    crf: int = 19,
) -> Path:
    """Wendet Farbpreset (optional) und beat-synchrone Effekte (optional) auf ein
    Einzelclip-Video an. `beat_times` muss bereits im Zeitrahmen dieses Videos
    liegen (siehe beat_detect.py)."""
    video_path = Path(video_path)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    effects = effects or BeatEffectConfig()

    filters: list[str] = []
    sendcmd_lines: list[str] = []

    if color_preset:
        filters.append(_color_preset_filter(color_preset))

    pulse = _beat_pulse_expr(beat_times) if beat_times else None
    kick_dur = 0.08

    if effects.zoom and beat_times:
        # crop w/h unterstuetzen (anders als x/y) keine Ausdruecke mit `t` -
        # daher per sendcmd zu jedem Takt kurz auf einen kleineren Ausschnitt
        # springen (= Zoom-Kick) und danach zurueck. Anschliessend fixe
        # scale-Zielgroesse, damit die Ausgabeaufloesung konstant bleibt.
        width, height = _probe_dimensions(video_path)
        zoomed_w = max(2, round(width / (1 + effects.zoom)) // 2 * 2)
        zoomed_h = max(2, round(height / (1 + effects.zoom)) // 2 * 2)
        sendcmd_lines += _kick_lines("zoomcrop", "w", str(width), str(zoomed_w), beat_times, kick_dur)
        sendcmd_lines += _kick_lines("zoomcrop", "h", str(height), str(zoomed_h), beat_times, kick_dur)
        filters.append(f"crop@zoomcrop=w={width}:h={height}")
        filters.append(f"scale={width}:{height}")

    if effects.flash and pulse:
        filters.append(f"eq=brightness='{effects.flash}*{pulse}':eval=frame")

    if effects.shake and pulse:
        # Feste, auf gerade Pixelzahlen gerundete Dimensionen statt
        # iw*margin/ih*margin-Ausdruecken - sonst koennen Rundungsfehler zu
        # ungeraden Aufloesungen fuehren, die yuv420p/libx264 ablehnen.
        width, height = _probe_dimensions(video_path)
        margin_w = max(2, round(width * 1.06) // 2 * 2)
        margin_h = max(2, round(height * 1.06) // 2 * 2)
        max_px = effects.shake * 18
        filters.append(f"scale={margin_w}:{margin_h}")
        filters.append(
            f"crop=w={width}:h={height}:"
            f"x='(in_w-out_w)/2+{max_px}*{pulse}*sin(2*PI*18*t)':"
            f"y='(in_h-out_h)/2+{max_px}*{pulse}*cos(2*PI*17*t)'"
        )

    if effects.rgb_split and beat_times:
        shift_px = max(1, round(effects.rgb_split * 8))
        sendcmd_lines += _kick_lines("rgbsplit", "rh", "0", str(shift_px), beat_times, kick_dur)
        sendcmd_lines += _kick_lines("rgbsplit", "bh", "0", str(-shift_px), beat_times, kick_dur)
        filters.append("rgbashift@rgbsplit")

    if sendcmd_lines:
        sendcmd_script = out_path.parent / f"{out_path.stem}_cmds.txt"
        _write_sendcmd_script(sendcmd_lines, sendcmd_script)
        escaped = _escape_ffmpeg_filter_path(sendcmd_script)
        filters.insert(0, f"sendcmd=f='{escaped}'")

    if not filters:
        filters.append("null")

    vf = ",".join(filters)
    cmd = [
        "ffmpeg", "-y", "-i", str(video_path),
        "-vf", vf,
        "-c:v", "libx264", "-preset", "medium", "-crf", str(crf), "-pix_fmt", "yuv420p",
        "-c:a", "copy",
        "-movflags", "+faststart",
        str(out_path),
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True)
    return out_path


def _main() -> None:
    parser = argparse.ArgumentParser(description="Farbpreset und/oder beat-synchrone Effekte anwenden")
    parser.add_argument("video_path")
    parser.add_argument("out_path")
    parser.add_argument("--color-preset", choices=list(COLOR_PRESETS))
    parser.add_argument("--beats-json", help="JSON-Datei mit beat_times_sec (wie beat_detect.py --json ausgibt)")
    parser.add_argument("--zoom", type=float, help="Intensitaet 0..1")
    parser.add_argument("--flash", type=float, help="Intensitaet 0..1")
    parser.add_argument("--shake", type=float, help="Intensitaet 0..1")
    parser.add_argument("--rgb-split", type=float, help="Intensitaet 0..1")
    args = parser.parse_args()

    beat_times: list[float] = []
    if args.beats_json:
        data = json.loads(Path(args.beats_json).read_text(encoding="utf-8"))
        beat_times = data["beat_times_sec"]

    effects = BeatEffectConfig(zoom=args.zoom, flash=args.flash, shake=args.shake, rgb_split=args.rgb_split)
    try:
        out = render_with_beat_effects(
            args.video_path, beat_times, args.out_path,
            color_preset=args.color_preset, effects=effects,
        )
    except subprocess.CalledProcessError as e:
        print(f"ffmpeg fehlgeschlagen:\n{e.stderr}")
        raise SystemExit(1)
    print(f"Export fertig: {out}")


if __name__ == "__main__":
    _main()
