"""Schritt 03: Songspur synchron ueber das Video legen und im 9:16-Format exportieren.

Nimmt den in sync_offset.py berechneten offset_ms entgegen (siehe Vorzeichen-
Konvention dort) und baut daraus einen ffmpeg filter_complex-Aufruf:

- offset_ms >= 0: Song wird um offset_ms beschnitten (atrim), damit sein Anfang
  auf den Video-Start faellt.
- offset_ms <  0: Song wird um |offset_ms| verzoegert (adelay), da das Video vor
  dem Songbeginn startet.

Die Ausgabe wird immer auf die Videolaenge begrenzt (-shortest), der Song wird
vorher mit Stille aufgefuellt (apad), damit er nie die limitierende Spur ist.
"""
from __future__ import annotations

import argparse
import subprocess
from pathlib import Path
from typing import Literal

OriginalAudioMode = Literal["mute", "background"]


def _probe_duration_sec(path: Path) -> float:
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(path),
    ]
    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    return float(result.stdout.strip())


def render_synced_video(
    video_path: str | Path,
    song_path: str | Path,
    offset_ms: float,
    out_path: str | Path,
    original_audio_mode: OriginalAudioMode = "mute",
    original_audio_gain_db: float = -20.0,
    target_width: int = 1080,
    target_height: int = 1920,
    crf: int = 19,
    audio_bitrate: str = "192k",
) -> Path:
    video_path = Path(video_path)
    song_path = Path(song_path)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Video-Dauer wird gebraucht, um den Song-Pad-Filter (apad) auf ein festes
    # Ende zu begrenzen. Ein unbegrenztes apad kombiniert mit -shortest hat sich
    # in Tests als unzuverlaessig erwiesen (ffmpeg bricht mit einem fehlerhaften
    # "No space left on device" ab, obwohl echter Speicherplatz vorhanden ist).
    video_duration_sec = _probe_duration_sec(video_path)

    video_filter = (
        f"[0:v]scale={target_width}:{target_height}:force_original_aspect_ratio=decrease,"
        f"pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2,setsar=1[vout]"
    )

    if offset_ms >= 0:
        start_sec = offset_ms / 1000.0
        song_chain = f"[1:a]atrim=start={start_sec:.6f},asetpts=PTS-STARTPTS[songsync]"
    else:
        delay_ms = int(round(-offset_ms))
        song_chain = f"[1:a]adelay=delays={delay_ms}:all=1[songsync]"

    pad_dur_sec = video_duration_sec + 0.5  # kleine Reserve gegen Rundungsfehler
    filters = [video_filter, song_chain, f"[songsync]apad=whole_dur={pad_dur_sec:.6f}[songpad]"]
    audio_out_label = "songpad"

    if original_audio_mode == "background":
        filters.append(f"[0:a]volume={original_audio_gain_db}dB[origvol]")
        filters.append("[songpad][origvol]amix=inputs=2:duration=first:dropout_transition=0[aout]")
        audio_out_label = "aout"
    elif original_audio_mode != "mute":
        raise ValueError(f"Unbekannter original_audio_mode: {original_audio_mode}")

    filter_complex = ";".join(filters)

    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-i", str(song_path),
        "-filter_complex", filter_complex,
        "-map", "[vout]",
        "-map", f"[{audio_out_label}]",
        "-c:v", "libx264", "-preset", "medium", "-crf", str(crf), "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", audio_bitrate,
        "-shortest",
        "-movflags", "+faststart",
        str(out_path),
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True)
    return out_path


def _main() -> None:
    parser = argparse.ArgumentParser(description="Song synchron ueber Video legen, 9:16 exportieren")
    parser.add_argument("video_path")
    parser.add_argument("song_path")
    parser.add_argument("offset_ms", type=float)
    parser.add_argument("out_path")
    parser.add_argument("--original-audio-mode", choices=["mute", "background"], default="mute")
    parser.add_argument("--original-audio-gain-db", type=float, default=-20.0)
    parser.add_argument("--target-width", type=int, default=1080)
    parser.add_argument("--target-height", type=int, default=1920)
    parser.add_argument("--crf", type=int, default=19)
    parser.add_argument("--audio-bitrate", default="192k")
    args = parser.parse_args()

    try:
        out = render_synced_video(
            args.video_path, args.song_path, args.offset_ms, args.out_path,
            original_audio_mode=args.original_audio_mode,
            original_audio_gain_db=args.original_audio_gain_db,
            target_width=args.target_width, target_height=args.target_height,
            crf=args.crf, audio_bitrate=args.audio_bitrate,
        )
    except subprocess.CalledProcessError as e:
        print(f"ffmpeg fehlgeschlagen:\n{e.stderr}")
        raise SystemExit(1)
    print(f"Export fertig: {out}")


if __name__ == "__main__":
    _main()
