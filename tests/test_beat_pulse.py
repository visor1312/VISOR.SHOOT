"""Tests fuer beat_pulse: Taktschlaege -> AudioPulse-Beats fuers Render-Fenster.

Wie test_beat_effects nutzt das einen synthetischen Klick-Track (120 BPM),
damit die Beat-Erkennung deterministisch ist.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from backend.pipeline.beat_pulse import beat_pulses_for_window


@pytest.fixture(scope="module")
def click_track(tmp_path_factory) -> Path:
    sr = 22050
    interval_sec = 0.5  # 120 BPM
    duration_sec = 20.0
    rng = np.random.default_rng(7)

    n_samples = int(duration_sec * sr)
    audio = rng.normal(scale=0.05, size=n_samples)

    decay_len = int(0.1 * sr)
    decay_env = np.exp(-np.linspace(0, 15, decay_len))
    t = interval_sec
    while t < duration_sec - 0.1:
        start = int(t * sr)
        audio[start:start + decay_len] += decay_env
        t += interval_sec

    audio = audio / np.max(np.abs(audio)) * 0.9
    out = tmp_path_factory.mktemp("pulsefixtures") / "click_track.wav"
    sf.write(str(out), audio, sr)
    return out


def test_pulses_lie_in_window_and_are_sorted(click_track):
    pulses = beat_pulses_for_window(click_track, 5.0, 10.0, fps=30)
    assert len(pulses) >= 5  # 5s Fenster bei ~0.5s Intervall
    frames = [p.frame for p in pulses]
    assert frames == sorted(frames)
    assert len(set(frames)) == len(frames)  # keine Duplikate
    # Frames relativ zum Fensterstart: 0 .. 5s*30fps
    assert all(0 <= f < 5.0 * 30 for f in frames)


def test_amplitudes_normalized(click_track):
    pulses = beat_pulses_for_window(click_track, 0.0, 20.0, fps=30)
    assert pulses
    assert all(0.0 <= p.amplitude <= 1.0 for p in pulses)
    # Klick-Track: die Schlaege sind deutlich, Amplituden sollen nicht am Boden kleben.
    assert max(p.amplitude for p in pulses) > 0.5


def test_stride_thins_out_beats(click_track):
    every = beat_pulses_for_window(click_track, 0.0, 20.0, fps=30)
    halved = beat_pulses_for_window(click_track, 0.0, 20.0, fps=30, stride=2)
    assert 0 < len(halved) <= len(every) // 2 + 1
    # stride behaelt genau jeden 2. Beat des vollen Rasters.
    assert [p.frame for p in halved] == [p.frame for p in every[::2]]


def test_dense_beats_are_auto_thinned(tmp_path_factory):
    """Doppeltempo-Fall (Rap/Hi-Hats): Beats alle 0.2s duerfen NICHT alle
    pulsieren, sonst ueberlappen sich die Envelopes und es flackert
    durchgehend. Auto-Stride muss auf >= MIN_PULSE_SPACING_SEC ausduennen."""
    from backend.pipeline.beat_pulse import MIN_PULSE_SPACING_SEC

    sr = 22050
    rng = np.random.default_rng(7)
    audio = rng.normal(scale=0.05, size=int(20 * sr))
    decay_env = np.exp(-np.linspace(0, 15, int(0.05 * sr)))
    t = 0.2
    while t < 19.9:  # 300 BPM Klicks
        start = int(t * sr)
        audio[start:start + len(decay_env)] += decay_env
        t += 0.2
    audio = audio / np.max(np.abs(audio)) * 0.9
    dense = tmp_path_factory.mktemp("dense") / "dense_clicks.wav"
    sf.write(str(dense), audio, sr)

    pulses = beat_pulses_for_window(dense, 0.0, 20.0, fps=30)
    assert len(pulses) >= 2
    min_gap_frames = min(np.diff([p.frame for p in pulses]))
    assert min_gap_frames >= MIN_PULSE_SPACING_SEC * 30 * 0.9  # kleine Toleranz


def test_silence_yields_no_pulses(tmp_path):
    sr = 22050
    silent = tmp_path / "silence.wav"
    sf.write(str(silent), np.zeros(int(6 * sr)), sr)
    assert beat_pulses_for_window(silent, 0.0, 6.0, fps=30) == []
