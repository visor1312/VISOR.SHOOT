"""GET /erstellt - eine Liste ueber alle Werkzeuge hinweg.

Die Ergebnisse liegen in fuenf Tabellen (edit_jobs, content_packs,
canvas_jobs, hook_jobs, projects). Fuer den Nutzer ist das eine kuenstliche
Trennung - er hat "Sachen gemacht". Diese Tests halten fest, dass die Liste
wirklich alle fuenf einsammelt, richtig sortiert und nichts Fremdes zeigt.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest

from backend import config, db


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def test_leeres_konto_bekommt_leere_liste(auth_client):
    assert auth_client.get("/erstellt").json() == []


def test_alle_fuenf_arten_tauchen_auf(auth_client):
    uid = auth_client.user["id"]
    db.create_edit_job(video_path="v.mp4", song_path="s.wav", with_subtitles=False,
                       user_id=uid)
    db.create_content_pack("v.mp4", "s.wav", with_subtitles=False, user_id=uid)
    db.create_canvas_job(video_path="v.mp4", song_path="s.wav", style="clean", duration_sec=5.0,
                         user_id=uid)
    db.create_hook_job(song_path="s.wav", user_id=uid)
    db.create_project(name="Mein Song", song_path="s.wav", user_id=uid)

    arten = {e["art"] for e in auth_client.get("/erstellt").json()}
    assert arten == {"reel", "pack", "canvas", "hook", "aufnahme"}


def test_neueste_zuerst(auth_client):
    uid = auth_client.user["id"]
    alt = db.create_project(name="Alt", song_path="s.wav", user_id=uid)
    neu = db.create_canvas_job(video_path="v.mp4", song_path="s.wav", style="clean",
                               duration_sec=5.0, user_id=uid)
    jetzt = datetime.now(timezone.utc)
    with db._connect(db.DEFAULT_DB_PATH) as conn:
        conn.execute("UPDATE projects SET created_at = ? WHERE id = ?",
                     (_iso(jetzt - timedelta(days=3)), alt))
        conn.execute("UPDATE canvas_jobs SET created_at = ? WHERE id = ?",
                     (_iso(jetzt), neu))
    liste = auth_client.get("/erstellt").json()
    ids = [e["id"] for e in liste]
    assert ids.index(neu) < ids.index(alt)


def test_fremde_sachen_bleiben_draussen(auth_client, second_auth_client):
    db.create_canvas_job(video_path="v.mp4", song_path="s.wav", style="clean", duration_sec=5.0,
                         user_id=auth_client.user["id"])
    fremd = second_auth_client.get("/erstellt").json()
    assert all(e["art"] != "canvas" for e in fremd)


def test_fertiges_reel_hat_einen_download(auth_client):
    job = db.create_edit_job(video_path="v.mp4", song_path="s.wav",
                             with_subtitles=False, user_id=auth_client.user["id"])
    db.update_edit_job(job, status="done", output_path="/tmp/final.mp4")
    eintrag = next(e for e in auth_client.get("/erstellt").json() if e["id"] == job)
    assert eintrag["status"] == "fertig"
    assert len(eintrag["downloads"]) == 1
    assert eintrag["downloads"][0]["url"] == f"/edit/{job}/download"


def test_unfertiges_hat_keinen_download(auth_client):
    job = db.create_edit_job(video_path="v.mp4", song_path="s.wav",
                             with_subtitles=False, user_id=auth_client.user["id"])
    eintrag = next(e for e in auth_client.get("/erstellt").json() if e["id"] == job)
    assert eintrag["status"] == "laeuft"
    assert eintrag["downloads"] == []


def test_pack_zaehlt_fertige_videos(auth_client):
    pack = db.create_content_pack("v.mp4", "s.wav", with_subtitles=False,
                                  user_id=auth_client.user["id"])
    db.update_content_pack(pack, hooks_json=json.dumps([{"start_sec": 1.0, "end_sec": 5.0}]))
    fertig = db.create_pack_item(pack, idx=0, hook_index=0, style_key="clean",
                                 platform="reel")
    db.create_pack_item(pack, idx=1, hook_index=0, style_key="vhs", platform="reel")
    db.update_pack_item(fertig, status="done", output_path="/tmp/item0.mp4")

    eintrag = next(e for e in auth_client.get("/erstellt").json() if e["id"] == pack)
    assert eintrag["detail"] == "1 von 2 Videos fertig"
    # Nur das fertige Video ist ladbar - ein Knopf fuer ein Video, das es
    # noch nicht gibt, waere eine Luege.
    assert [d["url"] for d in eintrag["downloads"]] == [f"/packs/{pack}/items/0/download"]


def test_fehlermeldung_wird_durchgereicht(auth_client):
    """Ohne den Text stuende da nur "Fehler" und niemand wuesste, woran es lag."""
    job = db.create_canvas_job(video_path="v.mp4", song_path="s.wav", style="clean",
                               duration_sec=5.0, user_id=auth_client.user["id"])
    db.update_canvas_job(job, status="error", error="Kein Hook im Video gefunden")
    eintrag = next(e for e in auth_client.get("/erstellt").json() if e["id"] == job)
    assert eintrag["status"] == "fehler"
    assert eintrag["fehler"] == "Kein Hook im Video gefunden"


def test_ohne_anmeldung_gesperrt(client):
    assert client.get("/erstellt").status_code == 401


def test_ohne_abo_weiter_sichtbar(auth_client, monkeypatch):
    """Was in der bezahlten Zeit entstanden ist, muss auffindbar bleiben -
    dieselbe Regel wie bei den Download-Routen."""
    monkeypatch.setattr(config, "PREMIUM_REQUIRED", True)
    db.create_canvas_job(video_path="v.mp4", song_path="s.wav", style="clean", duration_sec=5.0,
                         user_id=auth_client.user["id"])
    r = auth_client.get("/erstellt")
    assert r.status_code == 200 and len(r.json()) >= 1
