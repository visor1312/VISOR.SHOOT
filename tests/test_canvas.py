"""Tests fuer den Spotify-Canvas-Generator.

Reine Fenster-Logik + Dauer-Clamp direkt; API wie die Edit-/Pack-Tests mit
Junk-Dateien (Analyse schlaegt fehl -> Status 'error') + Ownership. Der
Ton-Strip (ffmpeg -an) wird an einer echten Mini-MP4 geprueft - ffmpeg ist da,
nur der eigentliche Chrome-Render laeuft nur beim Nutzer.
"""
from __future__ import annotations

import subprocess

from backend.pipeline.content_pack import (
    CANVAS_MAX_SEC,
    CANVAS_MIN_SEC,
    canvas_window,
    clamp_canvas_duration,
)


# --- Fenster-Logik --------------------------------------------------------

def test_clamp_canvas_duration():
    assert clamp_canvas_duration(1) == CANVAS_MIN_SEC
    assert clamp_canvas_duration(100) == CANVAS_MAX_SEC
    assert clamp_canvas_duration(6) == 6


def test_canvas_window_at_hook():
    # offset 2s: Song-Zeit 10 liegt bei Video 8. Video 30s lang, 6s Fenster passt.
    win = canvas_window(hook_start_sec=10.0, offset_sec=2.0, video_dur=30.0, duration_sec=6.0)
    assert win is not None
    assert round(win.end_sec - win.start_sec, 3) == 6.0
    assert win.start_sec == 10.0  # bleibt am Hook


def test_canvas_window_shifts_back_when_overrunning():
    # Hook nahe Videoende: Fenster wird nach vorn geschoben, damit es passt.
    win = canvas_window(hook_start_sec=28.0, offset_sec=0.0, video_dur=30.0, duration_sec=6.0)
    assert win is not None
    assert win.end_sec <= 30.0 + 1e-6
    assert round(win.end_sec - win.start_sec, 3) == 6.0


def test_canvas_window_none_when_video_too_short():
    assert canvas_window(0.0, 0.0, video_dur=2.0, duration_sec=6.0) is None


def test_canvas_window_clamps_duration():
    win = canvas_window(0.0, 0.0, video_dur=30.0, duration_sec=100.0)
    assert win is not None
    assert round(win.end_sec - win.start_sec, 3) == CANVAS_MAX_SEC


# --- ffmpeg Ton-Strip (echt) ----------------------------------------------

def test_ffmpeg_strips_audio(tmp_path):
    """Bestaetigt, dass der Ton-Strip-Schritt aus _run_canvas_job (ffmpeg -an)
    eine tonlose MP4 erzeugt."""
    with_audio = tmp_path / "with_audio.mp4"
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc=size=64x64:rate=10:duration=1",
         "-f", "lavfi", "-i", "sine=frequency=440:duration=1",
         "-c:v", "libx264", "-preset", "ultrafast", "-c:a", "aac", "-shortest",
         str(with_audio)],
        check=True, capture_output=True)
    # Ausgangsdatei hat eine Tonspur
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries",
         "stream=codec_type", "-of", "csv=p=0", str(with_audio)],
        check=True, capture_output=True, text=True)
    assert "audio" in probe.stdout

    silent = tmp_path / "silent.mp4"
    subprocess.run(["ffmpeg", "-y", "-i", str(with_audio), "-c", "copy", "-an", str(silent)],
                   check=True, capture_output=True)
    probe2 = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries",
         "stream=codec_type", "-of", "csv=p=0", str(silent)],
        check=True, capture_output=True, text=True)
    assert probe2.stdout.strip() == ""  # keine Tonspur mehr


# --- API ------------------------------------------------------------------

def test_canvas_requires_login(client):
    assert client.get("/canvas").status_code == 401
    assert client.get("/canvas/nope").status_code == 401
    assert client.get("/canvas/nope/download").status_code == 401


def test_create_canvas_clamps_duration_and_errors_on_junk(auth_client):
    r = auth_client.post("/canvas",
                         files={"video": ("v.mp4", b"junk", "video/mp4"),
                                "song": ("s.wav", b"junk", "audio/wav")},
                         data={"style": "vibrant", "duration_sec": "99", "use_hook": "true"})
    assert r.status_code == 200
    body = r.json()
    assert body["duration_sec"] == CANVAS_MAX_SEC  # 99 -> auf 8s geklemmt
    cid = body["canvas_id"]
    detail = auth_client.get(f"/canvas/{cid}").json()
    assert detail["status"] == "error" and detail["error"]  # Junk -> Analyse-Fehler
    assert detail["style"] == "vibrant"
    assert any(c["canvas_id"] == cid for c in auth_client.get("/canvas").json())


def test_canvas_ownership_isolation(auth_client, second_auth_client):
    r = auth_client.post("/canvas",
                         files={"video": ("v.mp4", b"junk", "video/mp4"),
                                "song": ("s.wav", b"junk", "audio/wav")},
                         data={"style": "clean"})
    cid = r.json()["canvas_id"]
    assert second_auth_client.get(f"/canvas/{cid}").status_code == 404
    assert second_auth_client.get(f"/canvas/{cid}/download").status_code == 404
    assert all(c["canvas_id"] != cid for c in second_auth_client.get("/canvas").json())


def test_invalid_style_falls_back_to_clean(auth_client):
    r = auth_client.post("/canvas",
                         files={"video": ("v.mp4", b"junk", "video/mp4"),
                                "song": ("s.wav", b"junk", "audio/wav")},
                         data={"style": "gibtsnicht"})
    assert r.status_code == 200
    assert auth_client.get(f"/canvas/{r.json()['canvas_id']}").json()["style"] == "clean"
