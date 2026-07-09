"""Schritt 06 (Phase 3): Taktschlaege einer Audio-/Videodatei erkennen.

Nutzt librosa.beat.beat_track. Wird auf der bereits synchronisierten
Output-Audiospur eines Takes aufgerufen (nicht auf der rohen Songdatei),
damit die zurueckgegebenen Zeitstempel direkt im Zeitrahmen des fertigen
Videos liegen - analog zu transcribe.py in Phase 2, aus demselben Grund
(keine zusaetzliche Offset-Verrechnung noetig).
"""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import librosa
import numpy as np

DEFAULT_SAMPLE_RATE = 22050


@dataclass
class BeatResult:
    tempo_bpm: float
    beat_times_sec: list[float]


def detect_beats(audio_path: str | Path, sample_rate: int = DEFAULT_SAMPLE_RATE) -> BeatResult:
    y, sr = librosa.load(str(audio_path), sr=sample_rate, mono=True)
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
    beat_times = librosa.frames_to_time(beat_frames, sr=sr)
    tempo_bpm = float(tempo) if np.isscalar(tempo) else float(tempo[0])
    return BeatResult(tempo_bpm=tempo_bpm, beat_times_sec=[float(t) for t in beat_times])


def _main() -> None:
    parser = argparse.ArgumentParser(description="Taktschlaege einer Audio-/Videodatei erkennen")
    parser.add_argument("audio_path")
    parser.add_argument("--sample-rate", type=int, default=DEFAULT_SAMPLE_RATE)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    result = detect_beats(args.audio_path, args.sample_rate)
    if args.json:
        print(json.dumps(asdict(result), indent=2))
    else:
        print(f"Tempo: {result.tempo_bpm:.1f} BPM, {len(result.beat_times_sec)} Taktschlaege erkannt")
        print(", ".join(f"{t:.2f}" for t in result.beat_times_sec[:20]) + (" ..." if len(result.beat_times_sec) > 20 else ""))


if __name__ == "__main__":
    _main()
