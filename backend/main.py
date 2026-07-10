"""FastAPI-Endpunkte fuer HOOKCUT (Phase 1: Sync).

Duenne Schicht ueber db.py und den pipeline/-Modulen. Das Gradio-Frontend
(frontend/app.py) ruft fuer die MVP-Oberflaeche dieselben pipeline-Funktionen
direkt auf (kein HTTP-Umweg noetig fuer einen lokalen Einzelnutzer), nutzt
aber dieselbe Verzeichnisstruktur (storage.py) und DB (db.py). Diese API
existiert fuer programmatischen/skriptbaren Zugriff.
"""
from __future__ import annotations

import shutil
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from backend import db, storage
from backend.pipeline.extract_audio import extract_audio
from backend.pipeline.render_sync import render_synced_video
from backend.pipeline.sync_offset import compute_offset

app = FastAPI(title="HOOKCUT")


@app.on_event("startup")
def _on_startup() -> None:
    db.init_db()


def _save_upload(upload: UploadFile, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("wb") as f:
        shutil.copyfileobj(upload.file, f)
    return dest


@app.post("/projects")
def create_project(name: str = Form(...), song: UploadFile = File(...)):
    suffix = Path(song.filename or "song.wav").suffix or ".wav"
    project_id = db.create_project(name=name, song_path="")  # Pfad wird gleich nachgetragen
    song_dest = storage.song_path(project_id, suffix)
    _save_upload(song, song_dest)
    db.set_project_song_path(project_id, str(song_dest))
    return {"project_id": project_id}


@app.post("/projects/{project_id}/takes")
def create_take(project_id: str, video: UploadFile = File(...), original_audio_mode: str = Form("mute")):
    project = db.get_project(project_id)
    if not project:
        raise HTTPException(404, "Projekt nicht gefunden")
    if original_audio_mode not in ("mute", "background"):
        raise HTTPException(400, "original_audio_mode muss 'mute' oder 'background' sein")

    take_id = db.create_take(project_id, video_path="", original_audio_mode=original_audio_mode)
    suffix = Path(video.filename or "video.mp4").suffix or ".mp4"
    video_dest = storage.take_video_path(project_id, take_id, suffix)
    _save_upload(video, video_dest)
    db.set_take_video_path(take_id, str(video_dest))
    return {"take_id": take_id}


@app.post("/projects/{project_id}/takes/{take_id}/sync")
def sync_take(project_id: str, take_id: str):
    project = db.get_project(project_id)
    take = db.get_take(take_id)
    if not project or not take or take["project_id"] != project_id:
        raise HTTPException(404, "Projekt oder Take nicht gefunden")

    audio_path = storage.take_audio_path(project_id, take_id)
    output_path = storage.take_output_path(project_id, take_id)

    try:
        extract_audio(take["video_path"], audio_path)
        result = compute_offset(project["song_path"], audio_path)
        render_synced_video(
            take["video_path"], project["song_path"], result.offset_ms, output_path,
            original_audio_mode=take["original_audio_mode"],
        )
        db.update_take(
            take_id, status="done", offset_ms=result.offset_ms,
            confidence=result.confidence, output_path=str(output_path), error=None,
        )
    except Exception as e:  # ffmpeg/subprocess Fehler, Audio-Analyse-Fehler, etc.
        db.update_take(take_id, status="error", error=str(e))
        raise HTTPException(500, f"Sync fehlgeschlagen: {e}")

    return db.get_take(take_id)


@app.get("/projects/{project_id}/takes/{take_id}")
def get_take(project_id: str, take_id: str):
    take = db.get_take(take_id)
    if not take or take["project_id"] != project_id:
        raise HTTPException(404, "Take nicht gefunden")
    return take


@app.get("/projects/{project_id}/takes")
def list_takes(project_id: str):
    if not db.get_project(project_id):
        raise HTTPException(404, "Projekt nicht gefunden")
    return db.list_takes(project_id)


@app.get("/projects/{project_id}/takes/{take_id}/download")
def download_take(project_id: str, take_id: str):
    take = db.get_take(take_id)
    if not take or take["project_id"] != project_id:
        raise HTTPException(404, "Take nicht gefunden")
    if take["status"] != "done" or not take["output_path"]:
        raise HTTPException(409, "Take ist noch nicht fertig synchronisiert")
    return FileResponse(take["output_path"], media_type="video/mp4", filename=Path(take["output_path"]).name)
