"""Schritt 10 (Roadmap-Ausbaustufe): Automatische Hook-/Refrain-Erkennung.

Findet den Abschnitt eines Songs, der sich am ehesten als Social-Media-Hook
eignet - typischerweise der Refrain. Hook-Score 2.0 kombiniert vier Signale:

- Wiederholung: beat-synchrones Chroma + Self-Similarity (Standard-MIR-
  Technik fuer Chorus-Detection: der Refrain ist die Stelle, die sich am
  eindeutigsten an einer ANDEREN Stelle im Song wiederholt)
- Energie: RMS des Fensters relativ zum Song-Durchschnitt
- Vocals (optional, via vocal_separation.py/Demucs): Vocal-Praesenz und
  Flow-Dichte im Vocal-Stem - ein Rap-Hook hat praesente, rhythmisch
  artikulierte Vocals, was aus dem Gesamtmix nicht ablesbar ist
- Position: milde Abwertung des Song-Anfangs (Intros wiederholen sich oft,
  sind aber selten der Hook)

Ohne Vocal-Stem (demucs nicht installiert / Modell-Download nicht moeglich)
rechnet alles wie bisher rein mit librosa weiter.

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
# Unterhalb dieses mittleren RMS gilt ein Vocal-Stem als "praktisch stumm"
# (Instrumental) und die Vocal-Features werden ignoriert.
MIN_VOCAL_RMS = 1e-4
# Fenster, die in den ersten 10% des Songs starten, werden mild abgewertet
# (linear von INTRO_PENALTY hoch auf 1.0).
INTRO_FRACTION = 0.10
INTRO_PENALTY = 0.8


@dataclass
class HookCandidate:
    start_sec: float
    end_sec: float
    repetition_score: float  # 0..1, wie stark sich dieser Abschnitt woanders im Song wiederholt
    energy_score: float      # relative Lautstaerke ggue. Songdurchschnitt (1.0 = Durchschnitt)
    vocal_score: float | None = None  # Vocal-Praesenz x Flow-Dichte rel. zum Songdurchschnitt; None = kein Vocal-Stem
    viral_score: float = 0.0          # 0..100, kombinierte Bewertung fuers UI


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


def _bar_vocal_features(
    vocals_path: str | Path, sr: int, bar_bounds: np.ndarray
) -> tuple[np.ndarray, np.ndarray] | None:
    """Vocal-Praesenz (RMS) und Flow-Dichte (Onset-Staerke) pro Takt.

    None, wenn der Stem praktisch stumm ist (Instrumental) - dann sagen die
    Vocal-Features nichts aus und wuerden nur Rauschen in den Score bringen.
    """
    yv, _ = librosa.load(str(vocals_path), sr=sr, mono=True)
    vocal_rms = _bar_rms(yv, sr, bar_bounds)
    if float(np.mean(vocal_rms)) < MIN_VOCAL_RMS:
        return None

    onset_env = librosa.onset.onset_strength(y=yv, sr=sr)
    bar_frames = librosa.time_to_frames(bar_bounds, sr=sr)
    bar_frames = np.clip(bar_frames, 0, len(onset_env))
    n_bars = len(bar_bounds) - 1
    vocal_onset = np.zeros(n_bars)
    for i in range(n_bars):
        segment = onset_env[bar_frames[i]:bar_frames[i + 1]]
        vocal_onset[i] = float(np.mean(segment)) if len(segment) > 0 else 0.0
    return vocal_rms, vocal_onset


def _position_prior(start_sec: float, song_duration_sec: float) -> float:
    """Milde Abwertung des Song-Anfangs: Intros sind selten der Hook."""
    if song_duration_sec <= 0:
        return 1.0
    frac = start_sec / song_duration_sec
    return INTRO_PENALTY + (1.0 - INTRO_PENALTY) * min(frac / INTRO_FRACTION, 1.0)


def _viral_score(repetition: float, energy: float, vocal: float | None) -> float:
    """Kombiniert die Signale zu einer verkaufbaren 0-100-Zahl.

    Gewichtete Summe statt Produkt, damit die Skala interpretierbar bleibt
    (Produkt der Roh-Scores bleibt das interne Ranking-Kriterium). Energie-
    und Vocal-Terme sind relative Werte um 1.0 und werden auf [0, 1.5]
    gedeckelt, damit ein Ausreisser nicht alles dominiert.
    """
    energy_norm = min(max(energy, 0.0), 1.5) / 1.5
    if vocal is None:
        combined = 0.65 * repetition + 0.35 * energy_norm
    else:
        vocal_norm = min(max(vocal, 0.0), 1.5) / 1.5
        combined = 0.5 * repetition + 0.25 * energy_norm + 0.25 * vocal_norm
    return round(100.0 * min(max(combined, 0.0), 1.0), 1)


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
    vocals_path: str | Path | None = None,
) -> HookResult:
    """Findet den vielversprechendsten Hook-/Refrain-Abschnitt eines Songs.

    `vocals_path`: optionaler Vocal-Stem (aus vocal_separation.separate_vocals).
    Ohne ihn wird rein aus dem Gesamtmix bewertet.
    """
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

    # Vocal-Features (optional): Praesenz und Flow-Dichte relativ zum
    # Song-Durchschnitt, geometrisches Mittel als ein Vocal-Score pro Fenster.
    vocal_scores: np.ndarray | None = None
    if vocals_path is not None:
        vocal_features = _bar_vocal_features(vocals_path, sample_rate, bar_bounds)
        if vocal_features is not None:
            vocal_rms, vocal_onset = vocal_features
            mean_rms = float(np.mean(vocal_rms)) or 1e-9
            mean_onset = float(np.mean(vocal_onset)) or 1e-9
            presence = np.array([
                np.mean(vocal_rms[i:i + k]) / mean_rms for i in range(n_windows)
            ])
            flow = np.array([
                np.mean(vocal_onset[i:i + k]) / mean_onset for i in range(n_windows)
            ])
            vocal_scores = np.sqrt(np.clip(presence, 1e-9, None) * np.clip(flow, 1e-9, None))

    song_duration_sec = float(len(y)) / sr
    priors = np.array([
        _position_prior(float(bar_bounds[i]), song_duration_sec) for i in range(n_windows)
    ])

    combined = scores * energy_scores * priors
    if vocal_scores is not None:
        combined = combined * vocal_scores

    order = np.argsort(combined)[::-1]
    candidates: list[HookCandidate] = []
    for idx in order:
        start_idx = int(idx)
        if any(abs(start_idx - c_idx) < k for c_idx in [c[0] for c in candidates]):
            continue
        vocal = float(vocal_scores[start_idx]) if vocal_scores is not None else None
        candidates.append((start_idx, HookCandidate(
            start_sec=float(bar_bounds[start_idx]),
            end_sec=float(bar_bounds[start_idx + k]),
            repetition_score=float(scores[start_idx]),
            energy_score=float(energy_scores[start_idx]),
            vocal_score=vocal,
            viral_score=_viral_score(float(scores[start_idx]), float(energy_scores[start_idx]), vocal),
        )))
        if len(candidates) >= MAX_ALTERNATIVES + 1:
            break

    if not candidates:
        raise ValueError("Keine Hook-Kandidaten gefunden.")

    best = candidates[0][1]
    alternatives = [c[1] for c in candidates[1:]]
    return HookResult(best=best, alternatives=alternatives)


def _format_candidate(c: HookCandidate) -> str:
    parts = [
        f"Viral-Score: {c.viral_score:.0f}/100",
        f"Wiederholung: {c.repetition_score:.2f}",
        f"Energie: {c.energy_score:.2f}x",
    ]
    if c.vocal_score is not None:
        parts.append(f"Vocals: {c.vocal_score:.2f}x")
    return f"{c.start_sec:.1f}s - {c.end_sec:.1f}s ({', '.join(parts)})"


def _main() -> None:
    parser = argparse.ArgumentParser(description="Hook-/Refrain-Abschnitt eines Songs automatisch finden")
    parser.add_argument("song_path")
    parser.add_argument("--target-duration", type=float, default=DEFAULT_TARGET_DURATION)
    parser.add_argument("--min-duration", type=float, default=DEFAULT_MIN_DURATION)
    parser.add_argument("--max-duration", type=float, default=DEFAULT_MAX_DURATION)
    parser.add_argument("--no-vocals", action="store_true",
                        help="Vocal-Separation ueberspringen (schneller, ungenauer)")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    vocals = None
    if not args.no_vocals:
        from backend.pipeline.vocal_separation import separate_vocals
        vocals = separate_vocals(args.song_path)
        if vocals is None:
            print("Hinweis: Vocal-Separation nicht verfuegbar - bewerte ohne Vocal-Features.")

    try:
        result = detect_hook(args.song_path, args.target_duration, args.min_duration,
                             args.max_duration, vocals_path=vocals)
    except ValueError as e:
        print(f"Fehler: {e}")
        raise SystemExit(1)

    if args.json:
        print(json.dumps({
            "best": asdict(result.best),
            "alternatives": [asdict(c) for c in result.alternatives],
        }, indent=2))
    else:
        print(f"Hook: {_format_candidate(result.best)}")
        for i, alt in enumerate(result.alternatives, 1):
            print(f"Alternative {i}: {_format_candidate(alt)}")


if __name__ == "__main__":
    _main()
