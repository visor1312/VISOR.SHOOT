"""Minimaler SQLite-Projektstatus: Projekte (Song + Metadaten) und Takes (einzelne
Video-Aufnahmen, die gegen den Song synchronisiert werden).

Bewusst ohne ORM - der Schema-Umfang rechtfertigt das nicht.
"""
from __future__ import annotations

import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Optional

# HOOKCUT_DB uebersteuert den DB-Pfad (wird beim Import gelesen). Genutzt von
# den Tests (tests/conftest.py), damit API-Tests NIE in die echte state.db
# schreiben - sonst wuerde z.B. der erste Test-User die Altdaten uebernehmen.
DEFAULT_DB_PATH = Path(
    os.environ.get("HOOKCUT_DB")
    or Path(__file__).resolve().parent.parent / "projects" / "state.db"
)

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

-- Benutzer-System (Login/Registrierung/Sessions). E-Mails werden im Code
-- normalisiert (strip().lower()) gespeichert, nicht per COLLATE NOCASE.
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    is_admin INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);

-- Session-Tokens liegen NUR als SHA-256-Hash in der DB: ein Leak der
-- state.db gibt keine gueltigen Sitzungen preis.
CREATE TABLE IF NOT EXISTS sessions (
    token_hash TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id),
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS invite_codes (
    code TEXT PRIMARY KEY,
    created_by TEXT,
    used_by TEXT REFERENCES users(id),
    used_at TEXT,
    created_at TEXT NOT NULL
);

