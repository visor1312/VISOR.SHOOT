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

from fastapi import BackgroundTasks, Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from backend import auth, db, storage
from backend.pipeline.beat_detect import detect_beats
from backend.pipeline.extract_audio import extract_audio
from backend.pipeline.hook_detect import detect_hook
from backend.pipeline.presets import PRESETS, apply_preset, preset_catalog, preset_is_noop
from backend.pipeline.render_sync import _probe_duration_sec, render_synced_video
from backend.pipeline.subtitles import burn_subtitles, group_words_into_lines, write_ass
from backend.pipeline.sync_offset import compute_offset
from backend.pipeline.transcribe import transcribe
from backend.pipeline.vocal_separation import separate_vocals

# Whisper-Modell fuer die automatischen Untertitel im Web-Flow. "small" ist
# der Kompromiss aus Qualitaet und Tempo auf CPU (~460 MB einmaliger
# Download). Das beste Modell ("large-v3", ~3 GB, deutlich langsamer) bleibt
# ueber die Gradio-Oberflaeche waehlbar.
AUTO_SUBTITLE_MODEL = "small"
# Fuer den All-in-One-Assistenten: bestes Whisper-Modell auf der ISOLIERTEN
# Gesangsspur (Demucs) - das war die Ursache der schlechten Untertitel: der
# Beat im Gesamtmix ruiniert die Erkennung. "large-v3" ist gross (~3 GB,
# einmaliger Download) und langsam, aber genau, was bei Untertiteln zaehlt.
AUTO_SUBTITLE_MODEL_BEST = "large-v3"

app = FastAPI(title="HOOKCUT")

# Das React-Dashboard (web/, Vite auf Port 5173) spricht das Backend ueber den
# /api-Proxy an (same-origin, web/vite.config.ts). CORS deckt nur direkte
# Aufrufe vom Dev-Server ab - seit dem Login-System mit Session-Cookies darf
# hier KEIN Wildcard mehr stehen (Credentials + "*" ist per Spec verboten).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)


@app.on_event("startup")
def _on_startup() -> None:
    db.init_db()


def _save_upload(upload: UploadFile, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("wb") as f:
        shutil.copyfileobj(upload.file, f)
    return dest


# Ownership-Regel (gilt fuer alle Datenrouten): Listen filtern per user_id,
# Einzel-/Download-Routen werfen bei fremden Ressourcen 404 (nicht 403) -
# so laesst sich nicht einmal herausfinden, OB eine fremde ID existiert.
def _own(row: dict | None, user: dict) -> dict:
    if not row or row.get("user_id") != user["id"]:
        raise HTTPException(404, "Nicht gefunden")
    return row


@app.post("/projects")
def create_project(name: str = Form(...), song: UploadFile = File(...),
                   user: dict = Depends(auth.get_current_user)):
    suffix = Path(song.filename or "song.wav").suffix or ".wav"
    project_id = db.create_project(name=name, song_path="", user_id=user["id"])
    song_dest = storage.song_path(project_id, suffix)
    _save_upload(song, song_dest)
    db.set_project_song_path(project_id, str(song_dest))
    return {"project_id": project_id}


@app.get("/projects")
def list_projects(user: dict = Depends(auth.get_current_user)):
    """Eigene Projekte inkl. ihrer Takes - Datenquelle fuer das Dashboard."""
    return [
        {**project, "takes": db.list_takes(project["id"])}
        for project in db.list_projects(user_id=user["id"])
    ]


@app.post("/projects/{project_id}/takes")
def create_take(project_id: str, video: UploadFile = File(...), original_audio_mode: str = Form("mute"),
                user: dict = Depends(auth.get_current_user)):
    _own(db.get_project(project_id), user)
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
    user: dict = Depends(auth.get_current_user),
):
    _own(db.get_project(project_id), user)
    take = db.get_take(take_id)
    if not take or take["project_id"] != project_id:
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
def get_take(project_id: str, take_id: str, user: dict = Depends(auth.get_current_user)):
    _own(db.get_project(project_id), user)
    take = db.get_take(take_id)
    if not take or take["project_id"] != project_id:
        raise HTTPException(404, "Take nicht gefunden")
    return take


@app.get("/projects/{project_id}/takes")
def list_takes(project_id: str, user: dict = Depends(auth.get_current_user)):
    _own(db.get_project(project_id), user)
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
def analyze_hook(background_tasks: BackgroundTasks, song: UploadFile = File(...),
                 user: dict = Depends(auth.get_current_user)):
    suffix = Path(song.filename or "song.wav").suffix or ".wav"
    job_id = db.create_hook_job(song_path="", user_id=user["id"])
    song_dest = storage.hook_song_path(job_id, suffix)
    _save_upload(song, song_dest)
    db.set_hook_job_song_path(job_id, str(song_dest))

    # Status bleibt "pending", bis der Hintergrund-Job startet und selbst
    # seine Stufen (separating -> analyzing -> done) setzt.
    background_tasks.add_task(_run_hook_job, job_id)
    return {"job_id": job_id, "status": "pending"}


