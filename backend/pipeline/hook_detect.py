"""Schritt 10 (Roadmap-Ausbaustufe): Automatische Hook-/Refrain-Erkennung.

Findet den Abschnitt eines Songs, der sich am ehesten als Social-Media-Hook
eignet - typischerweise der Refrain: ein Abschnitt, der sich im Song
wiederholt UND ueberdurchschnittlich energiereich ist. Loest ein Problem, das
VOR dem Filmen auftritt (welchen Teil des Songs performen?), nutzt aber
dieselbe Werkzeugkiste wie die bestehende Pipeline:

- beat_detect.py fuer Taktschlaege -> Takt-Grenzen (4/4 angenommen)
- librosa fuer beat-synchrones Chroma + Self-Similarity (Standard-MIR-Technik
  fuer Chorus-Detection: der Refrain ist die Stelle, die sich am
  eindeutigsten an einer ANDEREN Stelle im Song wiederholt)

Das Ergebnis ist ein Zeitfenster im Song (nicht in einem bestimmten Video-
Take) - Video-Takes werden ueber ihr `offset_ms` aus Phase 1 damit verrechnet.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import librosa
import numpy as np

from backend.pipeline.beat_detect import detect_beats

BEATS_PER_BAR = 4
MIN_BARS_REQUIRED = 8
DEFAULT_TARGET_DURATION = 20.0
DEFAULT_MIN_DURATION = 15.0
DEFAULT_MAX_DURATION = 30.0
MAX_ALTERNATIVES = 3


@dataclass
class HookCandidate:
    start_sec: float
    end_sec: float
    repetition_score: float  # 0..1, wie stark sich dieser Abschnitt woanders im Song wiederholt
    energy_score: float      # relative Lautstaerke ggue. Songdurchschnitt (1.0 = Durchschnitt)


@dataclass
class HookResult:
    best: HookCandidate
    alternatives: list[HookCandidate]


def _bar_boundaries(beat_times_sec: list[float]) -> np.ndarray:
    bars = beat_times_sec[0::BEATS_PER_BAR]
    return np.array(bars, dtype=np.float64)


def _bar_chroma(y: np.ndarray, sr: int, bar_bounds: np.ndarray) -> np.ndarray:
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
    bar_frames = librosa.time_to_frames(bar_bounds, sr=sr)
    bar_frames = np.clip(bar_frames, 0, chroma.shape[1])
    # librosa.util.sync mit N Grenzen liefert N Segmente zurueck (das letzte
    # reicht bis zum Ende der Audiodatei) - wir wollen aber nur die N-1
    # Segmente ZWISCHEN den Taktgrenzen, konsistent mit _bar_rms().
    synced = librosa.util.sync(chroma, bar_frames, aggregate=np.mean)
    return synced[:, :len(bar_bounds) - 1]


def _bar_rms(y: np.ndarray, sr: int, bar_bounds: np.ndarray) -> np.ndarray:
    n_bars = len(bar_bounds) - 1
    rms = np.zeros(n_bars)
    for i in range(n_bars):
        start_sample = int(bar_bounds[i] * sr)
        end_sample = int(bar_bounds[i + 1] * sr)
        segment = y[start_sample:end_sample]
        rms[i] = np.sqrt(np.mean(segment ** 2)) if len(segment) > 0 else 0.0
    return rms


def _choose_bars_per_window(bar_bounds: np.ndarray, target: float, min_dur: float, max_dur: float) -> int:
    bar_durations = np.diff(bar_bounds)
    mean_bar_dur = float(np.mean(bar_durations))
    if mean_bar_dur <= 0:
        raise ValueError("Ungueltige Takt-Dauer erkannt.")

    best_k, best_diff = None, float("inf")
    for k in range(2, len(bar_bounds)):
        dur = k * mean_bar_dur
        if dur < min_dur or dur > max_dur:
            continue
        diff = abs(dur - target)
        if diff < best_diff:
            best_k, best_diff = k, diff
    if best_k is None:
        # Kein Fenster passt exakt in den Bereich - naechstbeste Groesse nehmen.
        best_k = max(2, round(target / mean_bar_dur))
    return best_k


def detect_hook(
    song_path: str | Path,
    target_duration_sec: float = DEFAULT_TARGET_DURATION,
    min_duration: float = DEFAULT_MIN_DURATION,
    max_duration: float = DEFAULT_MAX_DURATION,
    sample_rate: int = 22050,
) -> HookResult:
    """Findet den vielversprechendsten Hook-/Refrain-Abschnitt eines Songs."""
    beats = detect_beats(song_path, sample_rate=sample_rate)
    bar_bounds = _bar_boundaries(beats.beat_times_sec)
    if len(bar_bounds) < MIN_BARS_REQUIRED:
        raise ValueError(
            f"Zu wenige Taktschlaege erkannt ({len(beats.beat_times_sec)}) fuer eine "
            "verlaessliche Hook-Erkennung - Song zu kurz oder zu percussion-arm?"
        )

    y, sr = librosa.load(str(song_path), sr=sample_rate, mono=True)
    bar_chroma = _bar_chroma(y, sr, bar_bounds)
    bar_rms = _bar_rms(y, sr, bar_bounds)
    song_mean_rms = float(np.mean(bar_rms)) or 1e-9

    n_bars = bar_chroma.shape[1]
    k = _choose_bars_per_window(bar_bounds, target_duration_sec, min_duration, max_duration)
    if n_bars - k < 2:
        raise ValueError("Song zu kurz fuer die gewaehlte Hook-Laenge.")

    # Normierte Chroma-Vektoren fuer Cosinus-Aehnlichkeit.
    norms = np.linalg.norm(bar_chroma, axis=0, keepdims=True)
    norms[norms == 0] = 1e-9
    normed = bar_chroma / norms

    n_windows = n_bars - k + 1
    scores = np.zeros(n_windows)
    for i in range(n_windows):
        window_i = normed[:, i:i + k]
        best_match = 0.0
        for j in range(n_windows):
            if abs(j - i) < k:  # ueberlappende/identische Fenster ausschliessen
                continue
            window_j = normed[:, j:j + k]
            # Mittlere Cosinus-Aehnlichkeit takt-fuer-takt zwischen beiden Fenstern.
            sim = float(np.mean(np.sum(window_i * window_j, axis=0)))
            best_match = max(best_match, sim)
        scores[i] = best_match

    energy_scores = np.array([
        (np.mean(bar_rms[i:i + k]) / song_mean_rms) for i in range(n_windows)
    ])
    combined = scores * energy_scores

    order = np.argsort(combined)[::-1]
    candidates: list[HookCandidate] = []
    for idx in order:
        start_idx = int(idx)
        if any(abs(start_idx - c_idx) < k for c_idx in [c[0] for c in candidates]):
            continue
        candidates.append((start_idx, HookCandidate(
            start_sec=float(bar_bounds[start_idx]),
            end_sec=float(bar_bounds[start_idx + k]),
            repetition_score=float(scores[start_idx]),
            energy_score=float(energy_scores[start_idx]),
        )))
        if len(candidates) >= MAX_ALTERNATIVES + 1:
            break

    if not candidates:
        raise ValueError("Keine Hook-Kandidaten gefunden.")

    best = candidates[0][1]
    alternatives = [c[1] for c in candidates[1:]]
    return HookResult(best=best, alternatives=alternatives)


def _main() -> None:
    parser = argparse.ArgumentParser(description="Hook-/Refrain-Abschnitt eines Songs automatisch finden")
    parser.add_argument("song_path")
    parser.add_argument("--target-duration", type=float, default=DEFAULT_TARGET_DURATION)
    parser.add_argument("--min-duration", type=float, default=DEFAULT_MIN_DURATION)
    parser.add_argument("--max-duration", type=float, default=DEFAULT_MAX_DURATION)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    try:
        result = detect_hook(args.song_path, args.target_duration, args.min_duration, args.max_duration)
    except ValueError as e:
        print(f"Fehler: {e}")
        raise SystemExit(1)

    if args.json:
        print(json.dumps({
            "best": asdict(result.best),
            "alternatives": [asdict(c) for c in result.alternatives],
        }, indent=2))
    else:
        b = result.best
        print(f"Hook: {b.start_sec:.1f}s - {b.end_sec:.1f}s "
              f"(Wiederholung: {b.repetition_score:.2f}, Energie: {b.energy_score:.2f}x Durchschnitt)")
        for i, alt in enumerate(result.alternatives, 1):
            print(f"Alternative {i}: {alt.start_sec:.1f}s - {alt.end_sec:.1f}s "
                  f"(Wiederholung: {alt.repetition_score:.2f}, Energie: {alt.energy_score:.2f}x)")


if __name__ == "__main__":
    _main()
