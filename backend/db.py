"""Minimaler SQLite-Projektstatus: Projekte (Song + Metadaten) und Takes (einzelne
Video-Aufnahmen, die gegen den Song synchronisiert werden).

Bewusst ohne ORM - der Schema-Umfang rechtfertigt das nicht.
"""
from __future__ import annotations

import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Optional

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "projects" / "state.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    song_path TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS takes (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id),
    video_path TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    offset_ms REAL,
    confidence REAL,
    original_audio_mode TEXT NOT NULL DEFAULT 'mute',
    preset TEXT,
    subtitles INTEGER,
    output_path TEXT,
    error TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS hook_jobs (
    id TEXT PRIMARY KEY,
    song_path TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    result_json TEXT,
    error TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS analyze_jobs (
    id TEXT PRIMARY KEY,
    video_path TEXT NOT NULL,
    song_path TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    result_json TEXT,
    error TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS edit_jobs (
    id TEXT PRIMARY KEY,
    video_path TEXT NOT NULL,
    song_path TEXT NOT NULL,
    with_subtitles INTEGER NOT NULL DEFAULT 0,
    lyrics TEXT,
    style TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    offset_ms REAL,
    confidence REAL,
    hook_start REAL,
    hook_end REAL,
    output_path TEXT,
    platforms TEXT,
    outputs_json TEXT,
    error TEXT,
    created_at TEXT NOT NULL
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def init_db(db_path: str | Path = DEFAULT_DB_PATH) -> None:
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with _connect(db_path) as conn:
        conn.executescript(SCHEMA)
        # Mini-Migration fuer bestehende DBs: CREATE IF NOT EXISTS ergaenzt
        # keine Spalten. ALTER TABLE wirft bei schon vorhandener Spalte einen
        # OperationalError - der ist dann erwartbar und wird ignoriert.
        for column_def in ("preset TEXT", "subtitles INTEGER"):
            try:
                conn.execute(f"ALTER TABLE takes ADD COLUMN {column_def}")
            except sqlite3.OperationalError:
                pass
        for column_def in ("lyrics TEXT", "platforms TEXT", "outputs_json TEXT"):
            try:
                conn.execute(f"ALTER TABLE edit_jobs ADD COLUMN {column_def}")
            except sqlite3.OperationalError:
                pass


@contextmanager
def _connect(db_path: str | Path = DEFAULT_DB_PATH) -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def create_project(name: str, song_path: str, db_path: str | Path = DEFAULT_DB_PATH) -> str:
    project_id = str(uuid.uuid4())
    with _connect(db_path) as conn:
        conn.execute(
            "INSERT INTO projects (id, name, song_path, created_at) VALUES (?, ?, ?, ?)",
            (project_id, name, song_path, _now()),
        )
    return project_id


def set_project_song_path(project_id: str, song_path: str, db_path: str | Path = DEFAULT_DB_PATH) -> None:
    with _connect(db_path) as conn:
        conn.execute("UPDATE projects SET song_path = ? WHERE id = ?", (song_path, project_id))


def create_take(
    project_id: str,
    video_path: str,
    original_audio_mode: str = "mute",
    db_path: str | Path = DEFAULT_DB_PATH,
) -> str:
    take_id = str(uuid.uuid4())
    with _connect(db_path) as conn:
        conn.execute(
            "INSERT INTO takes (id, project_id, video_path, status, original_audio_mode, created_at) "
            "VALUES (?, ?, ?, 'pending', ?, ?)",
            (take_id, project_id, video_path, original_audio_mode, _now()),
        )
    return take_id


def set_take_video_path(take_id: str, video_path: str, db_path: str | Path = DEFAULT_DB_PATH) -> None:
    with _connect(db_path) as conn:
        conn.execute("UPDATE takes SET video_path = ? WHERE id = ?", (video_path, take_id))


def update_take(take_id: str, db_path: str | Path = DEFAULT_DB_PATH, **fields: Any) -> None:
    if not fields:
        return
    allowed = {"status", "offset_ms", "confidence", "output_path", "error",
               "original_audio_mode", "preset", "subtitles"}
    unknown = set(fields) - allowed
    if unknown:
        raise ValueError(f"Unbekannte Felder: {unknown}")
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    with _connect(db_path) as conn:
        conn.execute(f"UPDATE takes SET {set_clause} WHERE id = ?", (*fields.values(), take_id))


def get_project(project_id: str, db_path: str | Path = DEFAULT_DB_PATH) -> Optional[dict]:
    with _connect(db_path) as conn:
        row = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
        return dict(row) if row else None


def get_take(take_id: str, db_path: str | Path = DEFAULT_DB_PATH) -> Optional[dict]:
    with _connect(db_path) as conn:
        row = conn.execute("SELECT * FROM takes WHERE id = ?", (take_id,)).fetchone()
        return dict(row) if row else None


def create_hook_job(song_path: str, db_path: str | Path = DEFAULT_DB_PATH) -> str:
    job_id = str(uuid.uuid4())
    with _connect(db_path) as conn:
        conn.execute(
            "INSERT INTO hook_jobs (id, song_path, status, created_at) VALUES (?, ?, 'pending', ?)",
            (job_id, song_path, _now()),
        )
    return job_id


def set_hook_job_song_path(job_id: str, song_path: str, db_path: str | Path = DEFAULT_DB_PATH) -> None:
    with _connect(db_path) as conn:
        conn.execute("UPDATE hook_jobs SET song_path = ? WHERE id = ?", (song_path, job_id))


def update_hook_job(job_id: str, db_path: str | Path = DEFAULT_DB_PATH, **fields: Any) -> None:
    if not fields:
        return
    allowed = {"status", "result_json", "error"}
    unknown = set(fields) - allowed
    if unknown:
        raise ValueError(f"Unbekannte Felder: {unknown}")
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    with _connect(db_path) as conn:
        conn.execute(f"UPDATE hook_jobs SET {set_clause} WHERE id = ?", (*fields.values(), job_id))


def get_hook_job(job_id: str, db_path: str | Path = DEFAULT_DB_PATH) -> Optional[dict]:
    with _connect(db_path) as conn:
        row = conn.execute("SELECT * FROM hook_jobs WHERE id = ?", (job_id,)).fetchone()
        return dict(row) if row else None


def create_analyze_job(video_path: str, song_path: str, db_path: str | Path = DEFAULT_DB_PATH) -> str:
    job_id = str(uuid.uuid4())
    with _connect(db_path) as conn:
        conn.execute(
            "INSERT INTO analyze_jobs (id, video_path, song_path, status, created_at) "
            "VALUES (?, ?, ?, 'pending', ?)",
            (job_id, video_path, song_path, _now()),
        )
    return job_id


def set_analyze_job_paths(job_id: str, video_path: str, song_path: str,
                          db_path: str | Path = DEFAULT_DB_PATH) -> None:
    with _connect(db_path) as conn:
        conn.execute("UPDATE analyze_jobs SET video_path = ?, song_path = ? WHERE id = ?",
                     (video_path, song_path, job_id))


def update_analyze_job(job_id: str, db_path: str | Path = DEFAULT_DB_PATH, **fields: Any) -> None:
    if not fields:
        return
    allowed = {"status", "result_json", "error"}
    unknown = set(fields) - allowed
    if unknown:
        raise ValueError(f"Unbekannte Felder: {unknown}")
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    with _connect(db_path) as conn:
        conn.execute(f"UPDATE analyze_jobs SET {set_clause} WHERE id = ?", (*fields.values(), job_id))


def get_analyze_job(job_id: str, db_path: str | Path = DEFAULT_DB_PATH) -> Optional[dict]:
    with _connect(db_path) as conn:
        row = conn.execute("SELECT * FROM analyze_jobs WHERE id = ?", (job_id,)).fetchone()
        return dict(row) if row else None


def create_edit_job(video_path: str, song_path: str, with_subtitles: bool,
                    lyrics: str | None = None, db_path: str | Path = DEFAULT_DB_PATH) -> str:
    job_id = str(uuid.uuid4())
    with _connect(db_path) as conn:
        conn.execute(
            "INSERT INTO edit_jobs (id, video_path, song_path, with_subtitles, lyrics, status, created_at) "
            "VALUES (?, ?, ?, ?, ?, 'pending', ?)",
            (job_id, video_path, song_path, 1 if with_subtitles else 0, lyrics or None, _now()),
        )
    return job_id


def update_edit_job(job_id: str, db_path: str | Path = DEFAULT_DB_PATH, **fields: Any) -> None:
    if not fields:
        return
    allowed = {"video_path", "song_path", "style", "status", "offset_ms", "confidence",
               "hook_start", "hook_end", "output_path", "platforms", "outputs_json", "error"}
    unknown = set(fields) - allowed
    if unknown:
        raise ValueError(f"Unbekannte Felder: {unknown}")
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    with _connect(db_path) as conn:
        conn.execute(f"UPDATE edit_jobs SET {set_clause} WHERE id = ?", (*fields.values(), job_id))


def get_edit_job(job_id: str, db_path: str | Path = DEFAULT_DB_PATH) -> Optional[dict]:
    with _connect(db_path) as conn:
        row = conn.execute("SELECT * FROM edit_jobs WHERE id = ?", (job_id,)).fetchone()
        return dict(row) if row else None


def list_takes(project_id: str, db_path: str | Path = DEFAULT_DB_PATH) -> list[dict]:
    with _connect(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM takes WHERE project_id = ? ORDER BY created_at", (project_id,)
        ).fetchall()
        return [dict(r) for r in rows]


def list_projects(db_path: str | Path = DEFAULT_DB_PATH) -> list[dict]:
    with _connect(db_path) as conn:
        rows = conn.execute("SELECT * FROM projects ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]


def list_hook_jobs(limit: int = 10, db_path: str | Path = DEFAULT_DB_PATH) -> list[dict]:
    with _connect(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM hook_jobs ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]
