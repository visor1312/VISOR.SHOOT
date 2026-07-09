"""Gradio-Oberflaeche fuer Phase 1 (Sync) des Rap-Video Auto-Editors.

Ruft die pipeline-Funktionen direkt auf (kein HTTP-Umweg ueber backend/main.py
noetig fuer ein lokales Einzelnutzer-Tool), nutzt aber dieselbe Verzeichnis-
struktur (backend/storage.py) und denselben Projektstatus (backend/db.py) wie
das FastAPI-Backend.
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import gradio as gr

from backend import db, storage
from backend.pipeline.extract_audio import extract_audio
from backend.pipeline.render_sync import render_synced_video
from backend.pipeline.sync_offset import compute_offset

db.init_db()

LOW_CONFIDENCE_THRESHOLD = 0.15

INTRO_MD = """
# Rap-Video Auto-Editor - Phase 1: Sync

Lade **eine Songdatei** (die fertig produzierte Studio-Version) und **einen oder
mehrere Video-Takes** hoch, in denen du zu genau dieser Songstelle mitgerappt
hast. Jeder Take wird einzeln gegen den Song synchronisiert (eigener
Zeitversatz pro Take) und als 9:16-Video mit der sauberen Songspur exportiert.

**Was dieses Tool NICHT macht:** Es gibt kein KI-generiertes Lip-Sync - das ist
hier unnoetig, weil deine Lippen beim Filmen bereits zum abgespielten Song
passen. Das Tool synchronisiert nur die Audiospur zeitlich exakt ueber dein
Video.
"""

LIMITATIONS_MD = """
**Bekannte Grenzen (Phase 1):**
- Keine automatische Drift-Korrektur bei abweichender Handy-Samplerate ueber
  laengere Videos - falls dir bei einem Export ein Auseinanderlaufen von Ton
  und Bild auffaellt, sag Bescheid, das wird dann gezielt nachgeruestet.
- Eine niedrige Konfidenz (siehe Ergebnis-Tabelle) bedeutet: Video-Ton war
  vermutlich zu leise/verzerrt fuer eine zuverlaessige Erkennung - bitte das
  Ergebnis manuell gegenpruefen.
- Untertitel, Beat-Effekte, Farbgrading und Upscaling folgen in Phase 2/3.
"""


def _copy_to(src_path: str, dest_path: Path) -> None:
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(src_path, dest_path)


def process(
    song_file: str | None,
    video_files: list[str] | None,
    original_audio_mode: str,
    bg_gain_db: float,
    progress: gr.Progress = gr.Progress(),
) -> list[dict[str, Any]]:
    if not song_file:
        raise gr.Error("Bitte eine Songdatei hochladen.")
    if not video_files:
        raise gr.Error("Bitte mindestens einen Video-Take hochladen.")

    project_id = db.create_project(name="gradio-session", song_path="")
    song_dest = storage.song_path(project_id, Path(song_file).suffix or ".wav")
    _copy_to(song_file, song_dest)
    db.set_project_song_path(project_id, str(song_dest))

    results: list[dict[str, Any]] = []
    for video_file in progress.tqdm(video_files, desc="Takes werden synchronisiert"):
        take_id = db.create_take(project_id, video_path="", original_audio_mode=original_audio_mode)
        video_dest = storage.take_video_path(project_id, take_id, Path(video_file).suffix or ".mp4")
        _copy_to(video_file, video_dest)
        db.set_take_video_path(take_id, str(video_dest))

        audio_path = storage.take_audio_path(project_id, take_id)
        output_path = storage.take_output_path(project_id, take_id)
        entry: dict[str, Any] = {"name": Path(video_file).name, "take_id": take_id}
        try:
            extract_audio(video_dest, audio_path)
            sync_result = compute_offset(song_dest, audio_path)
            render_synced_video(
                video_dest, song_dest, sync_result.offset_ms, output_path,
                original_audio_mode=original_audio_mode,
                original_audio_gain_db=bg_gain_db,
            )
            db.update_take(
                take_id, status="done", offset_ms=sync_result.offset_ms,
                confidence=sync_result.confidence, output_path=str(output_path),
            )
            entry.update(
                offset_ms=sync_result.offset_ms,
                confidence=sync_result.confidence,
                output_path=str(output_path),
                error=None,
            )
        except Exception as e:
            db.update_take(take_id, status="error", error=str(e))
            entry.update(offset_ms=None, confidence=None, output_path=None, error=str(e))
        results.append(entry)

    return results


with gr.Blocks(title="Rap-Video Auto-Editor") as demo:
    gr.Markdown(INTRO_MD)

    with gr.Row():
        song_input = gr.File(label="Songdatei (mp3/wav)", file_types=["audio"])
        video_input = gr.File(label="Video-Take(s)", file_count="multiple", file_types=["video"])

    with gr.Row():
        audio_mode = gr.Radio(
            choices=["mute", "background"],
            value="mute",
            label="Original-Videoton",
            info="mute = Handyton komplett stumm; background = leise im Hintergrund fuer Atmosphaere",
        )
        bg_gain = gr.Slider(
            minimum=-40, maximum=-5, value=-20, step=1,
            label="Lautstaerke Original-Videoton (dB, nur bei 'background')",
        )

    run_btn = gr.Button("Synchronisieren", variant="primary")

    results_state = gr.State([])
    run_btn.click(process, inputs=[song_input, video_input, audio_mode, bg_gain], outputs=results_state)

    @gr.render(inputs=results_state)
    def show_results(results: list[dict[str, Any]]):
        if not results:
            return
        for entry in results:
            with gr.Group():
                if entry.get("error"):
                    gr.Markdown(f"### {entry['name']} - Fehler")
                    gr.Markdown(f"```\n{entry['error']}\n```")
                    continue

                confidence = entry["confidence"]
                warning = (
                    f"\n\n⚠️ Niedrige Konfidenz ({confidence:.2f}) - Ergebnis manuell pruefen."
                    if confidence < LOW_CONFIDENCE_THRESHOLD else ""
                )
                gr.Markdown(
                    f"### {entry['name']}\n"
                    f"Offset: **{entry['offset_ms']:.1f} ms** | Konfidenz: **{confidence:.2f}**{warning}"
                )
                gr.Video(value=entry["output_path"], label="Vorschau")
                gr.File(value=entry["output_path"], label="Download")

    gr.Markdown(LIMITATIONS_MD)


if __name__ == "__main__":
    demo.queue().launch()
