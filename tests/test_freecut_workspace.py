"""Tests fuer den render-fertigen FreeCut-Workspace-Generator (All-in-One).

Prueft die reine Aufbau-Logik (Frame-Mathematik, Datei-Layout, Style-Effekte)
mit einem kurzen synthetischen Video+Song - der eigentliche Chrome-Render
(node headless/render.mjs) laeuft nur beim Nutzer.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from backend.pipeline.freecut_workspace import SubtitleCue, build_workspace
from backend.pipeline.styles import STYLES, get_style


@pytest.fixture(scope="module")
def media(tmp_path_factory) -> tuple[Path, Path]:
    d = tmp_path_factory.mktemp("wsmedia")
    sr = 22050
    song = d / "song.wav"
    sf.write(str(song), np.zeros(int(6 * sr)), sr)  # 6s Stille reicht als Song

    # 4s stummes Testvideo via ffmpeg (Farbbalken).
    video = d / "video.mp4"
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc=size=1080x1920:rate=30:duration=4",
         "-pix_fmt", "yuv420p", str(video)],
        check=True, capture_output=True,
    )
    return video, song


def _load_project(ws: Path) -> dict:
    pj = next(ws.glob("projects/*/project.json"))
    return json.loads(pj.read_text(encoding="utf-8"))


def test_workspace_layout_and_frames(media, tmp_path):
    video, song = media
    ws = tmp_path / "ws"
    info = build_workspace(ws, video, song, offset_ms=1000.0,
                           hook_start_sec=2.0, hook_end_sec=5.0, style_key="vibrant")

    # Layout, das headless/render.mjs erwartet.
    assert (ws / "projects" / info["project_id"] / "project.json").exists()
    media_dirs = list((ws / "media").iterdir())
    assert len(media_dirs) == 2
    for md in media_dirs:
        assert (md / "metadata.json").exists()
        # genau eine Quelldatei neben der metadata.json
        assert any(f.name != "metadata.json" for f in md.iterdir())

    project = _load_project(ws)
    assert project["metadata"] == {"width": 1080, "height": 1920, "fps": 30, "backgroundColor": "#000000"}
    v = next(i for i in project["timeline"]["items"] if i["type"] == "video")
    a = next(i for i in project["timeline"]["items"] if i["type"] == "audio")

    # Hook 2..5s => 3s * 30fps = 90 Frames; beide Clips gleich lang, from=0.
    assert v["durationInFrames"] == 90 and a["durationInFrames"] == 90
    assert v["from"] == 0 and a["from"] == 0
    # Song-Start = Hook-Start 2.0s -> Frame 60; Video-Start = 2.0 - 1.0(offset) = 1.0s -> Frame 30.
    assert a["sourceStart"] == 60
    assert v["sourceStart"] == 30
    # Video stumm.
    assert v["volume"] == -60 and v["embeddedAudioMuted"] is True


def test_style_effects_attached(media, tmp_path):
    video, song = media
    ws = tmp_path / "ws"
    build_workspace(ws, video, song, offset_ms=0.0, style_key="cinematic")
    project = _load_project(ws)
    v = next(i for i in project["timeline"]["items"] if i["type"] == "video")

    got = [e["effect"]["gpuEffectType"] for e in v["effects"]]
    expected = [gpu for gpu, _ in get_style("cinematic").effects]
    assert got == expected
    for eff in v["effects"]:
        assert eff["effect"]["type"] == "gpu-effect"
        assert eff["enabled"] is True


def test_no_hook_uses_full_filmed_window(media, tmp_path):
    video, song = media  # Video 4s, Song 6s
    ws = tmp_path / "ws"
    # offset 1s, kein Hook -> Fenster = [1.0 .. min(6, 1+4)=5.0] = 4s.
    build_workspace(ws, video, song, offset_ms=1000.0, style_key="clean")
    project = _load_project(ws)
    a = next(i for i in project["timeline"]["items"] if i["type"] == "audio")
    assert a["durationInFrames"] == 120  # 4s * 30


def test_subtitles_become_segment_with_relative_cues(media, tmp_path):
    video, song = media
    ws = tmp_path / "ws"
    cues = [SubtitleCue(2.5, 3.5, "Zeile eins"), SubtitleCue(10.0, 11.0, "ausserhalb")]
    build_workspace(ws, video, song, offset_ms=0.0,
                    hook_start_sec=2.0, hook_end_sec=5.0, subtitle_cues=cues)
    project = _load_project(ws)
    sub = next((i for i in project["timeline"]["items"] if i["type"] == "subtitle"), None)
    assert sub is not None
    # Nur die Cue im Fenster; Zeit relativ zum Fenster-Start (2.5 - 2.0 = 0.5).
    assert len(sub["cues"]) == 1
    assert sub["cues"][0]["startSeconds"] == pytest.approx(0.5)
    assert sub["cues"][0]["text"] == "Zeile eins"


def test_all_styles_have_valid_effect_shape():
    for style in STYLES.values():
        for gpu_type, params in style.effects:
            assert gpu_type.startswith("gpu-")
            assert isinstance(params, dict)