@app.get("/hooks")
def list_hook_jobs(limit: int = 10, user: dict = Depends(auth.get_current_user)):
    """Eigene Hook-Analysen (neueste zuerst) - Datenquelle fuer das Dashboard.

    Pro Job wird nur der beste Kandidat mitgeliefert; die volle Kandidaten-
    liste gibt es weiterhin ueber GET /hooks/{job_id}.
    """
    jobs = []
    for job in db.list_hook_jobs(limit=limit, user_id=user["id"]):
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
def get_hook_job(job_id: str, user: dict = Depends(auth.get_current_user)):
    job = _own(db.get_hook_job(job_id), user)
    result = json.loads(job["result_json"]) if job["result_json"] else None
    return {"job_id": job["id"], "status": job["status"], "error": job["error"], "result": result}


@app.get("/hooks/{job_id}/preview/{index}")
def hook_preview(job_id: str, index: int, user: dict = Depends(auth.get_current_user)):
    """MP3-Ausschnitt eines Kandidaten (0 = bester, 1.. = Alternativen)."""
    job = _own(db.get_hook_job(job_id), user)
    if not job["result_json"]:
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


def _run_analyze_job(job_id: str) -> None:
    """Editor-Analyse (Etappe 3): NUR Zahlen, KEIN Rendern.

    Der HOOKCUT-Editor (editor/, FreeCut-Fork) uebernimmt Schnitt und Export
    selbst im Browser - er braucht von uns nur Sync-Versatz, Hook-Fenster und
    Dauern, um die Timeline vorzubereiten.
    """
    job = db.get_analyze_job(job_id)
    if not job:
        return
    try:
        db.update_analyze_job(job_id, status="analyzing")

        video_audio = storage.analyze_job_dir(job_id) / "video_audio.wav"
        extract_audio(job["video_path"], video_audio)
        offset = compute_offset(job["song_path"], video_audio)
        hook = detect_hook(job["song_path"])

        payload = {
            "offset_ms": offset.offset_ms,
            "confidence": offset.confidence,
            "video_duration_sec": _probe_duration_sec(job["video_path"]),
            "song_duration_sec": _probe_duration_sec(job["song_path"]),
            "hook": {
                "best": asdict(hook.best),
                "alternatives": [asdict(c) for c in hook.alternatives],
            },
        }
        db.update_analyze_job(job_id, status="done", result_json=json.dumps(payload), error=None)
    except Exception as e:
        db.update_analyze_job(job_id, status="error", error=str(e))


@app.post("/editor/analyze")
def editor_analyze(
    background_tasks: BackgroundTasks,
    video: UploadFile = File(...),
    song: UploadFile = File(...),
    user: dict = Depends(auth.get_current_user),
):
    video_suffix = Path(video.filename or "video.mp4").suffix or ".mp4"
    song_suffix = Path(song.filename or "song.wav").suffix or ".wav"
    job_id = db.create_analyze_job(video_path="", song_path="", user_id=user["id"])
    video_dest = _save_upload(video, storage.analyze_video_path(job_id, video_suffix))
    song_dest = _save_upload(song, storage.analyze_song_path(job_id, song_suffix))
    db.set_analyze_job_paths(job_id, str(video_dest), str(song_dest))

    db.update_analyze_job(job_id, status="analyzing")
    background_tasks.add_task(_run_analyze_job, job_id)
    return {"job_id": job_id, "status": "analyzing"}


@app.get("/editor/analyze/{job_id}")
def get_editor_analyze(job_id: str, user: dict = Depends(auth.get_current_user)):
    job = _own(db.get_analyze_job(job_id), user)
    result = json.loads(job["result_json"]) if job["result_json"] else None
    return {"job_id": job["id"], "status": job["status"], "error": job["error"], "result": result}


@app.get("/styles")
def list_styles():
    from backend.pipeline.styles import style_catalog
    return {"styles": style_catalog()}


def _run_edit_analyze(job_id: str) -> None:
    """Schritt 1: ganzes Video gegen Song synchronisieren (nur Zahlen)."""
    job = db.get_edit_job(job_id)
    if not job:
        return
    try:
        db.update_edit_job(job_id, status="syncing")
        audio = storage.edit_job_dir(job_id) / "video_audio.wav"
        extract_audio(job["video_path"], audio)
        offset = compute_offset(job["song_path"], audio)
        db.update_edit_job(job_id, status="synced",
                           offset_ms=offset.offset_ms, confidence=offset.confidence)
    except Exception as e:
        db.update_edit_job(job_id, status="error", error=str(e))


