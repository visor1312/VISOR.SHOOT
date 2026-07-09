"""End-to-End-Test der Phase-1-Pipeline mit synthetisch erzeugten Video-/Audiodateien.

Erzeugt per ffmpeg eine "Song"-Datei (breitbandiges Rauschen, damit die
Cross-Correlation nicht durch Periodizitaet gestoert wird - reine Sinustoene
sind dafuer ein Anti-Testfall) sowie zwei "Video-Takes" mit bekanntem,
absichtlich eingebautem Zeitversatz (einmal positiv, einmal negativ) und
prueft, ob sync_offset.py diesen Versatz korrekt erkennt und render_sync.py
ein gueltiges 9:16 H.264-Video produziert.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from backend.pipeline.extract_audio import extract_audio
from backend.pipeline.render_sync import render_synced_video
from backend.pipeline.sync_offset import compute_offset


def _run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True, capture_output=True, text=True)


@pytest.fixture(scope="module")
def song(tmp_path_factory) -> Path:
    out = tmp_path_factory.mktemp("fixtures") / "song.wav"
    _run([
        "ffmpeg", "-y", "-f", "lavfi",
        "-i", "anoisesrc=color=pink:duration=15:sample_rate=44100:amplitude=0.6",
        "-af", "aformat=channel_layouts=stereo",
        str(out),
    ])
    return out


def _make_take(song: Path, out_dir: Path, name: str, pre_silence_sec: float, song_start_sec: float, clip_len_sec: float) -> Path:
    """Baut einen Test-Take: `pre_silence_sec` Sekunden Stille/Rauschen, danach
    ein Ausschnitt des Songs ab `song_start_sec` fuer `clip_len_sec` Sekunden,
    (leicht degradiert, wie ein Handymikro), gemuxt mit einem Test-Videobild.

    Erwarteter offset_ms = song_start_sec*1000 - pre_silence_sec*1000.
    """
    audio_part = out_dir / f"{name}_audio_part.wav"
    _run([
        "ffmpeg", "-y", "-i", str(song),
        "-ss", str(song_start_sec), "-t", str(clip_len_sec),
        "-af", "highpass=f=300,lowpass=f=3000,volume=0.8",
        str(audio_part),
    ])

    full_audio = out_dir / f"{name}_audio.wav"
    if pre_silence_sec > 0:
        _run([
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", f"anoisesrc=color=white:duration={pre_silence_sec}:sample_rate=44100:amplitude=0.02",
            "-i", str(audio_part),
            "-filter_complex", "[0:a][1:a]concat=n=2:v=0:a=1[a]",
            "-map", "[a]", str(full_audio),
        ])
    else:
        full_audio = audio_part

    total_dur = pre_silence_sec + clip_len_sec
    video_path = out_dir / f"{name}.mp4"
    _run([
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"testsrc2=size=720x1280:duration={total_dur}:rate=30",
        "-i", str(full_audio),
        "-map", "0:v", "-map", "1:a",
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23", "-c:a", "aac", "-shortest",
        str(video_path),
    ])
    return video_path


@pytest.mark.parametrize(
    "pre_silence_sec,song_start_sec,clip_len_sec,expected_offset_ms",
    [
        (0.0, 4.2, 6.0, 4200.0),   # Kamera startet zeitgleich mit Aufnahmebeginn, Song lag schon 4.2s
        (0.8, 0.0, 5.0, -800.0),   # Kamera startet 0.8s bevor der Song einsetzt
    ],
)
def test_sync_offset_detection(tmp_path, song, pre_silence_sec, song_start_sec, clip_len_sec, expected_offset_ms):
    take_video = _make_take(song, tmp_path, "take", pre_silence_sec, song_start_sec, clip_len_sec)
    take_audio = tmp_path / "take_audio_extracted.wav"

    extract_audio(take_video, take_audio)
    result = compute_offset(song, take_audio)

    assert result.offset_ms == pytest.approx(expected_offset_ms, abs=5.0)
    assert result.confidence > 0.1


def test_render_synced_video_produces_valid_9x16_output(tmp_path, song):
    take_video = _make_take(song, tmp_path, "take", pre_silence_sec=0.0, song_start_sec=4.2, clip_len_sec=6.0)
    take_audio = tmp_path / "take_audio_extracted.wav"
    extract_audio(take_video, take_audio)
    result = compute_offset(song, take_audio)

    out_path = tmp_path / "synced_output.mp4"
    render_synced_video(take_video, song, result.offset_ms, out_path)

    assert out_path.exists()
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height",
         "-of", "csv=p=0", str(out_path)],
        check=True, capture_output=True, text=True,
    )
    assert "1080" in probe.stdout and "1920" in probe.stdout

    # Rendertes Ergebnis muss inhaltlich exakt am erkannten Offset ausgerichtet sein.
    rendered_audio = tmp_path / "rendered_audio.wav"
    extract_audio(out_path, rendered_audio)
    check = compute_offset(song, rendered_audio)
    assert check.offset_ms == pytest.approx(result.offset_ms, abs=5.0)
    assert check.confidence > 0.9
