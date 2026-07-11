"""Schritt 05 (Phase 2): Wort-Zeitstempel -> ASS-Untertiteldatei, dann einbrennen.

Baut aus den (ggf. vom Nutzer korrigierten) Woertern aus transcribe.py
Untertitelzeilen und schreibt eine ASS-Datei. Optional im TikTok-typischen
Karaoke-Stil (aktuelles Wort farblich hervorgehoben).

Wird auf Woertern aufgerufen, deren Zeitstempel bereits im Zeitrahmen des
FERTIGEN (synchronisierten) Videos liegen - siehe transcribe.py. Es ist daher
keine zusaetzliche Offset-Verrechnung noetig.
"""
from __future__ import annotations

import argparse
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

from backend.pipeline.transcribe import Word

DEFAULT_MAX_CHARS = 40
DEFAULT_MAX_LINE_DURATION = 2.8
DEFAULT_MAX_PAUSE = 0.6

PRIMARY_COLOR_ASS = "&H00FFFFFF"  # weiss
HIGHLIGHT_COLOR_ASS = "&H0000FFFF"  # gelb (BGR-Reihenfolge in ASS)


@dataclass
class SubtitleLine:
    words: list[Word]

    @property
    def start(self) -> float:
        return self.words[0].start

    @property
    def end(self) -> float:
        return self.words[-1].end

    @property
    def text(self) -> str:
        return " ".join(w.word for w in self.words)


def group_words_into_lines(
    words: list[Word],
    max_chars: int = DEFAULT_MAX_CHARS,
    max_line_duration: float = DEFAULT_MAX_LINE_DURATION,
    max_pause: float = DEFAULT_MAX_PAUSE,
) -> list[SubtitleLine]:
    """Gruppiert Woerter zu Untertitelzeilen (Zeilenumbruch bei Sprechpause,
    zu langer Zeilendauer oder zu vielen Zeichen)."""
    lines: list[SubtitleLine] = []
    current: list[Word] = []
    current_chars = 0

    for w in words:
        if current:
            gap = w.start - current[-1].end
            projected_duration = w.end - current[0].start
            projected_chars = current_chars + 1 + len(w.word)
            if gap > max_pause or projected_duration > max_line_duration or projected_chars > max_chars:
                lines.append(SubtitleLine(words=current))
                current = []
                current_chars = 0
        current.append(w)
        current_chars += len(w.word) + (1 if len(current) > 1 else 0)

    if current:
        lines.append(SubtitleLine(words=current))
    return lines


def _format_ass_time(seconds: float) -> str:
    seconds = max(seconds, 0.0)
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    return f"{hours}:{minutes:02d}:{secs:05.2f}"


def _escape_ass_text(text: str) -> str:
    return text.replace("{", "(").replace("}", ")").replace("\\", "").replace("\n", " ")


def _ass_header(video_width: int, video_height: int, font_size: int) -> str:
    return f"""[Script Info]
Title: HOOKCUT Untertitel
ScriptType: v4.00+
PlayResX: {video_width}
PlayResY: {video_height}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial Black,{font_size},{PRIMARY_COLOR_ASS},&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,3,1,2,60,60,140,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def write_ass(
    lines: list[SubtitleLine],
    out_path: str | Path,
    video_width: int = 1080,
    video_height: int = 1920,
    font_size: int = 64,
    karaoke: bool = False,
) -> Path:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    events: list[str] = []
    for line in lines:
        if not karaoke:
            text = _escape_ass_text(line.text)
            events.append(
                f"Dialogue: 0,{_format_ass_time(line.start)},{_format_ass_time(line.end)},Default,,0,0,0,,{text}"
            )
            continue

        # Karaoke-Stil: pro Wort ein eigenes Dialogue-Event, das aktuelle
        # Wort farblich hervorgehoben, Rest der Zeile normal.
        for i, active_word in enumerate(line.words):
            parts = []
            for j, w in enumerate(line.words):
                token = _escape_ass_text(w.word)
                if j == i:
                    parts.append(f"{{\\c{HIGHLIGHT_COLOR_ASS}&}}{token}{{\\c{PRIMARY_COLOR_ASS}&}}")
                else:
                    parts.append(token)
            text = " ".join(parts)
            events.append(
                f"Dialogue: 0,{_format_ass_time(active_word.start)},{_format_ass_time(active_word.end)},"
                f"Default,,0,0,0,,{text}"
            )

    content = _ass_header(video_width, video_height, font_size) + "\n".join(events) + "\n"
    out_path.write_text(content, encoding="utf-8")
    return out_path


def _escape_ffmpeg_filter_value(value: str) -> str:
    # Escaping fuer WERTE innerhalb eines ffmpeg-Filtergraphen (':' trennt
    # Optionen, '\' ist Escape-Zeichen, ''' begrenzt Strings).
    return value.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")


def burn_subtitles(
    video_path: str | Path,
    ass_path: str | Path,
    out_path: str | Path,
    crf: int = 19,
) -> Path:
    # Windows-Pfade (C:\...) lassen sich nicht zuverlaessig fuer den
    # ass=-Filter escapen - der Laufwerks-Doppelpunkt wird trotz Escape als
    # Options-Trenner geparst (ffmpeg haelt den Rest dann fuer die Option
    # "original_size"). Statt Escaping-Akrobatik: ffmpeg im Ordner der
    # ASS-Datei starten und nur den Dateinamen referenzieren. Alle anderen
    # Pfade werden dafuer absolut aufgeloest.
    video_path = Path(video_path).resolve()
    ass_path = Path(ass_path).resolve()
    out_path = Path(out_path).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    escaped_ass = _escape_ffmpeg_filter_value(ass_path.name)
    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-vf", f"ass={escaped_ass}",
        "-c:v", "libx264", "-preset", "medium", "-crf", str(crf), "-pix_fmt", "yuv420p",
        "-c:a", "copy",
        "-movflags", "+faststart",
        str(out_path),
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True, cwd=ass_path.parent)
    return out_path


def _main() -> None:
    parser = argparse.ArgumentParser(description="Wort-Zeitstempel (JSON) -> ASS, optional direkt einbrennen")
    parser.add_argument("words_json", help="JSON-Datei mit Woertern (wie transcribe.py --json ausgibt)")
    parser.add_argument("out_ass")
    parser.add_argument("--karaoke", action="store_true")
    parser.add_argument("--video-width", type=int, default=1080)
    parser.add_argument("--video-height", type=int, default=1920)
    parser.add_argument("--font-size", type=int, default=64)
    parser.add_argument("--burn-into", help="Falls gesetzt: Video-Pfad, in den die Untertitel direkt eingebrannt werden")
    parser.add_argument("--burn-out", help="Ausgabepfad fuer das Video mit eingebrannten Untertiteln")
    args = parser.parse_args()

    raw_words = json.loads(Path(args.words_json).read_text(encoding="utf-8"))
    words = [Word(**w) for w in raw_words]
    lines = group_words_into_lines(words)
    write_ass(lines, args.out_ass, args.video_width, args.video_height, args.font_size, args.karaoke)
    print(f"ASS geschrieben: {args.out_ass} ({len(lines)} Zeilen)")

    if args.burn_into:
        if not args.burn_out:
            raise SystemExit("--burn-out ist erforderlich, wenn --burn-into gesetzt ist")
        try:
            out = burn_subtitles(args.burn_into, args.out_ass, args.burn_out)
        except subprocess.CalledProcessError as e:
            print(f"ffmpeg fehlgeschlagen:\n{e.stderr}")
            raise SystemExit(1)
        print(f"Video mit Untertiteln: {out}")


if __name__ == "__main__":
    _main()
