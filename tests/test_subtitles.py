"""Tests fuer die Untertitel-Pipeline (Phase 2): Zeilen-Gruppierung, ASS-Erzeugung,
Karaoke-Stil und das Einbrennen per ffmpeg. Nutzt simulierte Wort-Zeitstempel
statt echter faster-whisper-Transkription, damit die Tests ohne Modell-Download
laufen (transcribe.py selbst ist nur ein duenner Wrapper um faster-whisper und
wird hier bewusst nicht erneut getestet).
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from backend.pipeline.subtitles import (
    SubtitleLine,
    burn_subtitles,
    group_words_into_lines,
    write_ass,
)
from backend.pipeline.transcribe import Word


def _run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True, capture_output=True, text=True)


SAMPLE_WORDS = [
    Word("Yo", 0.10, 0.35), Word("check", 0.35, 0.65), Word("die", 0.65, 0.80), Word("Stimme", 0.80, 1.25),
    Word("ist", 1.25, 1.40), Word("tief", 1.40, 1.80),
    Word("und", 2.60, 2.75), Word("markant", 2.75, 3.40),
    Word("so", 4.50, 4.65), Word("geht", 4.65, 4.90), Word("die", 4.90, 5.05),
    Word("Nummer", 5.05, 5.60), Word("weiter", 5.60, 6.10),
]


def test_group_words_breaks_on_pause():
    lines = group_words_into_lines(SAMPLE_WORDS, max_pause=0.6)
    # Pausen von 0.8s (nach "tief") und 1.1s (nach "markant") sollen Zeilenumbrueche erzwingen.
    assert len(lines) == 3
    assert lines[0].text == "Yo check die Stimme ist tief"
    assert lines[1].text == "und markant"
    assert lines[2].text == "so geht die Nummer weiter"
    assert lines[0].start == pytest.approx(0.10)
    assert lines[0].end == pytest.approx(1.80)


def test_group_words_breaks_on_max_chars():
    long_words = [Word(f"wort{i}", i * 1.0, i * 1.0 + 0.3) for i in range(20)]
    lines = group_words_into_lines(long_words, max_chars=20, max_pause=999, max_line_duration=999)
    assert len(lines) > 1
    assert all(len(line.text) <= 20 + len("wort19") for line in lines)


def test_group_words_breaks_on_max_duration():
    words = [Word(f"w{i}", i * 0.5, i * 0.5 + 0.3) for i in range(10)]
    lines = group_words_into_lines(words, max_line_duration=1.0, max_pause=999, max_chars=9999)
    assert len(lines) > 1
    assert all((line.end - line.start) <= 1.0 + 0.5 for line in lines)


def test_write_ass_plain_contains_expected_structure(tmp_path):
    lines = group_words_into_lines(SAMPLE_WORDS)
    out = write_ass(lines, tmp_path / "out.ass", karaoke=False)
    content = out.read_text(encoding="utf-8")

    assert "[Script Info]" in content
    assert "[V4+ Styles]" in content
    assert "[Events]" in content
    assert content.count("Dialogue:") == len(lines)
    assert "Yo check die Stimme ist tief" in content
    # Kein Karaoke-Markup im Plain-Modus.
    assert "\\c&H0000FFFF&" not in content


def test_write_ass_karaoke_highlights_each_word(tmp_path):
    lines = group_words_into_lines(SAMPLE_WORDS)
    out = write_ass(lines, tmp_path / "out.ass", karaoke=True)
    content = out.read_text(encoding="utf-8")

    # Ein Dialogue-Event pro Wort ueber alle Zeilen hinweg.
    assert content.count("Dialogue:") == len(SAMPLE_WORDS)
    # Hervorhebungsfarbe kommt vor, und wird nach jedem Wort wieder zurueckgesetzt.
    assert content.count("\\c&H0000FFFF&") == len(SAMPLE_WORDS)
    assert content.count("\\c&H00FFFFFF&") == len(SAMPLE_WORDS)


def test_write_ass_escapes_curly_braces(tmp_path):
    words = [Word("{böse}", 0.0, 0.5)]
    lines = [SubtitleLine(words=words)]
    out = write_ass(lines, tmp_path / "out.ass")
    content = out.read_text(encoding="utf-8")
    assert "{böse}" not in content
    assert "(böse)" in content


def test_burn_subtitles_produces_valid_video(tmp_path):
    video = tmp_path / "test.mp4"
    _run([
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "testsrc2=size=720x1280:duration=3:rate=30",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=3",
        "-c:v", "libx264", "-preset", "ultrafast", "-c:a", "aac", "-shortest",
        str(video),
    ])

    words = [Word("test", 0.2, 0.8), Word("untertitel", 0.8, 1.5)]
    lines = group_words_into_lines(words)
    ass_path = write_ass(lines, tmp_path / "subs.ass")

    out_video = tmp_path / "out.mp4"
    burn_subtitles(video, ass_path, out_video)

    assert out_video.exists()
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height",
         "-of", "csv=p=0", str(out_video)],
        check=True, capture_output=True, text=True,
    )
    assert "720" in probe.stdout and "1280" in probe.stdout