-- Login-Lockout (5 Fehlversuche -> 15 min Sperre), pro E-Mail, auch fuer
-- unbekannte Adressen (kein User-Enumeration-Unterschied).
CREATE TABLE IF NOT EXISTS login_attempts (
    email TEXT PRIMARY KEY,
    fail_count INTEGER NOT NULL DEFAULT 0,
    locked_until TEXT,
    last_fail_at TEXT
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
        # Benutzer-System: Besitzer-Spalte auf allen Daten-Tabellen (nullable,
        # ohne FK - ALTER TABLE kann keine Constraints nachruesten). Zeilen mit
        # user_id NULL sind Altdaten und werden bei der ersten Registrierung
        # dem ersten Konto (= Admin) zugeschrieben, siehe claim_orphan_rows.
        for table in ("projects", "hook_jobs", "analyze_jobs", "edit_jobs"):
            try:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN user_id TEXT")
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


def create_project(name: str, song_path: str, user_id: str | None = None,
                   db_path: str | Path = DEFAULT_DB_PATH) -> str:
    project_id = str(uuid.uuid4())
    with _connect(db_path) as conn:
        conn.execute(
            "INSERT INTO projects (id, name, song_path, user_id, created_at) VALUES (?, ?, ?, ?, ?)",
            (project_id, name, song_path, user_id, _now()),
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


def create_hook_job(song_path: str, user_id: str | None = None,
                    db_path: str | Path = DEFAULT_DB_PATH) -> str:
    job_id = str(uuid.uuid4())
    with _connect(db_path) as conn:
        conn.execute(
            "INSERT INTO hook_jobs (id, song_path, status, user_id, created_at) VALUES (?, ?, 'pending', ?, ?)",
            (job_id, song_path, user_id, _now()),
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


def create_analyze_job(video_path: str, song_path: str, user_id: str | None = None,
                       db_path: str | Path = DEFAULT_DB_PATH) -> str:
    job_id = str(uuid.uuid4())
    with _connect(db_path) as conn:
        conn.execute(
            "INSERT INTO analyze_jobs (id, video_path, song_path, status, user_id, created_at) "
            "VALUES (?, ?, ?, 'pending', ?, ?)",
            (job_id, video_path, song_path, user_id, _now()),
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
                    lyrics: str | None = None, user_id: str | None = None,
                    db_path: str | Path = DEFAULT_DB_PATH) -> str:
    job_id = str(uuid.uuid4())
    with _connect(db_path) as conn:
        conn.execute(
            "INSERT INTO edit_jobs (id, video_path, song_path, with_subtitles, lyrics, status, user_id, created_at) "
            "VALUES (?, ?, ?, ?, ?, 'pending', ?, ?)",
            (job_id, video_path, song_path, 1 if with_subtitles else 0, lyrics or None, user_id, _now()),
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


def list_projects(user_id: str | None = None, db_path: str | Path = DEFAULT_DB_PATH) -> list[dict]:
    with _connect(db_path) as conn:
        if user_id is None:
            rows = conn.execute("SELECT * FROM projects ORDER BY created_at DESC").fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM projects WHERE user_id = ? ORDER BY created_at DESC", (user_id,)
            ).fetchall()
        return [dict(r) for r in rows]


def list_hook_jobs(limit: int = 10, user_id: str | None = None,
                   db_path: str | Path = DEFAULT_DB_PATH) -> list[dict]:
    with _connect(db_path) as conn:
        if user_id is None:
            rows = conn.execute(
                "SELECT * FROM hook_jobs ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM hook_jobs WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
                (user_id, limit),
            ).fetchall()
        return [dict(r) for r in rows]


def list_edit_jobs(user_id: str, limit: int = 20,
                   db_path: str | Path = DEFAULT_DB_PATH) -> list[dict]:
    with _connect(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM edit_jobs WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Benutzer-System: Users, Sessions, Einladungscodes, Login-Lockout


def create_user(email: str, display_name: str, password_hash: str,
                is_admin: bool = False, db_path: str | Path = DEFAULT_DB_PATH) -> str:
    user_id = str(uuid.uuid4())
    with _connect(db_path) as conn:
        conn.execute(
            "INSERT INTO users (id, email, display_name, password_hash, is_admin, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, email, display_name, password_hash, 1 if is_admin else 0, _now()),
        )
    return user_id


def get_user_by_email(email: str, db_path: str | Path = DEFAULT_DB_PATH) -> Optional[dict]:
    with _connect(db_path) as conn:
        row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        return dict(row) if row else None


def get_user_by_id(user_id: str, db_path: str | Path = DEFAULT_DB_PATH) -> Optional[dict]:
    with _connect(db_path) as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return dict(row) if row else None


def count_users(db_path: str | Path = DEFAULT_DB_PATH) -> int:
    with _connect(db_path) as conn:
        return int(conn.execute("SELECT COUNT(*) FROM users").fetchone()[0])


def list_users(db_path: str | Path = DEFAULT_DB_PATH) -> list[dict]:
    with _connect(db_path) as conn:
        rows = conn.execute("SELECT * FROM users ORDER BY created_at").fetchall()
        return [dict(r) for r in rows]


def set_user_password_hash(user_id: str, password_hash: str,
                           db_path: str | Path = DEFAULT_DB_PATH) -> None:
    with _connect(db_path) as conn:
        conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (password_hash, user_id))


def set_user_display_name(user_id: str, display_name: str,
                          db_path: str | Path = DEFAULT_DB_PATH) -> None:
    with _connect(db_path) as conn:
        conn.execute("UPDATE users SET display_name = ? WHERE id = ?", (display_name, user_id))


def claim_orphan_rows(user_id: str, db_path: str | Path = DEFAULT_DB_PATH) -> None:
    """Schreibt alle besitzerlosen Altdaten (user_id NULL) dem Konto zu.
    Wird genau einmal benutzt: bei der Registrierung des ERSTEN Kontos."""
    with _connect(db_path) as conn:
        for table in ("projects", "hook_jobs", "analyze_jobs", "edit_jobs"):
            conn.execute(f"UPDATE {table} SET user_id = ? WHERE user_id IS NULL", (user_id,))


def create_invite_code(code: str, created_by: str | None = None,
                       db_path: str | Path = DEFAULT_DB_PATH) -> str:
    with _connect(db_path) as conn:
        conn.execute(
            "INSERT INTO invite_codes (code, created_by, created_at) VALUES (?, ?, ?)",
            (code, created_by, _now()),
        )
    return code


def get_invite_code(code: str, db_path: str | Path = DEFAULT_DB_PATH) -> Optional[dict]:
    with _connect(db_path) as conn:
        row = conn.execute("SELECT * FROM invite_codes WHERE code = ?", (code,)).fetchone()
        return dict(row) if row else None


def mark_invite_used(code: str, user_id: str, db_path: str | Path = DEFAULT_DB_PATH) -> None:
    with _connect(db_path) as conn:
        conn.execute(
            "UPDATE invite_codes SET used_by = ?, used_at = ? WHERE code = ?",
            (user_id, _now(), code),
        )


def list_invite_codes(db_path: str | Path = DEFAULT_DB_PATH) -> list[dict]:
    with _connect(db_path) as conn:
        rows = conn.execute(
            "SELECT i.*, u.email AS used_by_email FROM invite_codes i "
            "LEFT JOIN users u ON u.id = i.used_by ORDER BY i.created_at"
        ).fetchall()
        return [dict(r) for r in rows]


def insert_session(token_hash: str, user_id: str, expires_at: str,
                   db_path: str | Path = DEFAULT_DB_PATH) -> None:
    now = _now()
    with _connect(db_path) as conn:
        conn.execute(
            "INSERT INTO sessions (token_hash, user_id, created_at, expires_at, last_seen_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (token_hash, user_id, now, expires_at, now),
        )


def get_session(token_hash: str, db_path: str | Path = DEFAULT_DB_PATH) -> Optional[dict]:
    with _connect(db_path) as conn:
        row = conn.execute("SELECT * FROM sessions WHERE token_hash = ?", (token_hash,)).fetchone()
        return dict(row) if row else None


def touch_session(token_hash: str, expires_at: str,
                  db_path: str | Path = DEFAULT_DB_PATH) -> None:
    with _connect(db_path) as conn:
        conn.execute(
            "UPDATE sessions SET expires_at = ?, last_seen_at = ? WHERE token_hash = ?",
            (expires_at, _now(), token_hash),
        )


def delete_session_row(token_hash: str, db_path: str | Path = DEFAULT_DB_PATH) -> None:
    with _connect(db_path) as conn:
        conn.execute("DELETE FROM sessions WHERE token_hash = ?", (token_hash,))


def delete_sessions_for_user(user_id: str, db_path: str | Path = DEFAULT_DB_PATH) -> None:
    with _connect(db_path) as conn:
        conn.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))


def delete_expired_sessions(now_iso: str, db_path: str | Path = DEFAULT_DB_PATH) -> None:
    with _connect(db_path) as conn:
        conn.execute("DELETE FROM sessions WHERE expires_at < ?", (now_iso,))


def get_login_attempt(email: str, db_path: str | Path = DEFAULT_DB_PATH) -> Optional[dict]:
    with _connect(db_path) as conn:
        row = conn.execute("SELECT * FROM login_attempts WHERE email = ?", (email,)).fetchone()
        return dict(row) if row else None


def record_login_failure(email: str, locked_until: str | None,
                         db_path: str | Path = DEFAULT_DB_PATH) -> None:
    with _connect(db_path) as conn:
        conn.execute(
            "INSERT INTO login_attempts (email, fail_count, locked_until, last_fail_at) "
            "VALUES (?, 1, ?, ?) "
            "ON CONFLICT(email) DO UPDATE SET fail_count = fail_count + 1, "
            "locked_until = excluded.locked_until, last_fail_at = excluded.last_fail_at",
            (email, locked_until, _now()),
        )


def reset_login_failures(email: str, db_path: str | Path = DEFAULT_DB_PATH) -> None:
    with _connect(db_path) as conn:
        conn.execute("DELETE FROM login_attempts WHERE email = ?", (email,))
