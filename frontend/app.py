"""Gradio-Oberflaeche fuer den Rap-Video Auto-Editor.

Phase 1 (Sync) + Phase 2 (Untertitel) + Phase 3 (Farbgrading, Beat-Effekte,
Multi-Take-Schnitt, optionales Upscaling). Ruft die pipeline-Funktionen direkt
auf (kein HTTP-Umweg ueber backend/main.py noetig fuer ein lokales
Einzelnutzer-Tool), nutzt aber dieselbe Verzeichnisstruktur (backend/storage.py)
und denselben Projektstatus (backend/db.py) wie das FastAPI-Backend.
"""
from __future__ import annotations

import shutil
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import gradio as gr

from backend import db, storage
from backend.pipeline.beat_detect import detect_beats
from backend.pipeline.effects_grading import COLOR_PRESETS, BeatEffectConfig, render_with_beat_effects
from backend.pipeline.extract_audio import extract_audio
from backend.pipeline.multitake_cut import TakeInfo, compute_multitake_plan, render_multitake_cut
from backend.pipeline.render_sync import render_synced_video
from backend.pipeline.subtitles import burn_subtitles, group_words_into_lines, write_ass
from backend.pipeline.sync_offset import LOW_CONFIDENCE_THRESHOLD, compute_offset
from backend.pipeline.transcribe import DEFAULT_MODEL_SIZE, MODEL_SIZES, Word, transcribe
from backend.pipeline.upscale import upscale_video

db.init_db()

INTRO_MD = """
# Rap-Video Auto-Editor

Lade **eine Songdatei** (die fertig produzierte Studio-Version) und **einen oder
mehrere Video-Takes** hoch, in denen du zu genau dieser Songstelle mitgerappt
hast. Jeder Take wird einzeln gegen den Song synchronisiert (eigener
Zeitversatz pro Take) und als 9:16-Video mit der sauberen Songspur exportiert.
Danach kannst du pro Take automatisch deutsche Untertitel erzeugen (Phase 2),
Farbgrading und beat-synchrone Effekte anwenden, und bei mehreren Takes einen
automatischen, taktgenauen Schnitt zwischen ihnen erzeugen lassen (Phase 3).

**Was dieses Tool NICHT macht:** Es gibt kein KI-generiertes Lip-Sync - das ist
hier unnoetig, weil deine Lippen beim Filmen bereits zum abgespielten Song
passen. Das Tool synchronisiert nur die Audiospur zeitlich exakt ueber dein
Video.
"""

