"""Schritt 08 (Phase 3): Automatischer, taktgenauer Schnitt zwischen mehreren
Takes derselben Songstelle.

Da alle Takes gegen denselben Song synchronisiert wurden (siehe sync_offset.py/
render_sync.py aus Phase 1, `offset_ms` pro Take), zeigt bei jedem gemeinsamen
Song-Zeitpunkt jeder Take passende Bildinformation - ein Wechsel zwischen
Takes an Taktgrenzen erzeugt daher keinen Sprung im (durchgehenden) Songton,
weil die Audiospur des Outputs immer die eine, ungeschnittene Songdatei ist -
nur das Bild wechselt zwischen den Takes.
"""
from __future__ import annotations

import argparse
import json
import random
import subprocess
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

OrderMode = Literal["fixed", "random"]

MIN_SEGMENT_DURATION = 0.05


@dataclass
class TakeInfo:
    video_path: str
    offset_ms: float
    duration_sec: float | None = None  # wird bei Bedarf per ffprobe ermittelt


@dataclass
class CutSegment:
    take_index: int
    song_start: float
    song_end: float


def _probe_duration_sec(path: str | Path) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        check=True, capture_output=True, text=True,
    )
    return float(result.stdout.strip())


def _probe_dimensions(video_path: str | Path) -> tuple[int, int]:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height", "-of", "csv=s=x:p=0", str(video_path)],
        check=True, capture_output=True, text=True,
    )
    # ffprobe haengt je nach Version/Datei ein ueberzaehliges Trennzeichen an
    # ("1080x1920x") - daher tolerant parsen statt strikt entpacken.
    parts = [p for p in result.stdout.strip().split("x") if p]
    return int(parts[0]), int(parts[1])


def compute_multitake_plan(
    takes: list[TakeInfo],
    beat_times_song: list[float],
    beat_interval: int = 1,
    order_mode: OrderMode = "fixed",
    seed: int | None = None,
) -> list[CutSegment]:
    """Berechnet den Schnittplan (welcher Take spielt in welchem Song-Zeitfenster).

    `beat_times_song` sind Taktschlaege im Zeitrahmen des SONGS (nicht eines
    einzelnen Takes) - z.B. per beat_detect.py auf der Songdatei selbst
    erkannt. `offset_ms` jedes Takes stammt aus Phase 1 (sync_offset.py).
    """
    if len(takes) < 2:
        raise ValueError("Multi-Take-Schnitt braucht mindestens 2 Takes")
    if beat_interval < 1:
        raise ValueError("beat_interval muss >= 1 sein")

    for t in takes:
        if t.duration_sec is None:
            t.duration_sec = _probe_duration_sec(t.video_path)

    song_start = max(t.offset_ms / 1000.0 for t in takes)
    song_end = min(t.offset_ms / 1000.0 + t.duration_sec for t in takes)
    if song_end - song_start < MIN_SEGMENT_DURATION:
        raise ValueError(
            "Die Takes ueberlappen sich im Song nicht ausreichend fuer einen "
            "gemeinsamen Multi-Take-Schnitt (zu unterschiedliche Offsets/Laengen)."
        )

    filtered_beats = [b for b in beat_times_song if song_start <= b <= song_end]
    cut_points = filtered_beats[::beat_interval]
    if not cut_points or cut_points[0] > song_start + 0.01:
        cut_points.insert(0, song_start)
    if cut_points[-1] < song_end - 0.01:
        cut_points.append(song_end)

    raw_segments = [
        (s, e) for s, e in zip(cut_points, cut_points[1:]) if e - s >= MIN_SEGMENT_DURATION
    ]
    if len(raw_segments) < 1:
        raise ValueError("Zu wenige Taktschlaege im gemeinsamen Zeitfenster fuer einen Schnitt.")

    if order_mode == "fixed":
        take_indices = [i % len(takes) for i in range(len(raw_segments))]
    elif order_mode == "random":
        rng = random.Random(seed)
        take_indices = [rng.randrange(len(takes)) for _ in raw_segments]
    else:
        raise ValueError(f"Unbekannter order_mode: {order_mode}")

    return [
        CutSegment(take_index=idx, song_start=s, song_end=e)
        for (s, e), idx in zip(raw_segments, take_indices)
    ]


