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
from typing import Any, Iterator, Optional, Sequence

from backend import config

# HOOKCUT_DB uebersteuert den DB-Pfad (wird beim Import gelesen). Genutzt von
# den Tests (tests/conftest.py), damit API-Tests NIE in die echte state.db
# schreiben - sonst wuerde z.B. der erste Test-User die Altdaten uebernehmen.
# Ohne diese Variable liegt die DB im Datenordner (config.PROJECTS_DIR): beim
# Hosting zeigt der auf die dauerhafte Festplatte, damit Konten und Beitraege
# ein Ausrollen ueberleben.
DEFAULT_DB_PATH = Path(
    os.environ.get("HOOKCUT_DB")
    or config.PROJECTS_DIR / "state.db"
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
    -- Standard 1 mit Absicht: Konten aus der Zeit vor der E-Mail-Pruefung
    -- (und alle, die ohne eingeschaltete Pruefung entstehen) gelten als
    -- bestaetigt. Ist die Pruefung an, setzt register_user ausdruecklich 0.
    email_verified INTEGER NOT NULL DEFAULT 1,
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

-- Offene Projekte ("mir fehlt noch ein Refrain") - der Kern des Netzwerks.
-- ACHTUNG, andere Sichtbarkeits-Regel als beim Rest: Beitraege darf JEDES
-- angemeldete Mitglied lesen (das ist der Zweck eines Feeds); aendern und
-- loeschen darf nur der Autor. Siehe _own_public() in main.py.
-- open_state = hat sich schon jemand gefunden? (Produkt-Zustand)
-- status     = Moderation (Betreiber kann ausblenden). Bewusst getrennt.
CREATE TABLE IF NOT EXISTS posts (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id),
    title TEXT NOT NULL,
    body TEXT NOT NULL DEFAULT '',
    genres TEXT NOT NULL DEFAULT '',
    bpm INTEGER,
    audio_path TEXT,
    audio_duration_sec REAL,
    open_state TEXT NOT NULL DEFAULT 'open',
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- Eigene Tabelle statt kommagetrennter Spalte: hiernach wird GEFILTERT
-- ("zeig mir alle, die einen Beat brauchen"). In einer Textspalte wuerde
-- die Suche nach 'beat' auch 'boombeat' treffen und keinen Index nutzen.
CREATE TABLE IF NOT EXISTS post_categories (
    post_id TEXT NOT NULL REFERENCES posts(id),
    category TEXT NOT NULL,
    PRIMARY KEY (post_id, category)
);

-- Wer folgt wem. Beide Spalten zusammen sind der Schluessel, damit doppeltes
-- Folgen gar nicht erst entstehen kann (INSERT OR IGNORE).
CREATE TABLE IF NOT EXISTS follows (
    follower_id TEXT NOT NULL REFERENCES users(id),
    followee_id TEXT NOT NULL REFERENCES users(id),
    created_at TEXT NOT NULL,
    PRIMARY KEY (follower_id, followee_id)
);

CREATE INDEX IF NOT EXISTS idx_follows_followee ON follows(followee_id);

-- "Ich kann helfen" an einem offenen Projekt. Beide Spalten als Schluessel:
-- zweimal draufdruecken kann keinen Doppeleintrag erzeugen.
CREATE TABLE IF NOT EXISTS post_interests (
    post_id TEXT NOT NULL REFERENCES posts(id),
    user_id TEXT NOT NULL REFERENCES users(id),
    created_at TEXT NOT NULL,
    PRIMARY KEY (post_id, user_id)
);

CREATE TABLE IF NOT EXISTS comments (
    id TEXT PRIMARY KEY,
    post_id TEXT NOT NULL REFERENCES posts(id),
    user_id TEXT NOT NULL REFERENCES users(id),
    body TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_comments_post ON comments(post_id, created_at);

-- Meldungen: jeder kann einen Beitrag oder Kommentar melden, der Betreiber
-- sieht die offenen Meldungen und entscheidet. Pflicht, sobald Fremde
-- Inhalte hochladen (DSA) - der Admin-Notaus allein reicht nicht.
-- UNIQUE(target_type, target_id, reporter_id): dieselbe Person meldet
-- denselben Inhalt nur einmal, sonst laesst sich die Liste zuspammen.
CREATE TABLE IF NOT EXISTS reports (
    id TEXT PRIMARY KEY,
    target_type TEXT NOT NULL,
    target_id TEXT NOT NULL,
    reporter_id TEXT NOT NULL REFERENCES users(id),
    reason TEXT NOT NULL,
    note TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'open',
    created_at TEXT NOT NULL,
    handled_at TEXT,
    handled_by TEXT REFERENCES users(id),
    UNIQUE(target_type, target_id, reporter_id)
);

CREATE INDEX IF NOT EXISTS idx_reports_status ON reports(status, created_at DESC);

-- Bremse gegen massenhaft angelegte Konten: eine Zeile je erfolgreicher
-- Registrierung, mit der Herkunftsadresse.
-- DATENSCHUTZ: Eine IP-Adresse ist ein personenbezogenes Datum. Sie steht
-- hier nur, solange die Bremse sie braucht - alles aelter als eine Stunde
-- wird bei jeder Registrierung weggeraeumt (prune_signup_attempts).
-- Rechtsgrundlage: berechtigtes Interesse an einem missbrauchsfreien
-- Dienst (Art. 6 Abs. 1 lit. f DSGVO); steht so in der Datenschutzerklaerung.
CREATE TABLE IF NOT EXISTS signup_attempts (
    ip TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_signup_attempts ON signup_attempts(ip, created_at);

-- Bestaetigungslinks fuer E-Mail-Adressen.
-- Wie bei den Sitzungen liegt hier NUR der SHA-256-Hash des Tokens: wer die
-- Datenbank in die Haende bekommt, kann damit keine fremde Adresse
-- bestaetigen. Ein Token gilt 24 Stunden und genau einmal.
CREATE TABLE IF NOT EXISTS email_tokens (
    token_hash TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id),
    expires_at TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_email_tokens_user ON email_tokens(user_id);

CREATE INDEX IF NOT EXISTS idx_posts_created ON posts(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_posts_user ON posts(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_post_categories ON post_categories(category, post_id);

-- Musiker-Profil: die OEFFENTLICHE Seite eines Kontos. Bewusst getrennt von
-- users - dort liegen E-Mail und Passwort-Hash, die nie jemand anderes sehen
-- darf. Was hier steht, ist fuer andere Musiker sichtbar.
-- handle = das Kuerzel in der Profil-Adresse (@name), eindeutig.
CREATE TABLE IF NOT EXISTS profiles (
    user_id TEXT PRIMARY KEY REFERENCES users(id),
    handle TEXT NOT NULL UNIQUE,
    artist_name TEXT NOT NULL,
    bio TEXT NOT NULL DEFAULT '',
    city TEXT NOT NULL DEFAULT '',
    genres TEXT NOT NULL DEFAULT '',
    links_json TEXT NOT NULL DEFAULT '{}',
    avatar_path TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- Wochen-Content / Content-Packs: EIN Song/Video -> viele fertige Posts
-- (Matrix aus Hook-Varianten x Styles x Formaten). Der Pack haelt die
-- gemeinsame Quelle + Analyse (Sync/Hook), jedes pack_item ist ein einzelner
-- Render-Auftrag. Wie alles per user_id gescoped.
CREATE TABLE IF NOT EXISTS content_packs (
    id TEXT PRIMARY KEY,
    user_id TEXT REFERENCES users(id),
    video_path TEXT NOT NULL,
    song_path TEXT NOT NULL,
    with_subtitles INTEGER NOT NULL DEFAULT 0,
    lyrics TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    offset_ms REAL,
    confidence REAL,
    hooks_json TEXT,          -- Liste der gewaehlten Hook-Fenster [{start,end}]
    error TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS pack_items (
    id TEXT PRIMARY KEY,
    pack_id TEXT NOT NULL REFERENCES content_packs(id),
    idx INTEGER NOT NULL,     -- Reihenfolge im Pack (0..n-1)
    hook_index INTEGER NOT NULL,
    style_key TEXT NOT NULL,
    platform TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    output_path TEXT,
    error TEXT,
    created_at TEXT NOT NULL
);

-- Spotify Canvas: kurzer (3-8s) stummer 9:16-Loop, der auf Spotify das Cover
-- ersetzt. Ein Canvas = ein Video-Ausschnitt am Hook, gestylt, ohne Ton.
CREATE TABLE IF NOT EXISTS canvas_jobs (
    id TEXT PRIMARY KEY,
    user_id TEXT REFERENCES users(id),
    video_path TEXT NOT NULL,
    song_path TEXT NOT NULL,
    style TEXT,
    duration_sec REAL NOT NULL DEFAULT 6,
    status TEXT NOT NULL DEFAULT 'pending',
    output_path TEXT,
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
        # WAL: bessere Nebenlaeufigkeit (Leser blockieren Schreiber nicht) -
        # wichtig fuers Hosting mit mehreren gleichzeitigen Anfragen. Die
        # Einstellung ist dauerhaft in der DB-Datei gespeichert.
        try:
            conn.execute("PRAGMA journal_mode=WAL")
        except sqlite3.OperationalError:
            pass  # z.B. read-only Dateisystem - dann bleibt es beim Default
        conn.executescript(SCHEMA)
        # Mini-Migration fuer bestehende DBs: CREATE IF NOT EXISTS ergaenzt
        # keine Spalten. ALTER TABLE wirft bei schon vorhandener Spalte einen
        # OperationalError - der ist dann erwartbar und wird ignoriert.
        # Bestehende Konten gelten als bestaetigt: sie stammen aus der Zeit
        # vor der Pruefung, und niemand soll sich ploetzlich nicht mehr
        # anmelden koennen, nur weil eine Spalte dazugekommen ist.
        try:
            conn.execute("ALTER TABLE users ADD COLUMN email_verified INTEGER NOT NULL DEFAULT 1")
        except sqlite3.OperationalError:
            pass
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
                is_admin: bool = False, email_verified: bool = True,
                db_path: str | Path = DEFAULT_DB_PATH) -> str:
    user_id = str(uuid.uuid4())
    with _connect(db_path) as conn:
        conn.execute(
            "INSERT INTO users (id, email, display_name, password_hash, is_admin, "
            "email_verified, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user_id, email, display_name, password_hash, 1 if is_admin else 0,
             1 if email_verified else 0, _now()),
        )
    return user_id


def delete_user(user_id: str, db_path: str | Path = DEFAULT_DB_PATH) -> None:
    """Nur fuer den Rueckbau einer angefangenen Registrierung (siehe
    auth.register_user): der Einladungscode wurde zwischendurch von jemand
    anderem verbraucht, also darf das halbfertige Konto nicht bestehen bleiben."""
    with _connect(db_path) as conn:
        conn.execute("DELETE FROM users WHERE id = ?", (user_id,))


def create_profile(user_id: str, handle: str, artist_name: str,
                   db_path: str | Path = DEFAULT_DB_PATH) -> None:
    now = _now()
    with _connect(db_path) as conn:
        conn.execute(
            "INSERT INTO profiles (user_id, handle, artist_name, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (user_id, handle, artist_name, now, now),
        )


def get_profile(user_id: str, db_path: str | Path = DEFAULT_DB_PATH) -> Optional[dict]:
    with _connect(db_path) as conn:
        row = conn.execute("SELECT * FROM profiles WHERE user_id = ?", (user_id,)).fetchone()
        return dict(row) if row else None


def get_profile_by_handle(handle: str, db_path: str | Path = DEFAULT_DB_PATH) -> Optional[dict]:
    with _connect(db_path) as conn:
        row = conn.execute("SELECT * FROM profiles WHERE handle = ?", (handle,)).fetchone()
        return dict(row) if row else None


def handle_exists(handle: str, db_path: str | Path = DEFAULT_DB_PATH) -> bool:
    with _connect(db_path) as conn:
        return conn.execute(
            "SELECT 1 FROM profiles WHERE handle = ?", (handle,)).fetchone() is not None


# Was am Profil geaendert werden darf. handle und user_id stehen bewusst NICHT
# drin: der Handle steckt in Profil-Adressen, ein stiller Wechsel wuerde
# fremde Links brechen (spaeter ggf. eigene Route mit Weiterleitung).
_PROFILE_FIELDS = ("artist_name", "bio", "city", "genres", "links_json", "avatar_path")


def update_profile(user_id: str, db_path: str | Path = DEFAULT_DB_PATH, **fields) -> None:
    erlaubt = {k: v for k, v in fields.items() if k in _PROFILE_FIELDS}
    if not erlaubt:
        return
    spalten = ", ".join(f"{k} = ?" for k in erlaubt)
    with _connect(db_path) as conn:
        conn.execute(
            f"UPDATE profiles SET {spalten}, updated_at = ? WHERE user_id = ?",
            (*erlaubt.values(), _now(), user_id),
        )


# --- Beitraege (offene Projekte) ------------------------------------------

def create_post(user_id: str, title: str, body: str = "", genres: str = "",
                bpm: int | None = None, categories: Sequence[str] = (),
                db_path: str | Path = DEFAULT_DB_PATH) -> str:
    post_id = str(uuid.uuid4())
    now = _now()
    with _connect(db_path) as conn:
        conn.execute(
            "INSERT INTO posts (id, user_id, title, body, genres, bpm, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (post_id, user_id, title, body, genres, bpm, now, now),
        )
        conn.executemany(
            "INSERT OR IGNORE INTO post_categories (post_id, category) VALUES (?, ?)",
            [(post_id, c) for c in categories],
        )
    return post_id


def get_post(post_id: str, db_path: str | Path = DEFAULT_DB_PATH) -> Optional[dict]:
    with _connect(db_path) as conn:
        row = conn.execute("SELECT * FROM posts WHERE id = ?", (post_id,)).fetchone()
        if not row:
            return None
        post = dict(row)
        post["categories"] = [
            r["category"] for r in conn.execute(
                "SELECT category FROM post_categories WHERE post_id = ? ORDER BY category",
                (post_id,)).fetchall()
        ]
        return post


# open_state/status stehen drin (erledigt-Schalter, Moderation), user_id nicht:
# der Autor eines Beitrags ist unveraenderlich.
_POST_FIELDS = ("title", "body", "genres", "bpm", "audio_path",
                "audio_duration_sec", "open_state", "status")


def update_post(post_id: str, db_path: str | Path = DEFAULT_DB_PATH, **fields) -> None:
    erlaubt = {k: v for k, v in fields.items() if k in _POST_FIELDS}
    if not erlaubt:
        return
    spalten = ", ".join(f"{k} = ?" for k in erlaubt)
    with _connect(db_path) as conn:
        conn.execute(
            f"UPDATE posts SET {spalten}, updated_at = ? WHERE id = ?",
            (*erlaubt.values(), _now(), post_id),
        )


def set_post_categories(post_id: str, categories: Sequence[str],
                        db_path: str | Path = DEFAULT_DB_PATH) -> None:
    with _connect(db_path) as conn:
        conn.execute("DELETE FROM post_categories WHERE post_id = ?", (post_id,))
        conn.executemany(
            "INSERT OR IGNORE INTO post_categories (post_id, category) VALUES (?, ?)",
            [(post_id, c) for c in categories],
        )


def delete_post(post_id: str, db_path: str | Path = DEFAULT_DB_PATH) -> None:
    """Raeumt alles mit weg, was am Beitrag haengt - sonst haelt der
    Fremdschluessel dagegen (PRAGMA foreign_keys = ON).

    Kommentare und Interessen MUESSEN mit: sobald jemand kommentiert oder
    Interesse gezeigt hatte, liess sich der Beitrag sonst gar nicht mehr
    loeschen (FOREIGN KEY constraint failed -> 500). Genau das ist der
    haeufige Fall, nicht der seltene.
    Meldungen zu diesem Beitrag gehen auch weg: sie zeigen ins Leere, und der
    Betreiber soll nur Offenes in seiner Liste haben.
    """
    with _connect(db_path) as conn:
        # Meldungen zuerst - auch die zu den Kommentaren, die gleich mit weg
        # sind, sonst zeigen sie hinterher ins Leere.
        conn.execute(
            "DELETE FROM reports WHERE (target_type = 'post' AND target_id = ?) "
            "   OR (target_type = 'comment' AND target_id IN "
            "       (SELECT id FROM comments WHERE post_id = ?))",
            (post_id, post_id))
        conn.execute("DELETE FROM comments WHERE post_id = ?", (post_id,))
        conn.execute("DELETE FROM post_interests WHERE post_id = ?", (post_id,))
        conn.execute("DELETE FROM post_categories WHERE post_id = ?", (post_id,))
        conn.execute("DELETE FROM posts WHERE id = ?", (post_id,))


def list_feed(viewer_id: str, *, only_following: bool = False,
              categories: Sequence[str] = (), genre: str = "",
              open_only: bool = True, before: str | None = None, limit: int = 20,
              db_path: str | Path = DEFAULT_DB_PATH) -> list[dict]:
    """Beitraege fuer den Feed, neueste zuerst.

    only_following=False ist die Entdecken-Ansicht (alle) - die Startansicht,
    denn wer neu ist, folgt noch niemandem und saehe sonst eine leere Seite.
    only_following=True zeigt eigene Beitraege plus die der gefolgten Profile.

    Das Autorenprofil kommt per JOIN mit, und die Kategorien werden fuer ALLE
    Treffer in einer zweiten Abfrage geholt - sonst waere es eine Abfrage pro
    Beitrag. Der JOIN darf hart sein (kein LEFT): create_post stellt sicher,
    dass jeder Autor ein Profil hat.
    """
    bedingungen = ["p.status = 'active'"]
    werte: list = []

    if open_only:
        bedingungen.append("p.open_state = 'open'")

    if only_following:
        erlaubt = following_ids(viewer_id, db_path=db_path) + [viewer_id]
        platzhalter = ",".join("?" for _ in erlaubt)
        bedingungen.append(f"p.user_id IN ({platzhalter})")
        werte.extend(erlaubt)

    if categories:
        platzhalter = ",".join("?" for _ in categories)
        bedingungen.append(
            f"p.id IN (SELECT post_id FROM post_categories WHERE category IN ({platzhalter}))")
        werte.extend(categories)

    if genre.strip():
        # Absichtlich Teiltreffer: "rap" soll auch "Deutschrap" finden.
        bedingungen.append("LOWER(p.genres) LIKE ?")
        werte.append(f"%{genre.strip().lower()}%")

    if before:
        bedingungen.append("p.created_at < ?")
        werte.append(before)

    werte.append(max(1, min(100, limit)))

    with _connect(db_path) as conn:
        rows = conn.execute(
            "SELECT p.*, "
            "       pr.handle, pr.artist_name, pr.bio, pr.city, pr.links_json, "
            "       pr.avatar_path, pr.genres AS author_genres, "
            "       pr.created_at AS author_created_at "
            "FROM posts p JOIN profiles pr ON pr.user_id = p.user_id "
            f"WHERE {' AND '.join(bedingungen)} "
            "ORDER BY p.created_at DESC LIMIT ?",
            werte,
        ).fetchall()
        beitraege = [dict(r) for r in rows]

        if beitraege:
            ids = [b["id"] for b in beitraege]
            platzhalter = ",".join("?" for _ in ids)
            kat_rows = conn.execute(
                f"SELECT post_id, category FROM post_categories WHERE post_id IN ({platzhalter})",
                ids).fetchall()
            nach_post: dict[str, list[str]] = {i: [] for i in ids}
            for r in kat_rows:
                nach_post[r["post_id"]].append(r["category"])
            for b in beitraege:
                b["categories"] = sorted(nach_post[b["id"]])
        return beitraege


def list_posts_by_user(user_id: str, limit: int = 50,
                       db_path: str | Path = DEFAULT_DB_PATH) -> list[dict]:
    """Beitraege einer Person (fuer die Profilseite) - auch erledigte."""
    with _connect(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM posts WHERE user_id = ? AND status = 'active' "
            "ORDER BY created_at DESC LIMIT ?",
            (user_id, max(1, min(100, limit)))).fetchall()
        beitraege = [dict(r) for r in rows]
        for b in beitraege:
            b["categories"] = [
                r["category"] for r in conn.execute(
                    "SELECT category FROM post_categories WHERE post_id = ? ORDER BY category",
                    (b["id"],)).fetchall()
            ]
        return beitraege


# --- Interesse & Kommentare -------------------------------------------------

def add_interest(post_id: str, user_id: str,
                 db_path: str | Path = DEFAULT_DB_PATH) -> None:
    """Idempotent - zweimal draufdruecken ist kein Fehler."""
    with _connect(db_path) as conn:
        conn.execute(
            "INSERT OR IGNORE INTO post_interests (post_id, user_id, created_at) "
            "VALUES (?, ?, ?)", (post_id, user_id, _now()))


def remove_interest(post_id: str, user_id: str,
                    db_path: str | Path = DEFAULT_DB_PATH) -> None:
    with _connect(db_path) as conn:
        conn.execute("DELETE FROM post_interests WHERE post_id = ? AND user_id = ?",
                     (post_id, user_id))


def list_interested(post_id: str, db_path: str | Path = DEFAULT_DB_PATH) -> list[dict]:
    """Wer hat Interesse - MIT Profil. Das ist der Kontaktweg: der Autor sieht
    die Profile und erreicht die Leute ueber deren hinterlegte Links."""
    with _connect(db_path) as conn:
        rows = conn.execute(
            "SELECT pr.* FROM post_interests i "
            "JOIN profiles pr ON pr.user_id = i.user_id "
            "WHERE i.post_id = ? ORDER BY i.created_at",
            (post_id,)).fetchall()
        return [dict(r) for r in rows]


def has_interest(post_id: str, user_id: str,
                 db_path: str | Path = DEFAULT_DB_PATH) -> bool:
    with _connect(db_path) as conn:
        return conn.execute(
            "SELECT 1 FROM post_interests WHERE post_id = ? AND user_id = ?",
            (post_id, user_id)).fetchone() is not None


def create_comment(post_id: str, user_id: str, body: str,
                   db_path: str | Path = DEFAULT_DB_PATH) -> str:
    comment_id = str(uuid.uuid4())
    with _connect(db_path) as conn:
        conn.execute(
            "INSERT INTO comments (id, post_id, user_id, body, created_at) "
            "VALUES (?, ?, ?, ?, ?)", (comment_id, post_id, user_id, body, _now()))
    return comment_id


def get_comment(comment_id: str, db_path: str | Path = DEFAULT_DB_PATH) -> Optional[dict]:
    with _connect(db_path) as conn:
        row = conn.execute("SELECT * FROM comments WHERE id = ?", (comment_id,)).fetchone()
        return dict(row) if row else None


def list_comments(post_id: str, db_path: str | Path = DEFAULT_DB_PATH) -> list[dict]:
    """Kommentare mit Autorenprofil (JOIN statt einer Abfrage pro Kommentar)."""
    with _connect(db_path) as conn:
        rows = conn.execute(
            "SELECT c.*, pr.handle, pr.artist_name, pr.bio, pr.city, pr.links_json, "
            "       pr.avatar_path, pr.genres AS author_genres, "
            "       pr.created_at AS author_created_at "
            "FROM comments c JOIN profiles pr ON pr.user_id = c.user_id "
            "WHERE c.post_id = ? AND c.status = 'active' ORDER BY c.created_at",
            (post_id,)).fetchall()
        return [dict(r) for r in rows]


def delete_comment(comment_id: str, db_path: str | Path = DEFAULT_DB_PATH) -> None:
    with _connect(db_path) as conn:
        conn.execute("DELETE FROM comments WHERE id = ?", (comment_id,))


def update_comment_status(comment_id: str, status: str,
                          db_path: str | Path = DEFAULT_DB_PATH) -> None:
    """Moderation: 'hidden' nimmt den Kommentar aus der Ansicht, ohne ihn zu
    loeschen - list_comments zeigt nur 'active'. Bewusst nicht loeschen: bei
    einer Beschwerde muss nachvollziehbar bleiben, worum es ging."""
    with _connect(db_path) as conn:
        conn.execute("UPDATE comments SET status = ? WHERE id = ?", (status, comment_id))


def post_counts(post_ids: Sequence[str],
                db_path: str | Path = DEFAULT_DB_PATH) -> dict[str, dict]:
    """Interesse- und Kommentarzahlen fuer VIELE Beitraege auf einmal -
    im Feed waere je eine Abfrage pro Beitrag eine unnoetige Bremse."""
    zaehler = {pid: {"interest_count": 0, "comment_count": 0} for pid in post_ids}
    if not post_ids:
        return zaehler
    platzhalter = ",".join("?" for _ in post_ids)
    with _connect(db_path) as conn:
        for r in conn.execute(
                f"SELECT post_id, COUNT(*) AS n FROM post_interests "
                f"WHERE post_id IN ({platzhalter}) GROUP BY post_id", list(post_ids)):
            zaehler[r["post_id"]]["interest_count"] = int(r["n"])
        for r in conn.execute(
                f"SELECT post_id, COUNT(*) AS n FROM comments "
                f"WHERE post_id IN ({platzhalter}) AND status = 'active' GROUP BY post_id",
                list(post_ids)):
            zaehler[r["post_id"]]["comment_count"] = int(r["n"])
    return zaehler


# --- Folgen -----------------------------------------------------------------

def follow(follower_id: str, followee_id: str,
           db_path: str | Path = DEFAULT_DB_PATH) -> None:
    """Idempotent: zweimal folgen ist kein Fehler, sondern egal."""
    with _connect(db_path) as conn:
        conn.execute(
            "INSERT OR IGNORE INTO follows (follower_id, followee_id, created_at) "
            "VALUES (?, ?, ?)",
            (follower_id, followee_id, _now()),
        )


def unfollow(follower_id: str, followee_id: str,
             db_path: str | Path = DEFAULT_DB_PATH) -> None:
    with _connect(db_path) as conn:
        conn.execute(
            "DELETE FROM follows WHERE follower_id = ? AND followee_id = ?",
            (follower_id, followee_id),
        )


def is_following(follower_id: str, followee_id: str,
                 db_path: str | Path = DEFAULT_DB_PATH) -> bool:
    with _connect(db_path) as conn:
        return conn.execute(
            "SELECT 1 FROM follows WHERE follower_id = ? AND followee_id = ?",
            (follower_id, followee_id)).fetchone() is not None


def follow_counts(user_id: str, db_path: str | Path = DEFAULT_DB_PATH) -> dict:
    """Wie viele folgen mir (followers) und wem folge ich (following)?"""
    with _connect(db_path) as conn:
        followers = conn.execute(
            "SELECT COUNT(*) AS n FROM follows WHERE followee_id = ?", (user_id,)).fetchone()["n"]
        following = conn.execute(
            "SELECT COUNT(*) AS n FROM follows WHERE follower_id = ?", (user_id,)).fetchone()["n"]
        return {"followers": int(followers), "following": int(following)}


def following_ids(follower_id: str, db_path: str | Path = DEFAULT_DB_PATH) -> list[str]:
    with _connect(db_path) as conn:
        rows = conn.execute(
            "SELECT followee_id FROM follows WHERE follower_id = ?", (follower_id,)).fetchall()
        return [r["followee_id"] for r in rows]


def count_recent_posts(user_id: str, since_iso: str,
                       db_path: str | Path = DEFAULT_DB_PATH) -> int:
    """Fuer die Spam-Bremse: wie viele Beitraege seit <since_iso>?"""
    with _connect(db_path) as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM posts WHERE user_id = ? AND created_at > ?",
            (user_id, since_iso)).fetchone()
        return int(row["n"])


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


def count_admins(db_path: str | Path = DEFAULT_DB_PATH) -> int:
    """Wie viele Konten koennen die Plattform noch verwalten? Wichtig vor dem
    Loeschen eines Kontos: ohne Admin bearbeitet niemand mehr Meldungen und
    niemand erzeugt mehr Einladungen."""
    with _connect(db_path) as conn:
        return int(conn.execute(
            "SELECT COUNT(*) FROM users WHERE is_admin = 1").fetchone()[0])


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


def mark_invite_used(code: str, user_id: str, db_path: str | Path = DEFAULT_DB_PATH) -> bool:
    """Loest den Code ein und liefert True, wenn das geklappt hat.

    Das "AND used_by IS NULL" ist die eigentliche Absicherung: SQLite fuehrt
    das UPDATE atomar aus, also kann von zwei gleichzeitigen Registrierungen
    mit demselben Code nur EINE gewinnen - die andere bekommt False. Ohne
    diese Bedingung haetten beide den Code verbraucht und es waeren zwei
    Konten aus einer Einladung entstanden.
    """
    with _connect(db_path) as conn:
        cur = conn.execute(
            "UPDATE invite_codes SET used_by = ?, used_at = ? "
            "WHERE code = ? AND used_by IS NULL",
            (user_id, _now(), code),
        )
        return cur.rowcount > 0


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


# ---------------------------------------------------------------------------
# Wochen-Content / Content-Packs (Matrix aus Hook x Style x Format)


def create_content_pack(video_path: str, song_path: str, with_subtitles: bool,
                        lyrics: str | None = None, user_id: str | None = None,
                        db_path: str | Path = DEFAULT_DB_PATH) -> str:
    pack_id = str(uuid.uuid4())
    with _connect(db_path) as conn:
        conn.execute(
            "INSERT INTO content_packs (id, video_path, song_path, with_subtitles, "
            "lyrics, status, user_id, created_at) VALUES (?, ?, ?, ?, ?, 'pending', ?, ?)",
            (pack_id, video_path, song_path, 1 if with_subtitles else 0,
             lyrics or None, user_id, _now()),
        )
    return pack_id


def update_content_pack(pack_id: str, db_path: str | Path = DEFAULT_DB_PATH, **fields: Any) -> None:
    if not fields:
        return
    allowed = {"video_path", "song_path", "status", "offset_ms", "confidence",
               "hooks_json", "error"}
    unknown = set(fields) - allowed
    if unknown:
        raise ValueError(f"Unbekannte Felder: {unknown}")
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    with _connect(db_path) as conn:
        conn.execute(f"UPDATE content_packs SET {set_clause} WHERE id = ?",
                     (*fields.values(), pack_id))


def get_content_pack(pack_id: str, db_path: str | Path = DEFAULT_DB_PATH) -> Optional[dict]:
    with _connect(db_path) as conn:
        row = conn.execute("SELECT * FROM content_packs WHERE id = ?", (pack_id,)).fetchone()
        return dict(row) if row else None


def list_content_packs(user_id: str, limit: int = 50,
                       db_path: str | Path = DEFAULT_DB_PATH) -> list[dict]:
    with _connect(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM content_packs WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]


def create_pack_item(pack_id: str, idx: int, hook_index: int, style_key: str,
                     platform: str, db_path: str | Path = DEFAULT_DB_PATH) -> str:
    item_id = str(uuid.uuid4())
    with _connect(db_path) as conn:
        conn.execute(
            "INSERT INTO pack_items (id, pack_id, idx, hook_index, style_key, platform, "
            "status, created_at) VALUES (?, ?, ?, ?, ?, ?, 'pending', ?)",
            (item_id, pack_id, idx, hook_index, style_key, platform, _now()),
        )
    return item_id


def update_pack_item(item_id: str, db_path: str | Path = DEFAULT_DB_PATH, **fields: Any) -> None:
    if not fields:
        return
    allowed = {"status", "output_path", "error"}
    unknown = set(fields) - allowed
    if unknown:
        raise ValueError(f"Unbekannte Felder: {unknown}")
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    with _connect(db_path) as conn:
        conn.execute(f"UPDATE pack_items SET {set_clause} WHERE id = ?",
                     (*fields.values(), item_id))


def get_pack_item(item_id: str, db_path: str | Path = DEFAULT_DB_PATH) -> Optional[dict]:
    with _connect(db_path) as conn:
        row = conn.execute("SELECT * FROM pack_items WHERE id = ?", (item_id,)).fetchone()
        return dict(row) if row else None


def list_pack_items(pack_id: str, db_path: str | Path = DEFAULT_DB_PATH) -> list[dict]:
    with _connect(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM pack_items WHERE pack_id = ? ORDER BY idx", (pack_id,)
        ).fetchall()
        return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Spotify Canvas (kurzer stummer 9:16-Loop)


def create_canvas_job(video_path: str, song_path: str, style: str | None,
                      duration_sec: float, user_id: str | None = None,
                      db_path: str | Path = DEFAULT_DB_PATH) -> str:
    job_id = str(uuid.uuid4())
    with _connect(db_path) as conn:
        conn.execute(
            "INSERT INTO canvas_jobs (id, video_path, song_path, style, duration_sec, "
            "status, user_id, created_at) VALUES (?, ?, ?, ?, ?, 'pending', ?, ?)",
            (job_id, video_path, song_path, style, duration_sec, user_id, _now()),
        )
    return job_id


def update_canvas_job(job_id: str, db_path: str | Path = DEFAULT_DB_PATH, **fields: Any) -> None:
    if not fields:
        return
    allowed = {"video_path", "song_path", "style", "status", "output_path", "error"}
    unknown = set(fields) - allowed
    if unknown:
        raise ValueError(f"Unbekannte Felder: {unknown}")
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    with _connect(db_path) as conn:
        conn.execute(f"UPDATE canvas_jobs SET {set_clause} WHERE id = ?",
                     (*fields.values(), job_id))


def get_canvas_job(job_id: str, db_path: str | Path = DEFAULT_DB_PATH) -> Optional[dict]:
    with _connect(db_path) as conn:
        row = conn.execute("SELECT * FROM canvas_jobs WHERE id = ?", (job_id,)).fetchone()
        return dict(row) if row else None


def list_canvas_jobs(user_id: str, limit: int = 50,
                     db_path: str | Path = DEFAULT_DB_PATH) -> list[dict]:
    with _connect(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM canvas_jobs WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]


# --- Meldungen (DSA: Nutzer melden, Betreiber entscheidet) ------------------

def create_report(target_type: str, target_id: str, reporter_id: str,
                  reason: str, note: str = "",
                  db_path: str | Path = DEFAULT_DB_PATH) -> Optional[str]:
    """Legt eine Meldung an.

    Der UNIQUE-Schluessel verhindert, dass jemand denselben Inhalt mehrfach
    in die Liste des Betreibers druecken kann. Zwei Faelle, die dabei
    auseinandergehalten werden muessen:

    * Es liegt schon eine OFFENE Meldung dieser Person vor -> nichts tun
      (None). Der zweite Klick ist ein Doppelklick, keine neue Information.
    * Die fruehere Meldung wurde bereits ENTSCHIEDEN -> wieder oeffnen, mit
      dem neuen Grund und der neuen Notiz. Ohne das koennte niemand denselben
      Inhalt je wieder melden - ein Beitrag laesst sich aber nach einer
      Entscheidung aendern. Die Meldung waere stillschweigend verschwunden,
      obwohl die Oberflaeche "Danke, ist angekommen" sagt.
    """
    report_id = str(uuid.uuid4())
    try:
        with _connect(db_path) as conn:
            conn.execute(
                "INSERT INTO reports (id, target_type, target_id, reporter_id, "
                "reason, note, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (report_id, target_type, target_id, reporter_id, reason, note, _now()))
        return report_id
    except sqlite3.IntegrityError:
        pass

    with _connect(db_path) as conn:
        vorhanden = conn.execute(
            "SELECT id, status FROM reports WHERE target_type = ? AND target_id = ? "
            "AND reporter_id = ?", (target_type, target_id, reporter_id)).fetchone()
        if not vorhanden or vorhanden["status"] == "open":
            return None
        conn.execute(
            "UPDATE reports SET status = 'open', reason = ?, note = ?, created_at = ?, "
            "handled_at = NULL, handled_by = NULL WHERE id = ?",
            (reason, note, _now(), vorhanden["id"]))
        return vorhanden["id"]


def get_report(report_id: str, db_path: str | Path = DEFAULT_DB_PATH) -> Optional[dict]:
    with _connect(db_path) as conn:
        row = conn.execute("SELECT * FROM reports WHERE id = ?", (report_id,)).fetchone()
        return dict(row) if row else None


def list_reports(status: str | None = "open", limit: int = 100,
                 db_path: str | Path = DEFAULT_DB_PATH) -> list[dict]:
    """Offene Meldungen zuerst - das ist die Arbeitsliste des Betreibers."""
    with _connect(db_path) as conn:
        if status:
            rows = conn.execute(
                "SELECT * FROM reports WHERE status = ? ORDER BY created_at DESC LIMIT ?",
                (status, limit)).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM reports ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]


def count_recent_reports(reporter_id: str, since_iso: str,
                         db_path: str | Path = DEFAULT_DB_PATH) -> int:
    """Spam-Bremse: auch das Melden selbst laesst sich missbrauchen."""
    with _connect(db_path) as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM reports WHERE reporter_id = ? AND created_at > ?",
            (reporter_id, since_iso)).fetchone()
        return int(row["n"])


def close_reports_for_target(target_type: str, target_id: str, status: str,
                             handled_by: str,
                             db_path: str | Path = DEFAULT_DB_PATH) -> int:
    """Eine Entscheidung gilt fuer ALLE Meldungen zu diesem Inhalt - sonst
    bleiben nach dem Ausblenden die Meldungen der anderen offen liegen."""
    with _connect(db_path) as conn:
        cur = conn.execute(
            "UPDATE reports SET status = ?, handled_at = ?, handled_by = ? "
            "WHERE target_type = ? AND target_id = ? AND status = 'open'",
            (status, _now(), handled_by, target_type, target_id))
        return cur.rowcount


def delete_user_completely(user_id: str,
                           db_path: str | Path = DEFAULT_DB_PATH) -> list[str]:
    """Konto und ALLES daran loeschen (DSGVO Art. 17).

    Gibt die IDs der geloeschten Beitraege zurueck, damit der Aufrufer die
    zugehoerigen Hoerproben von der Platte raeumen kann - die Datenbank
    kennt nur die Pfade, nicht das Dateisystem.

    Reihenfolge ist wichtig (PRAGMA foreign_keys = ON): erst alles, was auf
    den Nutzer zeigt, dann der Nutzer selbst.

    Bewusste Entscheidung beim Einladungscode: der Code bleibt als
    VERBRAUCHT stehen, nur der Verweis auf das Konto faellt weg. Sonst
    koennte man sich durch Loeschen und Neuanlegen unbegrenzt Einladungen
    zurueckholen.
    """
    with _connect(db_path) as conn:
        post_ids = [r["id"] for r in conn.execute(
            "SELECT id FROM posts WHERE user_id = ?", (user_id,)).fetchall()]

        # Meldungen: eigene, und alle zu eigenen Inhalten.
        conn.execute("DELETE FROM reports WHERE reporter_id = ?", (user_id,))
        conn.execute(
            "DELETE FROM reports WHERE (target_type = 'comment' AND target_id IN "
            "       (SELECT id FROM comments WHERE user_id = ?)) "
            "   OR (target_type = 'post' AND target_id IN "
            "       (SELECT id FROM posts WHERE user_id = ?))",
            (user_id, user_id))

        # Eigene Kommentare - und die Kommentare anderer unter den eigenen
        # Beitraegen (die Beitraege verschwinden ja).
        conn.execute("DELETE FROM comments WHERE user_id = ?", (user_id,))
        conn.execute(
            "DELETE FROM comments WHERE post_id IN (SELECT id FROM posts WHERE user_id = ?)",
            (user_id,))

        # Interesse: eigenes, und fremdes an den eigenen Beitraegen.
        conn.execute("DELETE FROM post_interests WHERE user_id = ?", (user_id,))
        conn.execute(
            "DELETE FROM post_interests WHERE post_id IN "
            "   (SELECT id FROM posts WHERE user_id = ?)", (user_id,))

        conn.execute(
            "DELETE FROM post_categories WHERE post_id IN "
            "   (SELECT id FROM posts WHERE user_id = ?)", (user_id,))
        conn.execute("DELETE FROM posts WHERE user_id = ?", (user_id,))

        # Folgen in BEIDE Richtungen.
        conn.execute("DELETE FROM follows WHERE follower_id = ? OR followee_id = ?",
                     (user_id, user_id))

        conn.execute("DELETE FROM profiles WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))

        # Einladungscodes: Verweis loesen, Code bleibt verbraucht.
        conn.execute("UPDATE invite_codes SET used_by = NULL WHERE used_by = ?", (user_id,))
        conn.execute("UPDATE invite_codes SET created_by = NULL WHERE created_by = ?",
                     (user_id,))
        # Meldungen, die dieses Konto als Betreiber bearbeitet hat.
        conn.execute("UPDATE reports SET handled_by = NULL WHERE handled_by = ?", (user_id,))

        # Login-Sperrzaehler haengt an der E-Mail, nicht an der ID.
        row = conn.execute("SELECT email FROM users WHERE id = ?", (user_id,)).fetchone()
        if row:
            conn.execute("DELETE FROM login_attempts WHERE email = ?", (row["email"],))
        conn.execute("DELETE FROM users WHERE id = ?", (user_id,))

    return post_ids


# --- Bremse gegen massenhaft angelegte Konten ------------------------------

def record_signup(ip: str, db_path: str | Path = DEFAULT_DB_PATH) -> None:
    with _connect(db_path) as conn:
        conn.execute("INSERT INTO signup_attempts (ip, created_at) VALUES (?, ?)",
                     (ip, _now()))


def count_recent_signups(ip: str, since_iso: str,
                         db_path: str | Path = DEFAULT_DB_PATH) -> int:
    with _connect(db_path) as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM signup_attempts WHERE ip = ? AND created_at > ?",
            (ip, since_iso)).fetchone()
        return int(row["n"])


def prune_signup_attempts(before_iso: str,
                          db_path: str | Path = DEFAULT_DB_PATH) -> int:
    """Alte Eintraege wegraeumen - Adressen sollen nicht laenger liegen
    bleiben, als die Bremse sie braucht."""
    with _connect(db_path) as conn:
        cur = conn.execute("DELETE FROM signup_attempts WHERE created_at <= ?",
                           (before_iso,))
        return cur.rowcount


# --- Bestaetigung der E-Mail-Adresse --------------------------------------

def insert_email_token(token_hash: str, user_id: str, expires_at: str,
                       db_path: str | Path = DEFAULT_DB_PATH) -> None:
    """Neuer Bestaetigungslink. Alte Links desselben Kontos verfallen dabei -
    sonst blieben beliebig viele gueltige Links im Umlauf, wenn jemand
    mehrfach auf "noch mal schicken" drueckt."""
    with _connect(db_path) as conn:
        conn.execute("DELETE FROM email_tokens WHERE user_id = ?", (user_id,))
        conn.execute(
            "INSERT INTO email_tokens (token_hash, user_id, expires_at, created_at) "
            "VALUES (?, ?, ?, ?)", (token_hash, user_id, expires_at, _now()))


def get_email_token(token_hash: str,
                    db_path: str | Path = DEFAULT_DB_PATH) -> Optional[dict]:
    with _connect(db_path) as conn:
        row = conn.execute("SELECT * FROM email_tokens WHERE token_hash = ?",
                           (token_hash,)).fetchone()
        return dict(row) if row else None


def delete_email_token(token_hash: str, db_path: str | Path = DEFAULT_DB_PATH) -> None:
    with _connect(db_path) as conn:
        conn.execute("DELETE FROM email_tokens WHERE token_hash = ?", (token_hash,))


def set_email_verified(user_id: str, db_path: str | Path = DEFAULT_DB_PATH) -> None:
    with _connect(db_path) as conn:
        conn.execute("UPDATE users SET email_verified = 1 WHERE id = ?", (user_id,))
