"""Tests fuer die Editing-Presets (presets.py).

Rendert jedes Preset auf einem kurzen synthetischen Testvideo (ffmpeg lavfi)
und prueft, dass ein gueltiges Video herauskommt - damit ein kaputter
ffmpeg-Filterstring in einem Preset sofort auffaellt und nicht erst beim
Nutzer.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from backend.pipeline.presets import (
    PRESETS,
    apply_preset,
    preset_catalog,
    preset_is_noop,
)


def _run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True, capture_output=True, text=True)


@pytest.fixture(scope="module")
def test_video(tmp_path_factory) -> Path:
    out = tmp_path_factory.mktemp("presetfixtures") / "test.mp4"
    _run([
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "testsrc2=size=720x1280:duration=3:rate=30",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=3",
        "-c:v", "libx264", "-preset", "ultrafast", "-c:a", "aac", "-shortest",
        str(out),
    ])
    return out


def test_mindestens_zehn_presets():
    assert len(PRESETS) >= 10


def test_catalog_matches_presets_and_has_texts():
    catalog = preset_catalog()
    assert [c["id"] for c in catalog] == list(PRESETS)
    for c in catalog:
        assert c["label"] and c["description"]


def test_clean_ist_noop_andere_nicht():
    assert preset_is_noop("clean")
    # Jedes andere Preset muss sichtbar etwas tun - sonst ist es sinnlos.
    for pid in PRESETS:
        if pid != "clean":
            assert not preset_is_noop(pid), f"Preset '{pid}' veraendert nichts"


def test_unbekanntes_preset_raises(tmp_path, test_video):
    with pytest.raises(ValueError):
        apply_preset(test_video, [], tmp_path / "out.mp4", "does-not-exist")


def test_beat_stride_werte_sind_sinnvoll():
    for p in PRESETS.values():
        assert p.beat_stride in (1, 2, 4), f"Preset '{p.id}': beat_stride {p.beat_stride}"


@pytest.mark.parametrize("preset_id", list(PRESETS))
def test_jedes_preset_rendert_gueltiges_video(tmp_path, test_video, preset_id):
    beat_times = [0.5, 1.0, 1.5, 2.0, 2.5]
    out = apply_preset(test_video, beat_times, tmp_path / f"{preset_id}.mp4", preset_id)
    assert out.exists()
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "stream=width,height",
         "-of", "csv=p=0", str(out)],
        check=True, capture_output=True, text=True,
    )
    assert "720" in probe.stdout and "1280" in probe.stdout
