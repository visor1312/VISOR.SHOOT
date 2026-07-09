"""Tests fuer Phase 3: Beat-Detection und beat-synchrone Effekte/Farbgrading.

Nutzt einen synthetisch erzeugten Klick-Track (regelmaessige perkussive
Treffer bei bekanntem Intervall) statt echter Musik, um die Beat-Erkennung
deterministisch zu testen, sowie kurze Testvideos (ffmpeg lavfi) fuer die
Effekt-Pipeline.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from backend.pipeline.beat_detect import detect_beats
from backend.pipeline.effects_grading import (
    COLOR_PRESETS,
    BeatEffectConfig,
    _beat_pulse_expr,
    apply_color_preset,
    render_with_beat_effects,
)


def _run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True, capture_output=True, text=True)


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
    out = tmp_path_factory.mktemp("beatfixtures") / "click_track.wav"
    sf.write(str(out), audio, sr)
    return out


@pytest.fixture(scope="module")
def test_video(tmp_path_factory) -> Path:
    out = tmp_path_factory.mktemp("beatfixtures") / "test.mp4"
    _run([
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "testsrc2=size=720x1280:duration=4:rate=30",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=4",
        "-c:v", "libx264", "-preset", "ultrafast", "-c:a", "aac", "-shortest",
        str(out),
    ])
    return out


def test_detect_beats_finds_regular_spacing(click_track):
    result = detect_beats(click_track)
    assert result.tempo_bpm > 0
    assert len(result.beat_times_sec) >= 10

    diffs = np.diff(result.beat_times_sec)
    # Erwartet: 0.5s Intervall, ggf. Oktavfehler (0.25s oder 1.0s) sind ein
    # bekanntes, akzeptables Verhalten von librosa.beat.beat_track.
    median_diff = np.median(diffs)
    assert median_diff == pytest.approx(0.5, abs=0.05) or median_diff == pytest.approx(0.25, abs=0.03) \
        or median_diff == pytest.approx(1.0, abs=0.05)
    # Taktschlaege sollen untereinander konsistent (nicht chaotisch) verteilt sein.
    assert np.std(diffs) < 0.05


def test_beat_pulse_expr_empty():
    assert _beat_pulse_expr([]) == "0"


def test_beat_pulse_expr_structure():
    expr = _beat_pulse_expr([1.0, 2.0])
    assert expr.startswith("(") and expr.endswith(")")
    assert "1.000" in expr and "2.000" in expr


def test_apply_color_preset_unknown_raises(tmp_path, test_video):
    with pytest.raises(ValueError):
        apply_color_preset(test_video, "does-not-exist", tmp_path / "out.mp4")


@pytest.mark.parametrize("preset", list(COLOR_PRESETS))
def test_apply_color_preset_produces_valid_video(tmp_path, test_video, preset):
    out = apply_color_preset(test_video, preset, tmp_path / f"{preset}.mp4")
    assert out.exists()
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height",
         "-of", "csv=p=0", str(out)],
        check=True, capture_output=True, text=True,
    )
    assert "720" in probe.stdout and "1280" in probe.stdout


@pytest.mark.parametrize("kwargs", [
    {"zoom": 0.15},
    {"flash": 0.3},
    {"shake": 0.5},
    {"rgb_split": 0.6},
])
def test_render_with_single_beat_effect(tmp_path, test_video, kwargs):
    beat_times = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5]
    out = render_with_beat_effects(
        test_video, beat_times, tmp_path / "out.mp4", effects=BeatEffectConfig(**kwargs),
    )
    assert out.exists()
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "stream=width,height",
         "-of", "csv=p=0", str(out)],
        check=True, capture_output=True, text=True,
    )
    assert "720" in probe.stdout and "1280" in probe.stdout


def test_render_with_all_effects_and_color_preset_combined(tmp_path, test_video):
    beat_times = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5]
    out = render_with_beat_effects(
        test_video, beat_times, tmp_path / "combo.mp4",
        color_preset="cold_urban",
        effects=BeatEffectConfig(zoom=0.12, flash=0.3, shake=0.5, rgb_split=0.5),
    )
    assert out.exists()
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(out)],
        check=True, capture_output=True, text=True,
    )
    assert float(probe.stdout.strip()) == pytest.approx(4.0, abs=0.5)


def test_render_with_no_effects_still_produces_output(tmp_path, test_video):
    out = render_with_beat_effects(test_video, [], tmp_path / "plain.mp4")
    assert out.exists()
