"""Test fuer die Hook-/Refrain-Erkennung mit einem synthetischen Song fester
Struktur: Strophe-Refrain-Strophe-Refrain-Strophe (A-B-A-B-A). B ist lauter
und wiederholt sich zweimal - genau das Muster, nach dem detect_hook() suchen
soll (Wiederholung + ueberdurchschnittliche Energie).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from backend.pipeline.hook_detect import detect_hook


def _section(duration_sec: float, sr: int, chord_freqs: list[float], amplitude: float, seed: int) -> np.ndarray:
    """Baut einen Songabschnitt: durchgehender Klick-Beat (fuer die
    Takterkennung) + ein charakteristischer Akkord (fuer die Chroma-Analyse)."""
    rng = np.random.default_rng(seed)
    n = int(duration_sec * sr)
    t = np.arange(n) / sr

    chord = np.zeros(n)
    for f in chord_freqs:
        chord += np.sin(2 * np.pi * f * t)
    chord = chord / len(chord_freqs) * amplitude

    # Klick-Beat alle 0.5s (120 BPM), damit beat_detect zuverlaessig Takte findet.
    beat_interval = 0.5
    decay_len = int(0.08 * sr)
    decay_env = np.exp(-np.linspace(0, 15, decay_len))
    clicks = np.zeros(n)
    t_click = 0.0
    while t_click < duration_sec:
        start = int(t_click * sr)
        end = min(start + decay_len, n)
        clicks[start:end] += decay_env[:end - start] * 0.5
        t_click += beat_interval

    noise = rng.normal(scale=0.02, size=n)
    return chord + clicks + noise


@pytest.fixture(scope="module")
def structured_song(tmp_path_factory) -> tuple[Path, float, float]:
    """Baut A-B-A-B-A und gibt (Pfad, section_duration, gesamt_dauer) zurueck."""
    sr = 22050
    section_dur = 8.0

    # A = "Strophe": leiser, Akkord aus tieferen Toenen (A-C-E).
    a_freqs = [220.0, 261.63, 329.63]
    # B = "Refrain": lauter, anderer Akkord (F-A-C, eine Terz hoeher liegend).
    b_freqs = [349.23, 440.0, 523.25]

    sections = [
        _section(section_dur, sr, a_freqs, amplitude=0.35, seed=1),
        _section(section_dur, sr, b_freqs, amplitude=0.7, seed=2),
        _section(section_dur, sr, a_freqs, amplitude=0.35, seed=3),
        _section(section_dur, sr, b_freqs, amplitude=0.7, seed=4),
        _section(section_dur, sr, a_freqs, amplitude=0.35, seed=5),
    ]
    audio = np.concatenate(sections)
    audio = audio / np.max(np.abs(audio)) * 0.9

    out = tmp_path_factory.mktemp("hookfixtures") / "song.wav"
    sf.write(str(out), np.column_stack([audio, audio]), sr)
    return out, section_dur, len(sections) * section_dur


def _section_index(t: float, section_dur: float) -> int:
    return int(t // section_dur)


def test_detect_hook_finds_repeated_louder_section(structured_song):
    song_path, section_dur, total_dur = structured_song
    result = detect_hook(song_path, target_duration_sec=8.0, min_duration=6.0, max_duration=10.0)

    best = result.best
    midpoint = (best.start_sec + best.end_sec) / 2
    midpoint_section = _section_index(midpoint, section_dur)

    # B liegt in Abschnitt 1 und 3 (0-indiziert: A=0,2,4  B=1,3). Die
    # Fenstergrenzen koennen wegen der Taktraster-Schaetzung leicht (< 1
    # Takt) in den naechsten Abschnitt hineinragen - die Fenstermitte muss
    # trotzdem eindeutig in einem B-Abschnitt liegen.
    assert midpoint_section in (1, 3)
    assert best.energy_score > 1.0  # B ist lauter als der Songdurchschnitt
    assert best.repetition_score > 0.5  # deutliche Wiederholung erkannt


def test_detect_hook_alternative_is_other_b_occurrence(structured_song):
    song_path, section_dur, _ = structured_song
    result = detect_hook(song_path, target_duration_sec=8.0, min_duration=6.0, max_duration=10.0)

    all_candidates = [result.best] + result.alternatives
    b_candidates = [
        c for c in all_candidates
        if _section_index(c.start_sec + 0.5, section_dur) in (1, 3)
    ]
    # Beide B-Vorkommen sollten unter den Top-Kandidaten auftauchen.
    assert len(b_candidates) >= 2


def test_detect_hook_raises_on_too_short_song(tmp_path):
    sr = 22050
    audio = np.random.default_rng(0).normal(scale=0.1, size=int(2 * sr))
    path = tmp_path / "short.wav"
    sf.write(str(path), audio, sr)
    with pytest.raises(ValueError):
        detect_hook(path)
