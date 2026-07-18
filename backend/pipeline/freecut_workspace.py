"""Baut einen render-fertigen FreeCut-Workspace (fuer den unsichtbaren
Hintergrund-Render der All-in-One-Pipeline).

Layout, das editor/headless/render.mjs erwartet (aus headless/lib/workspace.mjs
verifiziert):

    <workspace>/projects/<projectId>/project.json
    <workspace>/media/<mediaId>/<quelldatei>
    <workspace>/media/<mediaId>/metadata.json   (MediaMetadata)

Danach rendert:
    node editor/headless/render.mjs --workspace <ws> --project <projectId> \
        --resolution 1080x1920 --out final.mp4

Der Sync entspricht dem bereits im Editor bestaetigten Dialog:
Video-Frame 0 und Song-Frame 0 zeigen dieselbe Song-Zeit (offset_ms verrechnet).
"""
from __future__ import annotations

import json
import shutil
import subprocess
import uuid
from dataclasses import dataclass
from pathlib import Path

from backend.pipeline.styles import Style, get_style

AUDIO_CODECS_SUPPORTED = {"aac", "mp3", "mp2", "opus", "vorbis", "flac", "pcm_s16le", "pcm_s24le"}


@dataclass
class SubtitleCue:
    start_sec: float
    end_sec: float
    text: str


def _fid() -> str:
    return str(uuid.uuid4())


def _ffprobe(path: str | Path) -> dict:
    out = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams", str(path)],
        capture_output=True, text=True, check=True,
    )
    return json.loads(out.stdout)


def _media_metadata(path: Path, media_id: str) -> dict:
    """Erzeugt MediaMetadata (Untermenge), die der headless-Harness braucht."""
    probe = _ffprobe(path)
    fmt = probe.get("format", {})
    v = next((s for s in probe.get("streams", []) if s.get("codec_type") == "video"), None)
    a = next((s for s in probe.get("streams", []) if s.get("codec_type") == "audio"), None)

    duration = float(fmt.get("duration") or (v or a or {}).get("duration") or 0.0)
    fps = 30.0
    if v and v.get("r_frame_rate") and "/" in v["r_frame_rate"]:
        num, den = v["r_frame_rate"].split("/")
        if float(den) != 0:
            fps = float(num) / float(den)

    width = int(v["width"]) if v and v.get("width") else 0
    height = int(v["height"]) if v and v.get("height") else 0
    is_video = v is not None
    audio_codec = a.get("codec_name") if a else None

    return {
        "id": media_id,
        "storageType": "workspace",
        "fileName": path.name,
        "fileSize": int(fmt.get("size") or path.stat().st_size),
        "mimeType": "video/mp4" if is_video else "audio/wav",
        "duration": duration,
        "width": width,
        "height": height,
        "fps": round(fps, 3),
        "codec": (v or a or {}).get("codec_name", ""),
        "bitrate": int(float(fmt.get("bit_rate") or 0)),
        "audioCodec": audio_codec,
        "audioCodecSupported": (audio_codec in AUDIO_CODECS_SUPPORTED) if audio_codec else True,
    }


def _sec_to_frames(seconds: float, fps: float) -> int:
    return max(0, round(seconds * fps))


def _item_effects(style: Style) -> list[dict]:
    return [
        {"id": _fid(), "enabled": True,
         "effect": {"type": "gpu-effect", "gpuEffectType": gpu_type, "params": params}}
        for gpu_type, params in style.effects
    ]


