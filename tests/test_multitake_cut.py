"""Tests fuer den Multi-Take-Schnitt (Phase 3): Schnittplan-Berechnung und
Rendering mit synthetischen "Takes" (unterschiedliche Farben, damit man den
Wechsel im Schnittplan nachvollziehen kann) und einer synthetischen Songdatei.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from backend.pipeline.multitake_cut import (
    TakeInfo,
    compute_multitake_plan,
    render_multitake_cut,
)


def _run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True, capture_output=True, text=True)


@pytest.fixture(scope="module")
def song_path(tmp_path_factory) -> Path:
    sr = 44100
    duration_sec = 15.0
    rng = np.random.default_rng(3)
    audio = rng.normal(scale=0.1, size=int(duration_sec * sr))
    out = tmp_path_factory.mktemp("mtfixtures") / "song.wav"
    sf.write(str(out), np.column_stack([audio, audio]), sr)
    return out


@pytest.fixture(scope="module")
def take_videos(tmp_path_factory) -> tuple[Path, Path]:
    d = tmp_path_factory.mktemp("mtfixtures")
    red = d / "take_red.mp4"
    blue = d / "take_blue.mp4"
    for path, color in [(red, "red"), (blue, "blue")]:
        _run([
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", f"color=c={color}:size=720x1280:duration=10:rate=30",
            "-f", "lavfi", "-i", "sine=frequency=220:duration=10",
            "-c:v", "libx264", "-preset", "ultrafast", "-c:a", "aac", "-shortest",
            str(path),
        ])
    return red, blue


def test_compute_plan_requires_at_least_two_takes(take_videos):
    red, _ = take_videos
    with pytest.raises(ValueError):
        compute_multitake_plan([TakeInfo(str(red), 0.0)], [1.0, 2.0])


def test_compute_plan_requires_overlap(take_videos):
    red, blue = take_videos
    takes = [TakeInfo(str(red), 0.0, duration_sec=10.0), TakeInfo(str(blue), 50000.0, duration_sec=10.0)]
    with pytest.raises(ValueError):
        compute_multitake_plan(takes, [1.0, 2.0])


def test_compute_plan_fixed_order_alternates(take_videos):
    red, blue = take_videos
    takes = [TakeInfo(str(red), 2000.0, duration_sec=10.0), TakeInfo(str(blue), 3000.0, duration_sec=10.0)]
    # usable window: max(2,3)=3s .. min(12,13)=12s
    beats = [3.5 + 0.5 * i for i in range(18)]  # 3.5 .. 12.0
    plan = compute_multitake_plan(takes, beats, beat_interval=1, order_mode="fixed")

    assert plan[0].song_start == pytest.approx(3.0)
    assert plan[-1].song_end == pytest.approx(12.0, abs=0.05)
    indices = [seg.take_index for seg in plan]
    assert indices == [i % 2 for i in range(len(indices))]
    # Segmente muessen lueckenlos aneinander anschliessen.
    for a, b in zip(plan, plan[1:]):
        assert a.song_end == pytest.approx(b.song_start)


def test_compute_plan_beat_interval_reduces_cuts(take_videos):
    red, blue = take_videos
    takes = [TakeInfo(str(red), 2000.0, duration_sec=10.0), TakeInfo(str(blue), 3000.0, duration_sec=10.0)]
    beats = [3.5 + 0.5 * i for i in range(18)]
    plan_every_beat = compute_multitake_plan(takes, beats, beat_interval=1, order_mode="fixed")
    plan_every_2nd = compute_multitake_plan(takes, beats, beat_interval=2, order_mode="fixed")
    assert len(plan_every_2nd) < len(plan_every_beat)


def test_compute_plan_random_order_is_reproducible_with_seed(take_videos):
    red, blue = take_videos
    takes = [TakeInfo(str(red), 2000.0, duration_sec=10.0), TakeInfo(str(blue), 3000.0, duration_sec=10.0)]
    beats = [3.5 + 0.5 * i for i in range(18)]
    plan_a = compute_multitake_plan(takes, beats, order_mode="random", seed=42)
    plan_b = compute_multitake_plan(takes, beats, order_mode="random", seed=42)
    assert [s.take_index for s in plan_a] == [s.take_index for s in plan_b]


def test_render_multitake_cut_produces_valid_video(tmp_path, take_videos, song_path):
    red, blue = take_videos
    takes = [TakeInfo(str(red), 2000.0, duration_sec=10.0), TakeInfo(str(blue), 3000.0, duration_sec=10.0)]
    beats = [3.5 + 0.5 * i for i in range(18)]
    plan = compute_multitake_plan(takes, beats, beat_interval=2, order_mode="fixed")

    out = render_multitake_cut(takes, song_path, plan, tmp_path / "cut.mp4")
    assert out.exists()

    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height",
         "-show_entries", "format=duration", "-of", "default=noprint_wrappers=0", str(out)],
        check=True, capture_output=True, text=True,
    )
    assert "1080" in probe.stdout and "1920" in probe.stdout
    expected_duration = plan[-1].song_end - plan[0].song_start
    duration_line = [l for l in probe.stdout.splitlines() if l.startswith("duration=")][-1]
    actual_duration = float(duration_line.split("=")[1])
    assert actual_duration == pytest.approx(expected_duration, abs=0.3)
