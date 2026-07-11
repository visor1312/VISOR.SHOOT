"""FastAPI-Endpunkte fuer HOOKCUT (Sync + Viral Hook Detector).

Duenne Schicht ueber db.py und den pipeline/-Modulen. Das Gradio-Frontend
(frontend/app.py) ruft fuer die MVP-Oberflaeche dieselben pipeline-Funktionen
direkt auf (kein HTTP-Umweg noetig fuer einen lokalen Einzelnutzer), nutzt
aber dieselbe Verzeichnisstruktur (storage.py) und DB (db.py). Diese API
existiert fuer programmatischen/skriptbaren Zugriff.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import asdict
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from backend import db, storage
from backend.pipeline.extract_audio import extract_audio
from backend.pipeline.hook_detect import detect_hook
from backend.pipeline.render_sync import render_synced_video
from backend.pipeline.sync_offset import compute_offset
from backend.pipeline.vocal_separation import separate_vocals

app = FastAPI(title="HOOKCUT")

# Fuer die lokale Entwicklung: das React-Dashboard (web/, Vite auf Port 5173)
# darf das Backend direkt aufrufen. Im Dev-Server laeuft ohnehin ein /api-Proxy
# (web/vite.config.ts), CORS ist die Absicherung fuer direkte Aufrufe.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


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


def _run_sync_job(project_id: str, take_id: str) -> None:
    """Laeuft im Hintergrund (FastAPI BackgroundTasks). Aktualisiert den
    Take-Status in der DB; das Frontend pollt GET .../takes/{take_id}."""
    project = db.get_project(project_id)
    take = db.get_take(take_id)
    if not project or not take:
        return

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


@app.post("/projects/{project_id}/takes/{take_id}/sync")
def sync_take(project_id: str, take_id: str, background_tasks: BackgroundTasks):
    project = db.get_project(project_id)
    take = db.get_take(take_id)
    if not project or not take or take["project_id"] != project_id:
        raise HTTPException(404, "Projekt oder Take nicht gefunden")

    db.update_take(take_id, status="processing", error=None)
    background_tasks.add_task(_run_sync_job, project_id, take_id)
    return {"status": "processing", "take_id": take_id}


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


def _run_hook_job(job_id: str) -> None:
    """Laeuft im Hintergrund. Status-Stufen: separating -> analyzing -> done,
    damit das Frontend den Fortschritt anzeigen kann. Die Vocal-Separation
    ist optional - schlaegt sie fehl, wird ohne Vocal-Features bewertet."""
    job = db.get_hook_job(job_id)
    if not job:
        return
    try:
        db.update_hook_job(job_id, status="separating")
        vocals = separate_vocals(job["song_path"])

        db.update_hook_job(job_id, status="analyzing")
        result = detect_hook(job["song_path"], vocals_path=vocals)

        payload = {
            "best": asdict(result.best),
            "alternatives": [asdict(c) for c in result.alternatives],
            "used_vocals": vocals is not None,
        }
        db.update_hook_job(job_id, status="done", result_json=json.dumps(payload), error=None)
    except Exception as e:
        db.update_hook_job(job_id, status="error", error=str(e))


@app.post("/hooks/analyze")
def analyze_hook(background_tasks: BackgroundTasks, song: UploadFile = File(...)):
    suffix = Path(song.filename or "song.wav").suffix or ".wav"
    job_id = db.create_hook_job(song_path="")
    song_dest = storage.hook_song_path(job_id, suffix)
    _save_upload(song, song_dest)
    db.set_hook_job_song_path(job_id, str(song_dest))

    db.update_hook_job(job_id, status="separating")
    background_tasks.add_task(_run_hook_job, job_id)
    return {"job_id": job_id, "status": "separating"}


@app.get("/hooks/{job_id}")
def get_hook_job(job_id: str):
    job = db.get_hook_job(job_id)
    if not job:
        raise HTTPException(404, "Hook-Analyse nicht gefunden")
    result = json.loads(job["result_json"]) if job["result_json"] else None
    return {"job_id": job["id"], "status": job["status"], "error": job["error"], "result": result}


@app.get("/hooks/{job_id}/preview/{index}")
def hook_preview(job_id: str, index: int):
    """MP3-Ausschnitt eines Kandidaten (0 = bester, 1.. = Alternativen)."""
    job = db.get_hook_job(job_id)
    if not job or not job["result_json"]:
        raise HTTPException(404, "Hook-Analyse nicht gefunden oder noch nicht fertig")
    result = json.loads(job["result_json"])
    candidates = [result["best"], *result["alternatives"]]
    if not 0 <= index < len(candidates):
        raise HTTPException(404, "Kandidat existiert nicht")

    preview = storage.hook_preview_path(job_id, index)
    if not preview.exists():
        c = candidates[index]
        cmd = [
            "ffmpeg", "-y",
            "-ss", str(c["start_sec"]), "-to", str(c["end_sec"]),
            "-i", job["song_path"],
            "-vn", "-codec:a", "libmp3lame", "-q:a", "4",
            str(preview),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            raise HTTPException(500, f"Preview-Schnitt fehlgeschlagen: {proc.stderr[-300:]}")
    return FileResponse(preview, media_type="audio/mpeg", filename=f"hook_{index}.mp3")


@app.get("/projects/{project_id}/takes/{take_id}/download")
def download_take(project_id: str, take_id: str):
    take = db.get_take(take_id)
    if not take or take["project_id"] != project_id:
        raise HTTPException(404, "Take nicht gefunden")
    if take["status"] != "done" or not take["output_path"]:
        raise HTTPException(409, "Take ist noch nicht fertig synchronisiert")
    return FileResponse(take["output_path"], media_type="video/mp4", filename=Path(take["output_path"]).name)