@app.post("/edit/analyze")
def edit_analyze(background_tasks: BackgroundTasks, video: UploadFile = File(...),
                 song: UploadFile = File(...), with_subtitles: str = Form("false"),
                 lyrics: str = Form(""), user: dict = Depends(auth.get_current_user)):
    v_suffix = Path(video.filename or "video.mp4").suffix or ".mp4"
    s_suffix = Path(song.filename or "song.wav").suffix or ".wav"
    want_subs = with_subtitles.lower() in ("true", "1", "yes", "on")
    job_id = db.create_edit_job(video_path="", song_path="", with_subtitles=want_subs,
                                lyrics=lyrics.strip() or None, user_id=user["id"])
    v_dest = _save_upload(video, storage.edit_video_path(job_id, v_suffix))
    s_dest = _save_upload(song, storage.edit_song_path(job_id, s_suffix))
    db.update_edit_job(job_id, video_path=str(v_dest), song_path=str(s_dest), status="syncing")
    background_tasks.add_task(_run_edit_analyze, job_id)
    return {"job_id": job_id, "status": "syncing"}


def _run_edit_hook(job_id: str) -> None:
    """Schritt 2 (optional): viralsten Hook suchen + auf Video zuschneiden."""
    from backend.pipeline.render_pipeline import _choose_hook
    job = db.get_edit_job(job_id)
    if not job:
        return
    try:
        db.update_edit_job(job_id, status="hooking")
        result = detect_hook(job["song_path"])
        video_dur = _probe_duration_sec(job["video_path"])
        chosen = _choose_hook((job["offset_ms"] or 0) / 1000.0, video_dur, result.best, result.alternatives)
        if chosen:
            db.update_edit_job(job_id, status="hooked", hook_start=chosen[0], hook_end=chosen[1])
        else:
            db.update_edit_job(job_id, status="hooked", hook_start=None, hook_end=None)
    except Exception as e:
        db.update_edit_job(job_id, status="error", error=str(e))


@app.post("/edit/{job_id}/hook")
def edit_hook(job_id: str, background_tasks: BackgroundTasks,
              user: dict = Depends(auth.get_current_user)):
    _own(db.get_edit_job(job_id), user)
    db.update_edit_job(job_id, status="hooking")
    background_tasks.add_task(_run_edit_hook, job_id)
    return {"job_id": job_id, "status": "hooking"}


def _run_edit_render(job_id: str, style_key: str, use_hook: bool, beat_effects: bool,
                     platform_keys: str) -> None:
    """Schritt 3: Style anwenden + unsichtbar via FreeCut rendern -
    einmal pro gewaehltem Zielformat (Multi-Plattform-Export)."""
    from backend.pipeline.freecut_workspace import SubtitleCue, build_workspace
    from backend.pipeline.platforms import parse_platform_keys
    from backend.pipeline.render_pipeline import run_headless_render
    job = db.get_edit_job(job_id)
    if not job:
        return
    try:
        platforms = parse_platform_keys(platform_keys)
        db.update_edit_job(job_id, status="rendering", style=style_key,
                           platforms=",".join(p.key for p in platforms))
        hook_start = job["hook_start"] if use_hook else None
        hook_end = job["hook_end"] if use_hook else None

        cues = None
        if job["with_subtitles"]:
            # Auf der isolierten Gesangsspur transkribieren (falls Demucs da) -
            # ohne Beat wird die Erkennung drastisch genauer. Deutsch erzwungen.
            db.update_edit_job(job_id, status="transcribing")
            vocals = separate_vocals(job["song_path"])
            transcribe_src = str(vocals) if vocals else job["song_path"]
            words = transcribe(transcribe_src, language="de",
                               model_size=AUTO_SUBTITLE_MODEL_BEST,
                               initial_prompt=job["lyrics"] or None)
            if job["lyrics"]:
                # Nutzertext = Wahrheit: exakt seine Woerter anzeigen, Timing
                # aus der Erkennung uebernehmen (lyrics_align).
                from backend.pipeline.lyrics_align import align_lyrics_to_words
                aligned = align_lyrics_to_words(job["lyrics"], words)
                if aligned:
                    words = aligned
            lines = group_words_into_lines(words)
            cues = [SubtitleCue(l.start, l.end, l.text) for l in lines]

        # Analyse (Sync/Hook/Untertitel) gilt fuer alle Formate - nur der
        # Workspace-Bau + Render laeuft pro Plattform. Nach jedem fertigen
        # Format wird outputs_json aktualisiert, damit das UI den Fortschritt
        # zeigen und Fertiges schon anbieten kann.
        db.update_edit_job(job_id, status="rendering")
        editor_dir = Path(__file__).resolve().parent.parent / "editor"
        outputs: dict[str, str] = {}
        for p in platforms:
            ws = storage.edit_job_dir(job_id) / "ws" / p.key
            info = build_workspace(
                ws, job["video_path"], job["song_path"],
                offset_ms=job["offset_ms"] or 0.0,
                hook_start_sec=hook_start, hook_end_sec=hook_end,
                style_key=style_key, subtitle_cues=cues,
                beat_effects=beat_effects,
                width=p.width, height=p.height,
            )
            out = storage.edit_output_path(job_id, p.key)
            run_headless_render(editor_dir, info["render_args"], out)
            outputs[p.key] = str(out)
            db.update_edit_job(job_id, outputs_json=json.dumps(outputs))
        db.update_edit_job(job_id, status="done",
                           output_path=outputs[platforms[0].key],
                           outputs_json=json.dumps(outputs))
    except Exception as e:
        db.update_edit_job(job_id, status="error", error=str(e))