def render_multitake_cut(
    takes: list[TakeInfo],
    song_path: str | Path,
    plan: list[CutSegment],
    out_path: str | Path,
    target_width: int = 1080,
    target_height: int = 1920,
    crf: int = 19,
    audio_bitrate: str = "192k",
) -> Path:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    usage_count = Counter(seg.take_index for seg in plan)
    filter_parts: list[str] = []
    split_labels: dict[int, list[str]] = {}

    for idx, count in usage_count.items():
        if count == 1:
            split_labels[idx] = [f"{idx}:v"]
        else:
            outs = [f"tk{idx}_{k}" for k in range(count)]
            filter_parts.append(f"[{idx}:v]split={count}" + "".join(f"[{o}]" for o in outs))
            split_labels[idx] = outs

    consume_counters: dict[int, int] = defaultdict(int)
    segment_labels: list[str] = []
    for seg_i, seg in enumerate(plan):
        offset_sec = takes[seg.take_index].offset_ms / 1000.0
        duration = takes[seg.take_index].duration_sec or float("inf")
        local_start = max(0.0, seg.song_start - offset_sec)
        local_end = min(duration, seg.song_end - offset_sec)

        src_label = split_labels[seg.take_index][consume_counters[seg.take_index]]
        consume_counters[seg.take_index] += 1
        seg_label = f"seg{seg_i}"
        filter_parts.append(
            f"[{src_label}]trim=start={local_start:.6f}:end={local_end:.6f},"
            f"setpts=PTS-STARTPTS[{seg_label}]"
        )
        segment_labels.append(seg_label)

    concat_inputs = "".join(f"[{l}]" for l in segment_labels)
    filter_parts.append(f"{concat_inputs}concat=n={len(segment_labels)}:v=1:a=0[vcat]")
    filter_parts.append(
        f"[vcat]scale={target_width}:{target_height}:force_original_aspect_ratio=decrease,"
        f"pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2,setsar=1[vout]"
    )

    song_start = plan[0].song_start
    song_end = plan[-1].song_end
    song_input_idx = len(takes)
    filter_parts.append(
        f"[{song_input_idx}:a]atrim=start={song_start:.6f}:end={song_end:.6f},asetpts=PTS-STARTPTS[aout]"
    )

    filter_complex = ";".join(filter_parts)

    cmd = ["ffmpeg", "-y"]
    for t in takes:
        cmd += ["-i", str(t.video_path)]
    cmd += ["-i", str(song_path)]
    cmd += [
        "-filter_complex", filter_complex,
        "-map", "[vout]", "-map", "[aout]",
        "-c:v", "libx264", "-preset", "medium", "-crf", str(crf), "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", audio_bitrate,
        "-movflags", "+faststart",
        str(out_path),
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True)
    return out_path


def _main() -> None:
    parser = argparse.ArgumentParser(description="Taktgenauer Multi-Take-Schnitt")
    parser.add_argument("config_json", help="JSON mit takes=[{video_path,offset_ms}], song_path, beat_times_sec")
    parser.add_argument("out_path")
    parser.add_argument("--beat-interval", type=int, default=1, choices=[1, 2, 4])
    parser.add_argument("--order-mode", choices=["fixed", "random"], default="fixed")
    parser.add_argument("--seed", type=int, default=None)
    args = parser.parse_args()

    config = json.loads(Path(args.config_json).read_text(encoding="utf-8"))
    takes = [TakeInfo(**t) for t in config["takes"]]

    try:
        plan = compute_multitake_plan(
            takes, config["beat_times_sec"], args.beat_interval, args.order_mode, args.seed,
        )
        out = render_multitake_cut(takes, config["song_path"], plan, args.out_path)
    except (ValueError, subprocess.CalledProcessError) as e:
        stderr = getattr(e, "stderr", None)
        print(f"Fehler: {e}" + (f"\n{stderr}" if stderr else ""))
        raise SystemExit(1)

    print(f"Export fertig: {out} ({len(plan)} Segmente)")


if __name__ == "__main__":
    _main()