def build_workspace(
    workspace_dir: str | Path,
    video_path: str | Path,
    song_path: str | Path,
    *,
    offset_ms: float,
    hook_start_sec: float | None = None,
    hook_end_sec: float | None = None,
    style_key: str = "clean",
    subtitle_cues: list[SubtitleCue] | None = None,
    width: int = 1080,
    height: int = 1920,
    fps: int = 30,
    project_name: str = "HOOKCUT Export",
) -> dict:
    """Legt einen render-fertigen Workspace an. Rueckgabe: {project_id,
    workspace_dir, render_args} - render_args ist die Argumentliste fuer
    editor/headless/render.mjs."""
    workspace_dir = Path(workspace_dir)
    video_path = Path(video_path)
    song_path = Path(song_path)
    style = get_style(style_key)

    project_id = _fid()
    video_id = _fid()
    song_id = _fid()
    offset_sec = offset_ms / 1000.0

    # Fenster im Song: Hook (wenn gegeben) oder der ganze gefilmte Bereich.
    video_meta = _media_metadata(video_path, video_id)
    song_meta = _media_metadata(song_path, song_id)
    video_dur = video_meta["duration"]
    song_dur = song_meta["duration"]
    video_fps = video_meta["fps"] or fps
    song_fps = song_meta["fps"] or fps

    if hook_start_sec is not None and hook_end_sec is not None:
        win_start, win_end = hook_start_sec, hook_end_sec
    else:
        win_start = max(0.0, offset_sec)
        win_end = min(song_dur, offset_sec + video_dur)
    win_len = max(0.1, win_end - win_start)
    duration_frames = _sec_to_frames(win_len, fps)

    video_start_sec = max(0.0, win_start - offset_sec)  # Stelle IM Video

    video_track_id = _fid()
    audio_track_id = _fid()
    subtitle_track_id = _fid()

    tracks = [
        {"id": video_track_id, "name": "V1", "kind": "video", "height": 80,
         "locked": False, "visible": True, "muted": True, "solo": False, "volume": -60, "order": 0},
        {"id": audio_track_id, "name": "A1", "kind": "audio", "height": 60,
         "locked": False, "visible": True, "muted": False, "solo": False, "volume": 0, "order": 1},
    ]

    video_item = {
        "id": _fid(), "type": "video", "trackId": video_track_id,
        "from": 0, "durationInFrames": duration_frames, "label": video_path.name,
        "mediaId": video_id, "src": f"media/{video_id}/{video_path.name}",
        "sourceStart": _sec_to_frames(video_start_sec, video_fps),
        "sourceEnd": _sec_to_frames(video_start_sec + win_len, video_fps),
        "sourceDuration": _sec_to_frames(video_dur, video_fps),
        "sourceFps": round(video_fps, 3),
        "trimStart": 0, "trimEnd": 0,
        "volume": -60, "embeddedAudioMuted": True,
        "effects": _item_effects(style),
    }
    song_item = {
        "id": _fid(), "type": "audio", "trackId": audio_track_id,
        "from": 0, "durationInFrames": duration_frames, "label": song_path.name,
        "mediaId": song_id, "src": f"media/{song_id}/{song_path.name}",
        "sourceStart": _sec_to_frames(win_start, song_fps),
        "sourceEnd": _sec_to_frames(win_start + win_len, song_fps),
        "sourceDuration": _sec_to_frames(song_dur, song_fps),
        "sourceFps": round(song_fps, 3),
        "trimStart": 0, "trimEnd": 0, "volume": 0,
    }
    items = [video_item, song_item]

    if subtitle_cues:
        rel = [
            {"id": _fid(),
             "startSeconds": max(0.0, c.start_sec - win_start),
             "endSeconds": max(0.0, c.end_sec - win_start),
             "text": c.text}
            for c in subtitle_cues
            if c.end_sec > win_start and c.start_sec < win_end
        ]
        if rel:
            tracks.append({"id": subtitle_track_id, "name": "V2", "kind": "video", "height": 60,
                           "locked": False, "visible": True, "muted": True, "solo": False, "order": -1})
            items.append({
                "id": _fid(), "type": "subtitle", "trackId": subtitle_track_id,
                "from": 0, "durationInFrames": duration_frames, "label": "Untertitel",
                "source": {"type": "transcript", "mediaId": song_id, "clipId": song_item["id"]},
                "cues": rel, "color": "#ffffff",
            })

    project = {
        "id": project_id, "name": project_name,
        "description": "Automatisch von HOOKCUT erzeugt",
        "createdAt": 0, "updatedAt": 0, "duration": duration_frames,
        "schemaVersion": 1,
        "metadata": {"width": width, "height": height, "fps": fps, "backgroundColor": "#000000"},
        "timeline": {"masterBusDb": 0, "tracks": tracks, "items": items},
    }

    # --- Auf Platte schreiben ---
    proj_dir = workspace_dir / "projects" / project_id
    proj_dir.mkdir(parents=True, exist_ok=True)
    (proj_dir / "project.json").write_text(json.dumps(project, ensure_ascii=False, indent=2), encoding="utf-8")

    for media_id, src, meta in [(video_id, video_path, video_meta), (song_id, song_path, song_meta)]:
        mdir = workspace_dir / "media" / media_id
        mdir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, mdir / src.name)
        (mdir / "metadata.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "project_id": project_id,
        "workspace_dir": str(workspace_dir),
        "render_args": ["--workspace", str(workspace_dir), "--project", project_id,
                        "--resolution", f"{width}x{height}", "--fps", str(fps)],
    }


def _main() -> None:
    import argparse
    p = argparse.ArgumentParser(description="Render-fertigen FreeCut-Workspace bauen")
    p.add_argument("video")
    p.add_argument("song")
    p.add_argument("workspace")
    p.add_argument("--offset-ms", type=float, default=0.0)
    p.add_argument("--hook-start", type=float, default=None)
    p.add_argument("--hook-end", type=float, default=None)
    p.add_argument("--style", default="clean")
    args = p.parse_args()
    info = build_workspace(
        args.workspace, args.video, args.song,
        offset_ms=args.offset_ms, hook_start_sec=args.hook_start,
        hook_end_sec=args.hook_end, style_key=args.style,
    )
    print(json.dumps(info, indent=2))
    print("\nRender-Kommando (im Ordner editor/ ausfuehren):")
    print("  node headless/render.mjs " + " ".join(info["render_args"]) + " --out ../hookcut_test.mp4")


if __name__ == "__main__":
    _main()
