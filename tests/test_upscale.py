"""Test fuer die Video-Umbau-Mechanik von upscale.py (Frame-Extraktion,
Verarbeitung, Wiederzusammenbau mit Ton/fps) - OHNE echte Real-ESRGAN-
Inferenz. Der Modell-Download (github.com Release-Asset) ist in dieser
Sandbox nicht erreichbar (Session-Scoping auf ein anderes Repo), daher wird
`_get_upsampler` durch ein einfaches cv2.resize ersetzt. Das deckt die
komplette Pipeline rund um die eigentliche Modell-Inferenz ab (die auf einer
normalen Maschine mit Internetzugang beim ersten Aufruf automatisch
heruntergeladen wird).
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import cv2
import pytest

from backend.pipeline import upscale as upscale_module


class _DummyUpsampler:
    def enhance(self, img, outscale=2):
        h, w = img.shape[:2]
        return cv2.resize(img, (int(w * outscale), int(h * outscale)), interpolation=cv2.INTER_CUBIC), None


@pytest.fixture(autouse=True)
def _patch_upsampler(monkeypatch):
    monkeypatch.setattr(upscale_module, "_get_upsampler", lambda tile=0: _DummyUpsampler())


@pytest.fixture
def tiny_video(tmp_path) -> Path:
    out = tmp_path / "tiny.mp4"
    subprocess.run([
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "testsrc2=size=320x180:duration=0.3:rate=10",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=0.3",
        "-c:v", "libx264", "-preset", "ultrafast", "-c:a", "aac", "-shortest",
        str(out),
    ], check=True, capture_output=True, text=True)
    return out


def test_upscale_video_doubles_resolution(tmp_path, tiny_video):
    out = upscale_module.upscale_video(tiny_video, tmp_path / "out.mp4", scale=2)
    assert out.exists()

    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height",
         "-show_entries", "format=duration", "-of", "default=noprint_wrappers=0", str(out)],
        check=True, capture_output=True, text=True,
    )
    assert "width=640" in probe.stdout
    assert "height=360" in probe.stdout
    assert "codec_type=audio" in probe.stdout


def test_upscale_video_preserves_duration_and_audio(tmp_path, tiny_video):
    out = upscale_module.upscale_video(tiny_video, tmp_path / "out.mp4", scale=2)
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(out)],
        check=True, capture_output=True, text=True,
    )
    assert float(probe.stdout.strip()) == pytest.approx(0.3, abs=0.15)


def test_progress_callback_invoked_per_frame(tmp_path, tiny_video):
    calls = []
    upscale_module.upscale_video(
        tiny_video, tmp_path / "out.mp4", scale=2, progress_cb=lambda done, total: calls.append((done, total)),
    )
    assert len(calls) >= 2
    assert calls[-1][0] == calls[-1][1]