LIMITATIONS_MD = """
**Bekannte Grenzen:**
- Keine automatische Drift-Korrektur bei abweichender Handy-Samplerate ueber
  laengere Videos - falls dir bei einem Export ein Auseinanderlaufen von Ton
  und Bild auffaellt, sag Bescheid, das wird dann gezielt nachgeruestet.
- Eine niedrige Konfidenz (siehe Zahlenfeld) bedeutet: Video-Ton war
  vermutlich zu leise/verzerrt fuer eine zuverlaessige Erkennung - bitte das
  Ergebnis manuell gegenpruefen.
- Whisper macht bei Rap-Slang/Dialekt Fehler - **immer die Korrekturtabelle
  pruefen, bevor du die Untertitel renderst.**
- Groessere Whisper-Modelle (medium/large-v3) sind auf reiner CPU-Rechenleistung
  langsamer, aber genauer als kleinere (tiny/base/small).
- Beat-Effekte/Farbgrading werden auf den taktgenau erkannten Schlaegen der
  jeweiligen Tonspur berechnet - bei sehr leiser/percussion-armer Musik kann
  die Takterkennung ungenau sein.
- Multi-Take-Schnitt braucht mindestens 2 erfolgreich synchronisierte Takes,
  die sich im Song ausreichend ueberlappen (gleiche Songstelle).
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
        entry: dict[str, Any] = {
            "name": Path(video_file).name, "project_id": project_id, "take_id": take_id,
            "words": None, "final_output_path": None, "effects_output_path": None,
            "upscaled_output_path": None,
        }
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


def _make_transcribe_handler(take_id: str):
    def _handler(
        model_size: str, language: str, current_results: list[dict[str, Any]],
        progress: gr.Progress = gr.Progress(),
    ) -> list[dict[str, Any]]:
        new_results = []
        for r in current_results:
            if r["take_id"] == take_id:
                progress(0, desc="Lade Whisper-Modell und transkribiere...")
                try:
                    words = transcribe(r["output_path"], language=language, model_size=model_size)
                except Exception as e:
                    raise gr.Error(f"Transkription fehlgeschlagen: {e}")
                if not words:
                    raise gr.Error("Keine Woerter erkannt - ist im Video ueberhaupt Gesang/Sprache?")
                r = {**r, "words": [asdict(w) for w in words]}
            new_results.append(r)
        return new_results

    return _handler


def _make_effects_handler(take_id: str):
    def _handler(
        color_preset: str, zoom: float, flash: float, shake: float, rgb_split: float,
        current_results: list[dict[str, Any]],
        progress: gr.Progress = gr.Progress(),
    ) -> list[dict[str, Any]]:
        new_results = []
        for r in current_results:
            if r["take_id"] == take_id:
                progress(0, desc="Takte erkennen und Effekte rendern...")
                try:
                    beats = detect_beats(r["output_path"])
                    take_dir = storage.take_dir(r["project_id"], take_id)
                    effects_path = take_dir / "output_with_effects.mp4"
                    render_with_beat_effects(
                        r["output_path"], beats.beat_times_sec, effects_path,
                        color_preset=None if color_preset == "keins" else color_preset,
                        effects=BeatEffectConfig(
                            zoom=zoom or None, flash=flash or None,
                            shake=shake or None, rgb_split=rgb_split or None,
                        ),
                    )
                except Exception as e:
                    raise gr.Error(f"Effekt-Rendering fehlgeschlagen: {e}")
                r = {**r, "effects_output_path": str(effects_path)}
            new_results.append(r)
        return new_results

    return _handler


def _best_source_path(entry: dict[str, Any]) -> str:
    return entry.get("effects_output_path") or entry.get("final_output_path") or entry["output_path"]


def _make_upscale_handler(take_id: str):
    def _handler(
        scale: int, current_results: list[dict[str, Any]], progress: gr.Progress = gr.Progress(),
    ) -> list[dict[str, Any]]:
        new_results = []
        for r in current_results:
            if r["take_id"] == take_id:
                source = _best_source_path(r)

                def _cb(done: int, total: int, progress=progress) -> None:
                    progress(done / max(total, 1), desc=f"Upscaling: Frame {done}/{total}")

                try:
                    take_dir = storage.take_dir(r["project_id"], take_id)
                    upscaled_path = take_dir / "output_upscaled.mp4"
                    upscale_video(source, upscaled_path, scale=scale, progress_cb=_cb)
                except Exception as e:
                    raise gr.Error(f"Upscaling fehlgeschlagen: {e}")
                r = {**r, "upscaled_output_path": str(upscaled_path)}
            new_results.append(r)
        return new_results

    return _handler


def _make_burn_handler(take_id: str):
    def _handler(
        df_value: list[list[Any]], karaoke: bool, current_results: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        new_results = []
        for r in current_results:
            if r["take_id"] == take_id:
                try:
                    edited_words = [
                        Word(word=str(row[2]), start=float(row[0]), end=float(row[1]))
                        for row in df_value if str(row[2]).strip()
                    ]
                    if not edited_words:
                        raise gr.Error("Transkript ist leer - bitte mindestens ein Wort eingeben.")
                    lines = group_words_into_lines(edited_words)
                    take_dir = storage.take_dir(r["project_id"], take_id)
                    ass_path = take_dir / "subtitles.ass"
                    write_ass(lines, ass_path, karaoke=karaoke)
                    final_path = take_dir / "output_with_subs.mp4"
                    burn_subtitles(r["output_path"], ass_path, final_path)
                except gr.Error:
                    raise
                except Exception as e:
                    raise gr.Error(f"Untertitel-Rendering fehlgeschlagen: {e}")
                r = {**r, "final_output_path": str(final_path)}
            new_results.append(r)
        return new_results

    return _handler


def multitake_cut_handler(
    beat_interval: int, order_mode: str, current_results: list[dict[str, Any]],
    progress: gr.Progress = gr.Progress(),
) -> dict[str, Any] | None:
    usable = [r for r in current_results if not r.get("error")]
    if len(usable) < 2:
        raise gr.Error("Multi-Take-Schnitt braucht mindestens 2 erfolgreich synchronisierte Takes.")

    project_id = usable[0]["project_id"]
    project = db.get_project(project_id)
    if not project:
        raise gr.Error("Projekt nicht gefunden.")

    progress(0, desc="Takte im Song erkennen...")
    takes = [TakeInfo(video_path=r["output_path"], offset_ms=r["offset_ms"]) for r in usable]
    try:
        beats = detect_beats(project["song_path"])
        plan = compute_multitake_plan(takes, beats.beat_times_sec, beat_interval=beat_interval, order_mode=order_mode)
        out_path = storage.project_dir(project_id) / "multitake_cut.mp4"
        progress(0.3, desc="Takes zusammenschneiden...")
        render_multitake_cut(takes, project["song_path"], plan, out_path)
    except Exception as e:
        raise gr.Error(f"Multi-Take-Schnitt fehlgeschlagen: {e}")

    return {"output_path": str(out_path), "num_segments": len(plan)}


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
            take_id = entry["take_id"]
            with gr.Group():
                gr.Markdown(f"### {entry['name']}")
                if entry.get("error"):
                    gr.Markdown(f"```\n{entry['error']}\n```")
                    continue

                confidence = entry["confidence"]
                with gr.Row():
                    with gr.Column(scale=3):
                        gr.Video(value=entry["output_path"], label="Vorschau (Sync)")
                        gr.File(value=entry["output_path"], label="Download (ohne Untertitel)")
                    with gr.Column(scale=1, min_width=160):
                        gr.Number(value=round(entry["offset_ms"], 1), label="Zeitversatz (ms)", interactive=False)
                        gr.Number(value=round(confidence, 3), label="Konfidenz (0-1)", interactive=False)
                        if confidence < LOW_CONFIDENCE_THRESHOLD:
                            gr.Markdown("⚠️ Niedrige Konfidenz - Ergebnis manuell pruefen.")

                gr.Markdown("#### Untertitel (Phase 2)")
                with gr.Row():
                    model_size_dd = gr.Dropdown(choices=list(MODEL_SIZES), value=DEFAULT_MODEL_SIZE, label="Whisper-Modell")
                    language_dd = gr.Dropdown(choices=["de", "en"], value="de", label="Sprache")
                    transcribe_btn = gr.Button("Transkribieren")

                words = entry.get("words")
                if words:
                    gr.Markdown(
                        "**Bitte pruefen und korrigieren, bevor du die Untertitel renderst** "
                        "(Whisper macht bei Rap-Slang/Dialekt Fehler):"
                    )
                    words_df = gr.Dataframe(
                        value=[[w["start"], w["end"], w["word"]] for w in words],
                        headers=["Start (s)", "Ende (s)", "Wort"],
                        datatype=["number", "number", "str"],
                        type="array",
                        label="Transkript",
                    )
                    with gr.Row():
                        karaoke_cb = gr.Checkbox(value=True, label="Karaoke-Stil (aktuelles Wort hervorgehoben)")
                        burn_btn = gr.Button("Untertitel rendern", variant="primary")

                    burn_btn.click(
                        _make_burn_handler(take_id),
                        inputs=[words_df, karaoke_cb, results_state],
                        outputs=results_state,
                    )

                if entry.get("final_output_path"):
                    gr.Video(value=entry["final_output_path"], label="Vorschau mit Untertiteln")
                    gr.File(value=entry["final_output_path"], label="Download (mit Untertiteln)")

                transcribe_btn.click(
                    _make_transcribe_handler(take_id),
                    inputs=[model_size_dd, language_dd, results_state],
                    outputs=results_state,
                )

                gr.Markdown("#### Farbgrading & Beat-Effekte (Phase 3)")
                gr.Markdown(
                    "Taktschlaege werden auf dieser (bereits synchronisierten) Tonspur "
                    "erkannt. Intensitaet 0 = Effekt aus."
                )
                color_dd = gr.Dropdown(
                    choices=["keins"] + list(COLOR_PRESETS), value="keins", label="Farbpreset",
                )
                with gr.Row():
                    zoom_slider = gr.Slider(0, 1, value=0, step=0.05, label="Zoom-Pulse")
                    flash_slider = gr.Slider(0, 1, value=0, step=0.05, label="Flash")
                    shake_slider = gr.Slider(0, 1, value=0, step=0.05, label="Shake")
                    rgb_split_slider = gr.Slider(0, 1, value=0, step=0.05, label="RGB-Split-Kick")
                effects_btn = gr.Button("Effekte anwenden")

                if entry.get("effects_output_path"):
                    gr.Video(value=entry["effects_output_path"], label="Vorschau mit Effekten")
                    gr.File(value=entry["effects_output_path"], label="Download (mit Effekten)")

                effects_btn.click(
                    _make_effects_handler(take_id),
                    inputs=[color_dd, zoom_slider, flash_slider, shake_slider, rgb_split_slider, results_state],
                    outputs=results_state,
                )

                gr.Markdown("#### Upscaling (optional, Phase 3)")
                gr.Markdown(
                    "⚠️ **Kostet Rechenzeit** (auf reiner CPU ohne dedizierte GPU koennen es "
                    "leicht mehrere zehn Minuten bis Stunden pro Video werden, nicht nur ein "
                    "paar Minuten) und **erfindet keine neuen Bilddetails** - nur eine glaettere "
                    "Hochskalierung als einfache Interpolation. Wirkt auf die zuletzt erzeugte "
                    "Version (mit Effekten > mit Untertiteln > nur Sync)."
                )
                with gr.Row():
                    scale_radio = gr.Radio(choices=[2, 3, 4], value=2, label="Skalierungsfaktor")
                    upscale_btn = gr.Button("Hochskalieren")

                if entry.get("upscaled_output_path"):
                    gr.Video(value=entry["upscaled_output_path"], label="Vorschau hochskaliert")
                    gr.File(value=entry["upscaled_output_path"], label="Download (hochskaliert)")

                upscale_btn.click(
                    _make_upscale_handler(take_id),
                    inputs=[scale_radio, results_state],
                    outputs=results_state,
                )

    @gr.render(inputs=results_state)
    def show_multitake_section(results: list[dict[str, Any]]):
        usable = [r for r in results if not r.get("error")]
        if len(usable) < 2:
            return
        with gr.Group():
            gr.Markdown(
                "### Multi-Take-Schnitt (Phase 3)\n"
                f"{len(usable)} synchronisierte Takes gefunden - automatischer, taktgenauer "
                "Wechsel zwischen ihnen (kein Sprung im durchgehenden Songton, da alle Takes "
                "gegen denselben Song synchronisiert sind)."
            )
            with gr.Row():
                beat_interval_radio = gr.Radio(
                    choices=[("Jeden Takt", 1), ("Jeden 2. Takt", 2), ("Jeden 4. Takt", 4)],
                    value=1, label="Wechsel-Rhythmus",
                )
                order_radio = gr.Radio(
                    choices=[("Feste Reihenfolge", "fixed"), ("Zufaellig", "random")],
                    value="fixed", label="Take-Reihenfolge",
                )
            multitake_btn = gr.Button("Multi-Take-Schnitt erstellen", variant="primary")
            multitake_output = gr.State(None)
            multitake_btn.click(
                multitake_cut_handler,
                inputs=[beat_interval_radio, order_radio, results_state],
                outputs=multitake_output,
            )

            @gr.render(inputs=multitake_output)
            def show_multitake_result(result: dict[str, Any] | None):
                if not result:
                    return
                gr.Markdown(f"**{result['num_segments']} Segmente** geschnitten.")
                gr.Video(value=result["output_path"], label="Multi-Take-Schnitt")
                gr.File(value=result["output_path"], label="Download (Multi-Take-Schnitt)")

    gr.Markdown(LIMITATIONS_MD)


if __name__ == "__main__":
    demo.queue().launch()
