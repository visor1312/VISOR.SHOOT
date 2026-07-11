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
from backend.pipeline.beat_detect import detect_beats
from backend.pipeline.extract_audio import extract_audio
from backend.pipeline.hook_detect import detect_hook
from backend.pipeline.presets import PRESETS, apply_preset, preset_catalog, preset_is_noop
from backend.pipeline.render_sync import render_synced_video
from backend.pipeline.subtitles import burn_subtitles, group_words_into_lines, write_ass
from backend.pipeline.sync_offset import compute_offset
from backend.pipeline.transcribe import transcribe
from backend.pipeline.vocal_separation import separate_vocals

# Whisper-Modell fuer die automatischen Untertitel im Web-Flow. "small" ist
# der Kompromiss aus Qualitaet und Tempo auf CPU (~460 MB einmaliger
# Download). Das beste Modell ("large-v3", ~3 GB, deutlich langsamer) bleibt
# ueber die Gradio-Oberflaeche waehlbar.
AUTO_SUBTITLE_MODEL = "small"

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


@app.get("/projects")
def list_projects():
    """Alle Projekte inkl. ihrer Takes - Datenquelle fuer das Dashboard."""
    return [
        {**project, "takes": db.list_takes(project["id"])}
        for project in db.list_projects()
    ]


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


def _run_sync_job(
    project_id: str,
    take_id: str,
    preset: str = "clean",
    subtitles: bool = False,
    language: str = "de",
) -> None:
    """Laeuft im Hintergrund (FastAPI BackgroundTasks). Status-Stufen:
    processing -> effects -> subtitles -> done, damit das Frontend den
    Fortschritt anzeigen kann. Effekt- und Untertitel-Stufe werden nur
    durchlaufen, wenn sie tatsaechlich etwas tun."""
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

        # Beats/Untertitel arbeiten auf der Audiospur des FERTIGEN Videos -
        # deren Zeitstempel liegen damit automatisch im richtigen Zeitrahmen.
        output_audio: Path | None = None

        def _get_output_audio() -> Path:
            nonlocal output_audio
            if output_audio is None:
                output_audio = output_path.parent / "output_audio.wav"
                extract_audio(output_path, output_audio)
            return output_audio

        if preset and not preset_is_noop(preset):
            db.update_take(take_id, status="effects")
            beats = detect_beats(_get_output_audio()).beat_times_sec
            fx_path = output_path.parent / "output_fx.mp4"
            apply_preset(output_path, beats, fx_path, preset)
            fx_path.replace(output_path)

        if subtitles:
            db.update_take(take_id, status="subtitles")
            words = transcribe(
                _get_output_audio(), language=language, model_size=AUTO_SUBTITLE_MODEL,
            )
            if words:  # Instrumental/keine erkannten Woerter -> still ueberspringen
                lines = group_words_into_lines(words)
                ass_path = output_path.parent / "subtitles.ass"
                write_ass(lines, ass_path, karaoke=True)
                sub_path = output_path.parent / "output_sub.mp4"
                burn_subtitles(output_path, ass_path, sub_path)
                sub_path.replace(output_path)

        if output_audio is not None:
            output_audio.unlink(missing_ok=True)

        db.update_take(
            take_id, status="done", offset_ms=result.offset_ms,
            confidence=result.confidence, output_path=str(output_path), error=None,
        )
    except Exception as e:  # ffmpeg/subprocess Fehler, Audio-Analyse-Fehler, etc.
        db.update_take(take_id, status="error", error=str(e))


@app.get("/presets")
def list_presets():
    """Verfuegbare Editing-Presets fuer die Preset-Auswahl im Frontend."""
    return preset_catalog()


@app.post("/projects/{project_id}/takes/{take_id}/sync")
def sync_take(
    project_id: str,
    take_id: str,
    background_tasks: BackgroundTasks,
    preset: str = Form("clean"),
    subtitles: bool = Form(False),
    language: str = Form("de"),
):
    project = db.get_project(project_id)
    take = db.get_take(take_id)
    if not project or not take or take["project_id"] != project_id:
        raise HTTPException(404, "Projekt oder Take nicht gefunden")
    if preset not in PRESETS:
        raise HTTPException(400, f"Unbekanntes Preset: {preset}")
    if language not in ("de", "en"):
        raise HTTPException(400, "language muss 'de' oder 'en' sein")

    db.update_take(take_id, status="processing", error=None,
                   preset=preset, subtitles=int(subtitles))
    background_tasks.add_task(_run_sync_job, project_id, take_id,
                              preset=preset, subtitles=subtitles, language=language)
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
    ist optional - schlaegt sie fehl (demucs fehlt, Modell-Download
    blockiert), liefert separate_vocals None und es wird ohne
    Vocal-Features bewertet."""
    job = db.get_hook_job(job_id)
    if not job:
        return
    try:
        db.update_hook_job(job_id, status="separating")
        vocals_path = separate_vocals(job["song_path"])

        db.update_hook_job(job_id, status="analyzing")
        result = detect_hook(job["song_path"], vocals_path=vocals_path)

        payload = {
            "best": asdict(result.best),
            "alternatives": [asdict(c) for c in result.alternatives],
            # vocal_score None trotz Stem = Stem war praktisch stumm
            # (Instrumental) und wurde von detect_hook ignoriert.
            "used_vocals": result.best.vocal_score is not None,
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

    # Status bleibt "pending", bis der Hintergrund-Job startet und selbst
    # seine Stufen (separating -> analyzing -> done) setzt.
    background_tasks.add_task(_run_hook_job, job_id)
    return {"job_id": job_id, "status": "pending"}


@app.get("/hooks")
def list_hook_jobs(limit: int = 10):
    """Letzte Hook-Analysen (neueste zuerst) - Datenquelle fuer das Dashboard.

    Pro Job wird nur der beste Kandidat mitgeliefert; die volle Kandidaten-
    liste gibt es weiterhin ueber GET /hooks/{job_id}.
    """
    jobs = []
    for job in db.list_hook_jobs(limit=limit):
        best = None
        if job["result_json"]:
            best = json.loads(job["result_json"])["best"]
        jobs.append({
            "job_id": job["id"],
            "status": job["status"],
            "created_at": job["created_at"],
            "best": best,
        })
    return jobs


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
