"""Schritt 01: Ton aus einer Videodatei extrahieren.

Isolierte Funktion + CLI, testbar ohne den Rest der Pipeline.
"""
from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

DEFAULT_SAMPLE_RATE = 44100


def extract_audio(video_path: str | Path, out_wav_path: str | Path, sample_rate: int = DEFAULT_SAMPLE_RATE) -> Path:
    """Extrahiert die Audiospur eines Videos als Mono-WAV-Datei.

    Wirft subprocess.CalledProcessError, falls ffmpeg fehlschlägt (z.B. Video ohne Audiospur).
    """
    video_path = Path(video_path)
    out_wav_path = Path(out_wav_path)
    out_wav_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-vn",
        "-ac", "1",
        "-ar", str(sample_rate),
        "-acodec", "pcm_s16le",
        str(out_wav_path),
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True)
    return out_wav_path


def _main() -> None:
    parser = argparse.ArgumentParser(description="Ton aus Video extrahieren (Mono-WAV)")
    parser.add_argument("video_path", help="Pfad zur Videodatei")
    parser.add_argument("out_wav_path", help="Zielpfad für die WAV-Datei")
    parser.add_argument("--sample-rate", type=int, default=DEFAULT_SAMPLE_RATE)
    args = parser.parse_args()

    try:
        out = extract_audio(args.video_path, args.out_wav_path, args.sample_rate)
    except subprocess.CalledProcessError as e:
        print(f"ffmpeg fehlgeschlagen:\n{e.stderr}")
        raise SystemExit(1)
    print(f"Audio extrahiert: {out}")


if __name__ == "__main__":
    _main()
