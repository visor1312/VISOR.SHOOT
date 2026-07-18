"""FreeCut-Evaluation - Adapter-Prototyp (Teil A des Spikes).

Beweist die Kernfrage des Spikes: Kann unsere HOOKCUT-Analyse eine fertige
FreeCut-Timeline programmatisch erzeugen? Antwort laut FreeCut-Quellcode: JA.

FreeCut hat ein datei-basiertes Projektformat (`project.json`) und eine
headless Edit-/Render-CLI (`headless/edit.mjs`, `headless/render.mjs`), die
ohne UI ein Projekt hydrieren, bearbeiten und rendern. Das Datenmodell
(src/types/project.ts, src/types/timeline.ts) passt fast 1:1 auf unsere
Analyse-Ausgabe:

    HOOKCUT-Analyse            ->  FreeCut-Projekt
    ------------------------------------------------------------------
    offset_ms (sync_offset.py) ->  Startposition der Song-Tonspur
    hook_start/end (hook_detect)-> Trim von Video- und Tonspur auf den Hook
    subtitle_cues (subtitles)  ->  ein SubtitleSegmentItem mit cues[]
    9:16                       ->  metadata.width/height (1080x1920)

Dieser Prototyp erzeugt NUR die project.json-Struktur (reine Datenabbildung).
Das tatsaechliche Rendern/Abspielen laeuft im Browser bzw. via headless Chrome
auf dem Rechner des Nutzers (Teil B) - das kann die Sandbox nicht (WebGPU/
WebCodecs + Google-Chrome-Kanal fehlen).

Sign-Konvention offset_ms (aus backend/pipeline/sync_offset.py):
  positiv  = Song muss nach vorne getrimmt werden (Video startet mitten im Song)
  negativ  = Song muss verzoegert werden (Video begann vor dem Song)
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field


def _fid() -> str:
    return str(uuid.uuid4())


def _sec_to_frames(seconds: float, fps: int) -> int:
    return round(seconds * fps)


@dataclass
class SubtitleCue:
    start_seconds: float
    end_seconds: float
    text: str


@dataclass
class HookcutAnalysis:
    """Genau das, was unsere Python-Pipeline heute schon liefert."""
    video_media_id: str
    video_src: str
    video_duration_sec: float
    song_media_id: str
    song_src: str
    song_duration_sec: float
    offset_ms: float                     # sync_offset.compute_offset
    hook_start_sec: float                # hook_detect.detect_hook -> best.start_sec
    hook_end_sec: float                  # hook_detect.detect_hook -> best.end_sec
    subtitle_cues: list[SubtitleCue] = field(default_factory=list)


def build_freecut_project(
    a: HookcutAnalysis,
    *,
    name: str = "HOOKCUT Export",
    width: int = 1080,
    height: int = 1920,   # 9:16 hochkant
    fps: int = 30,
) -> dict:
    """Erzeugt ein FreeCut-Project-dict (serialisierbar zu project.json).

    Timeline: Video (stumm) auf Spur 1, Song auf Spur 2 um offset verschoben,
    beide auf das Hook-Fenster getrimmt, plus ein Untertitel-Segment.
    """
    now = 0  # createdAt/updatedAt - vom Aufrufer/Storage gesetzt
    offset_sec = a.offset_ms / 1000.0
    hook_len_sec = max(0.0, a.hook_end_sec - a.hook_start_sec)
    hook_len_frames = _sec_to_frames(hook_len_sec, fps)

    video_track_id = _fid()
    audio_track_id = _fid()
    subtitle_track_id = _fid()

    tracks = [
        {"id": video_track_id, "name": "Video", "kind": "video", "height": 80,
         "locked": False, "visible": True, "muted": True, "solo": False, "order": 0},
        {"id": audio_track_id, "name": "Song", "kind": "audio", "height": 60,
         "locked": False, "visible": True, "muted": False, "solo": False, "order": 1},
        {"id": subtitle_track_id, "name": "Untertitel", "kind": "video", "height": 60,
         "locked": False, "visible": True, "muted": True, "solo": False, "order": 2},
    ]

    # Video-lokaler Hook-Start: an welcher Stelle IM VIDEO liegt der Song-Hook?
    # Song-Zeit hook_start entspricht Video-Zeit (hook_start - offset_sec).
    video_hook_start_sec = max(0.0, a.hook_start_sec - offset_sec)

    video_item = {
        "id": _fid(), "type": "video", "trackId": video_track_id,
        "from": 0, "durationInFrames": hook_len_frames, "label": "Performance",
        "mediaId": a.video_media_id, "src": a.video_src,
        "trimStart": _sec_to_frames(video_hook_start_sec, fps),
        "sourceStart": _sec_to_frames(video_hook_start_sec, fps),
        "sourceDuration": _sec_to_frames(a.video_duration_sec, fps),
        "sourceFps": fps, "volume": -60,  # stumm (Originalton aus)
    }

    audio_item = {
        "id": _fid(), "type": "audio", "trackId": audio_track_id,
        "from": 0, "durationInFrames": hook_len_frames, "label": "Song",
        "mediaId": a.song_media_id, "src": a.song_src,
        "trimStart": _sec_to_frames(a.hook_start_sec, fps),
        "sourceStart": _sec_to_frames(a.hook_start_sec, fps),
        "sourceDuration": _sec_to_frames(a.song_duration_sec, fps),
        "sourceFps": fps, "volume": 0,
    }

    items = [video_item, audio_item]

    if a.subtitle_cues:
        # Cue-Zeiten relativ zum Clip-Anfang (Hook-Start im Song).
        rel_cues = [
            {"id": _fid(),
             "startSeconds": max(0.0, c.start_seconds - a.hook_start_sec),
             "endSeconds": max(0.0, c.end_seconds - a.hook_start_sec),
             "text": c.text}
            for c in a.subtitle_cues
            if c.end_seconds > a.hook_start_sec and c.start_seconds < a.hook_end_sec
        ]
        if rel_cues:
            items.append({
                "id": _fid(), "type": "subtitle", "trackId": subtitle_track_id,
                "from": 0, "durationInFrames": hook_len_frames, "label": "Untertitel",
                "source": {"type": "transcript", "mediaId": a.song_media_id,
                           "clipId": audio_item["id"]},
                "cues": rel_cues, "color": "#ffffff",
            })

    return {
        "id": _fid(), "name": name, "description": "Automatisch aus HOOKCUT erzeugt",
        "createdAt": now, "updatedAt": now,
        "duration": hook_len_frames,
        "schemaVersion": 1,
        "metadata": {"width": width, "height": height, "fps": fps, "backgroundColor": "#000000"},
        "timeline": {"masterBusDb": 0, "tracks": tracks, "items": items},
    }


def _demo() -> dict:
    """Beispiel mit erfundenen, aber realistischen Analyse-Werten."""
    analysis = HookcutAnalysis(
        video_media_id="vid-001", video_src="media/vid-001/performance.mp4",
        video_duration_sec=30.0,
        song_media_id="song-001", song_src="media/song-001/track.wav",
        song_duration_sec=180.0,
        offset_ms=240.0,           # Video begann 0,24s nach Song-Anfang
        hook_start_sec=48.0, hook_end_sec=64.0,  # 16s-Hook im Song
        subtitle_cues=[
            SubtitleCue(48.0, 50.2, "Real recognize real"),
            SubtitleCue(50.2, 52.5, "wir kommen von ganz unten"),
            SubtitleCue(52.5, 55.0, "kein Cap, das sind Fakten"),
        ],
    )
    return build_freecut_project(analysis)


if __name__ == "__main__":
    project = _demo()
    print(json.dumps(project, indent=2, ensure_ascii=False))
