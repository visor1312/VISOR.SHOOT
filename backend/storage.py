"""Gemeinsame Pfad-Konventionen fuer Projekt-/Take-Dateien.

Wird sowohl vom FastAPI-Backend (main.py) als auch vom Gradio-Frontend
(frontend/app.py) genutzt, damit beide dieselbe Verzeichnisstruktur unter
/projects/<project_id>/ verwenden.
"""
from __future__ import annotations

from pathlib import Path

PROJECTS_ROOT = Path(__file__).resolve().parent.parent / "projects"


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
