"""Gemeinsame Pfad-Konventionen fuer alle Dateien der Nutzer.

EINE Stelle fuer die Verzeichnisstruktur - Projekte, Takes, Hook-Jobs,
Content-Packs, Canvas und die Hoerproben des Netzwerks. Wer einen neuen
Ablageort braucht, ergaenzt ihn hier, statt Pfade selbst zusammenzubauen:
sonst landet beim Hosting etwas neben der dauerhaften Festplatte und ist
nach dem naechsten Ausrollen weg.
"""
from __future__ import annotations

from pathlib import Path

from backend import config

# Beim Hosting zeigt das auf die dauerhafte Festplatte (HOOKCUT_PROJECTS_DIR),
# lokal auf den projects/-Ordner im Projekt - siehe backend/config.py.
PROJECTS_ROOT: Path = config.PROJECTS_DIR


def project_dir(project_id: str) -> Path:
    return PROJECTS_ROOT / project_id


def take_dir(project_id: str, take_id: str) -> Path:
    return project_dir(project_id) / "takes" / take_id


def song_path(project_id: str, suffix: str) -> Path:
    return project_dir(project_id) / f"song{suffix}"


def take_video_path(project_id: str, take_id: str, suffix: str) -> Path:
    return take_dir(project_id, take_id) / f"video{suffix}"


def take_audio_path(project_id: str, take_id: str) -> Path:
    return take_dir(project_id, take_id) / "audio.wav"


def take_output_path(project_id: str, take_id: str) -> Path:
    return take_dir(project_id, take_id) / "output.mp4"


def hook_job_dir(job_id: str) -> Path:
    return PROJECTS_ROOT / "hooks" / job_id


def hook_song_path(job_id: str, suffix: str) -> Path:
    return hook_job_dir(job_id) / f"song{suffix}"


def hook_preview_path(job_id: str, index: int) -> Path:
    return hook_job_dir(job_id) / f"preview_{index}.mp3"


def analyze_job_dir(job_id: str) -> Path:
    return PROJECTS_ROOT / "analyze" / job_id


def analyze_video_path(job_id: str, suffix: str) -> Path:
    return analyze_job_dir(job_id) / f"video{suffix}"


def analyze_song_path(job_id: str, suffix: str) -> Path:
    return analyze_job_dir(job_id) / f"song{suffix}"


def edit_job_dir(job_id: str) -> Path:
    return PROJECTS_ROOT / "edit" / job_id


def edit_video_path(job_id: str, suffix: str) -> Path:
    return edit_job_dir(job_id) / f"video{suffix}"


def edit_song_path(job_id: str, suffix: str) -> Path:
    return edit_job_dir(job_id) / f"song{suffix}"


def edit_output_path(job_id: str, platform_key: str | None = None) -> Path:
    """Ohne platform_key: das alte Einzel-Layout (final.mp4, Bestandsjobs).
    Mit platform_key: eine Datei pro Zielformat (final_reel.mp4, ...)."""
    name = "final.mp4" if platform_key is None else f"final_{platform_key}.mp4"
    return edit_job_dir(job_id) / name


# --- Wochen-Content / Content-Packs ---------------------------------------

def pack_dir(pack_id: str) -> Path:
    return PROJECTS_ROOT / "packs" / pack_id


def pack_video_path(pack_id: str, suffix: str) -> Path:
    return pack_dir(pack_id) / f"video{suffix}"


def pack_song_path(pack_id: str, suffix: str) -> Path:
    return pack_dir(pack_id) / f"song{suffix}"


def pack_item_output_path(pack_id: str, item_idx: int) -> Path:
    return pack_dir(pack_id) / f"item_{item_idx}.mp4"


# --- Spotify Canvas -------------------------------------------------------

def canvas_dir(job_id: str) -> Path:
    return PROJECTS_ROOT / "canvas" / job_id


def canvas_video_path(job_id: str, suffix: str) -> Path:
    return canvas_dir(job_id) / f"video{suffix}"


def canvas_song_path(job_id: str, suffix: str) -> Path:
    return canvas_dir(job_id) / f"song{suffix}"


def canvas_output_path(job_id: str) -> Path:
    return canvas_dir(job_id) / "canvas.mp4"


# --- Netzwerk: Beitraege (offene Projekte) --------------------------------

def post_dir(post_id: str) -> Path:
    return PROJECTS_ROOT / "posts" / post_id


def post_audio_path(post_id: str, suffix: str) -> Path:
    """Hoerprobe eines Beitrags. Eine Datei pro Beitrag, Endung wie hochgeladen
    (die Positivliste steckt in main.py: POST_AUDIO_SUFFIXES)."""
    return post_dir(post_id) / f"audio{suffix}"
