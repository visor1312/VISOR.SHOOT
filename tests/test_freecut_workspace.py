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


@pytest.fixture(scope="module")
def beat_song(tmp_path_factory) -> Path:
    """6s Klick-Track (120 BPM) als Song, damit Beats erkennbar sind."""
    sr = 22050
    rng = np.random.default_rng(7)
    audio = rng.normal(scale=0.05, size=int(6 * sr))
    decay_env = np.exp(-np.linspace(0, 15, int(0.1 * sr)))
    t = 0.5
    while t < 5.9:
        start = int(t * sr)
        audio[start:start + len(decay_env)] += decay_env
        t += 0.5
    audio = audio / np.max(np.abs(audio)) * 0.9
    out = tmp_path_factory.mktemp("wsbeats") / "beat_song.wav"
    sf.write(str(out), audio, sr)
    return out


# Params aus editor/src/infrastructure/gpu-effects verifiziert (index.test.ts).
TRIGGER_WAVE_PARAM_KEYS = {
    "strength", "radius", "frequency", "decay", "phase", "speed",
    "centerX", "centerY", "chroma", "scanlineMix", "glowColor",
}


def test_beat_effects_add_trigger_wave_with_audio_pulse(media, beat_song, tmp_path):
    video, _song = media
    ws = tmp_path / "ws"
    build_workspace(ws, video, beat_song, offset_ms=0.0, style_key="hype",
                    beat_effects=True)
    project = _load_project(ws)
    v = next(i for i in project["timeline"]["items"] if i["type"] == "video")

    wave = next(e for e in v["effects"]
                if e["effect"]["gpuEffectType"] == "gpu-trigger-wave")
    # Style-Effekte bleiben davor erhalten, Pulse-Effekt kommt obendrauf.
    assert [e["effect"]["gpuEffectType"] for e in v["effects"][:-1]] \
        == [gpu for gpu, _ in get_style("hype").effects]
    assert set(wave["effect"]["params"].keys()) == TRIGGER_WAVE_PARAM_KEYS
    assert wave["effect"]["params"]["strength"] == 0  # Ruhe-Zustand: unsichtbar

    pulse = wave["audioPulse"]
    assert pulse["enabled"] is True
    assert pulse["beats"], "Klick-Track muss Beats liefern"
    max_frame = v["durationInFrames"] - 1
    for b in pulse["beats"]:
        assert 0 <= b["frame"] <= max_frame
        assert 0.0 <= b["amplitude"] <= 1.0
    assert 2 <= pulse["durationFrames"] <= max_frame
    assert pulse["strength"] > 0 and pulse["chroma"] > 0
    assert pulse["glowColorBase"] == 0x2E6B8C


def test_beat_effects_with_silent_song_add_nothing(media, tmp_path):
    video, song = media  # song = Stille -> keine Beats
    ws = tmp_path / "ws"
    build_workspace(ws, video, song, offset_ms=0.0, style_key="clean",
                    beat_effects=True)
    project = _load_project(ws)
    v = next(i for i in project["timeline"]["items"] if i["type"] == "video")
    assert all(e["effect"]["gpuEffectType"] != "gpu-trigger-wave" for e in v["effects"])


def test_beat_effects_respect_hook_window(media, beat_song, tmp_path):
    video, _song = media
    ws = tmp_path / "ws"
    # Hook 2..5s: Beats ausserhalb des Fensters duerfen nicht auftauchen.
    build_workspace(ws, video, beat_song, offset_ms=1000.0,
                    hook_start_sec=2.0, hook_end_sec=5.0, beat_effects=True)
    project = _load_project(ws)
    v = next(i for i in project["timeline"]["items"] if i["type"] == "video")
    wave = next(e for e in v["effects"]
                if e["effect"]["gpuEffectType"] == "gpu-trigger-wave")
    assert v["durationInFrames"] == 90
    assert all(0 <= b["frame"] <= 89 for b in wave["audioPulse"]["beats"])


def test_all_styles_have_valid_effect_shape():
    for style in STYLES.values():
        for gpu_type, params in style.effects:
            assert gpu_type.startswith("gpu-")
            assert isinstance(params, dict)
