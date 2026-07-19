"""All-in-One-Orchestrator (Analyse -> Workspace -> render-fertig).

Fasst die Schritte zusammen, die spaeter der Assistent im Hintergrund macht:
1. Sync-Versatz des ganzen Videos berechnen (sync_offset)
2. optional: viralsten Hook suchen (hook_detect)
3. optional: Untertitel-Cues erzeugen (transcribe/subtitles)  [noch nicht verdrahtet]
4. render-fertigen FreeCut-Workspace bauen (freecut_workspace)

Der eigentliche Render (node editor/headless/render.mjs) laeuft danach - der
Aufrufer bekommt die render_args zurueck. Dieser Modul-Teil ist in der Sandbox
voll testbar; nur der Chrome-Render nicht.
"""
from __future__ import annotations

from pathlib import Path

from backend.pipeline.extract_audio import extract_audio
from backend.pipeline.freecut_workspace import build_workspace
from backend.pipeline.hook_detect import detect_hook
from backend.pipeline.sync_offset import compute_offset

CLAMP_TOLERANCE_SEC = 1.0


def _choose_hook(offset_sec: float, video_dur: float, best, alternatives) -> tuple[float, float] | None:
    """Erster Hook-Kandidat, der (mit 1s-Clamp) ins Video passt - gleiche
    Logik wie im Editor-Dialog (chooseHookWindow)."""
    for c in [best, *alternatives]:
        vstart, vend = c.start_sec - offset_sec, c.end_sec - offset_sec
        if vstart < 0:
            continue
        if vend <= video_dur:
            return (c.start_sec, c.end_sec)
        if vend - video_dur <= CLAMP_TOLERANCE_SEC:
            clamped_end = c.end_sec - (vend - video_dur)
            if clamped_end > c.start_sec + 3:
                return (c.start_sec, clamped_end)
    return None


def prepare_render(
    video_path: str | Path,
    song_path: str | Path,
    workspace_dir: str | Path,
    *,
    style_key: str = "clean",
    find_hook: bool = False,
    beat_effects: bool = False,
    width: int = 1080,
    height: int = 1920,
    fps: int = 30,
) -> dict:
    """Analyse + Workspace-Bau. Rueckgabe enthaelt project_id, render_args,
    offset_ms, und (falls gesucht) das Hook-Fenster."""
    work = Path(workspace_dir) / "_work_audio.wav"
    work.parent.mkdir(parents=True, exist_ok=True)
    extract_audio(str(video_path), work)
    offset = compute_offset(str(song_path), str(work))

    hook_start = hook_end = None
    if find_hook:
        from backend.pipeline.render_sync import _probe_duration_sec
        video_dur = _probe_duration_sec(str(video_path))
        result = detect_hook(str(song_path))
        chosen = _choose_hook(offset.offset_ms / 1000.0, video_dur, result.best, result.alternatives)
        if chosen:
            hook_start, hook_end = chosen

    info = build_workspace(
        workspace_dir, video_path, song_path,
        offset_ms=offset.offset_ms,
        hook_start_sec=hook_start, hook_end_sec=hook_end,
        style_key=style_key, width=width, height=height, fps=fps,
        beat_effects=beat_effects,
    )
    info["offset_ms"] = offset.offset_ms
    info["confidence"] = offset.confidence
    info["hook"] = {"start_sec": hook_start, "end_sec": hook_end} if hook_start is not None else None
    return info


def run_headless_render(editor_dir: str | Path, render_args: list[str], out_path: str | Path) -> None:
    """Ruft editor/headless/render.mjs (FreeCut headless, Node + Chrome).

    Kann in dieser Sandbox NICHT getestet werden (kein Chrome/WebGPU) - laeuft
    beim Nutzer. `--build` baut dist/ bei Bedarf einmalig selbst.
    """
    import subprocess
    editor_dir = Path(editor_dir)
    cmd = ["node", "headless/render.mjs", *render_args, "--build", "--out", str(out_path)]
    subprocess.run(cmd, cwd=str(editor_dir), check=True)


def _main() -> None:
    import argparse
    import json

    p = argparse.ArgumentParser(description="Analyse + render-fertigen Workspace bauen")
    p.add_argument("video")
    p.add_argument("song")
    p.add_argument("workspace")
    p.add_argument("--style", default="vibrant")
    p.add_argument("--find-hook", action="store_true")
    p.add_argument("--beat-effects", action="store_true",
                   help="Glitch-Puls auf jedem erkannten Taktschlag")
    p.add_argument("--render", action="store_true", help="Direkt via editor/headless rendern")
    p.add_argument("--editor-dir", default=str(Path(__file__).resolve().parents[2] / "editor"))
    p.add_argument("--out", default="hookcut_test.mp4")
    args = p.parse_args()

    info = prepare_render(args.video, args.song, args.workspace,
                          style_key=args.style, find_hook=args.find_hook,
                          beat_effects=args.beat_effects)
    print(json.dumps({k: v for k, v in info.items() if k != "render_args"}, indent=2))

    if args.render:
        out_abs = str(Path(args.out).resolve())
        print(f"\n>>> Rendern via FreeCut headless -> {out_abs}")
        run_headless_render(args.editor_dir, info["render_args"], out_abs)
        print(f"Fertig: {out_abs}")
    else:
        print("\n>>> Jetzt rendern (im Ordner editor/):")
        print("  node headless/render.mjs " + " ".join(info["render_args"]) + " --build --out ../hookcut_test.mp4")


if __name__ == "__main__":
    _main()