@app.post("/edit/{job_id}/render")
def edit_render(job_id: str, background_tasks: BackgroundTasks,
                style: str = Form(...), use_hook: str = Form("false"),
                beat_effects: str = Form("false"), platforms: str = Form("reel"),
                user: dict = Depends(auth.get_current_user)):
    _own(db.get_edit_job(job_id), user)
    db.update_edit_job(job_id, status="rendering")
    background_tasks.add_task(_run_edit_render, job_id, style,
                              use_hook.lower() in ("true", "1", "yes", "on"),
                              beat_effects.lower() in ("true", "1", "yes", "on"),
                              platforms)
    return {"job_id": job_id, "status": "rendering"}


@app.get("/platforms")
def list_platforms():
    from backend.pipeline.platforms import platform_catalog
    return {"platforms": platform_catalog()}


def _edit_outputs(job: dict) -> list[dict] | None:
    """outputs[]-Block eines Edit-Jobs (Formate + ready-Status) oder None."""
    from backend.pipeline.platforms import get_platform
    if not job["platforms"]:
        return None
    done_outputs = json.loads(job["outputs_json"]) if job["outputs_json"] else {}
    outputs = []
    for key in job["platforms"].split(","):
        p = get_platform(key)
        outputs.append({"platform": p.key, "name": p.name,
                        "width": p.width, "height": p.height,
                        "ready": p.key in done_outputs})
    return outputs


@app.get("/edit")
def list_edit_jobs(limit: int = 20, user: dict = Depends(auth.get_current_user)):
    """Eigene Wizard-Reels (neueste zuerst) - Datenquelle fuer 'Meine Reels'
    im personalisierten Dashboard."""
    return [
        {"job_id": job["id"], "status": job["status"], "error": job["error"],
         "style": job["style"], "created_at": job["created_at"],
         "has_output": bool(job["output_path"]), "outputs": _edit_outputs(job)}
        for job in db.list_edit_jobs(user["id"], limit=limit)
    ]


@app.get("/edit/{job_id}")
def get_edit(job_id: str, user: dict = Depends(auth.get_current_user)):
    job = _own(db.get_edit_job(job_id), user)
    outputs = _edit_outputs(job)
    return {
        "job_id": job["id"], "status": job["status"], "error": job["error"],
        "with_subtitles": bool(job["with_subtitles"]), "style": job["style"],
        "offset_ms": job["offset_ms"], "confidence": job["confidence"],
        "hook": {"start_sec": job["hook_start"], "end_sec": job["hook_end"]}
        if job["hook_start"] is not None else None,
        "has_output": bool(job["output_path"]),
        "outputs": outputs,
    }


@app.get("/edit/{job_id}/download")
def download_edit(job_id: str, platform: str | None = None,
                  user: dict = Depends(auth.get_current_user)):
    job = _own(db.get_edit_job(job_id), user)
    if platform:
        outputs = json.loads(job["outputs_json"]) if job["outputs_json"] else {}
        path = outputs.get(platform)
        if not path:
            raise HTTPException(404, "Dieses Format ist noch nicht fertig")
        return FileResponse(path, media_type="video/mp4",
                            filename=f"hookcut_{platform}.mp4")
    if not job["output_path"]:
        raise HTTPException(404, "Noch kein fertiges Video")
    return FileResponse(job["output_path"], media_type="video/mp4", filename="hookcut_reel.mp4")


@app.get("/projects/{project_id}/takes/{take_id}/download")
def download_take(project_id: str, take_id: str, user: dict = Depends(auth.get_current_user)):
    _own(db.get_project(project_id), user)
    take = db.get_take(take_id)
    if not take or take["project_id"] != project_id:
        raise HTTPException(404, "Take nicht gefunden")
    if take["status"] != "done" or not take["output_path"]:
        raise HTTPException(409, "Take ist noch nicht fertig synchronisiert")
    return FileResponse(take["output_path"], media_type="video/mp4", filename=Path(take["output_path"]).name)
