"""Tests fuer die Datentrennung zwischen Benutzern (Ownership-Scoping).

Kernregel: fremde Ressourcen sind per 404 unsichtbar (kein Existenz-Orakel),
Listen zeigen nur eigene Eintraege. Der Legacy-Backfill (erstes Konto
uebernimmt Altdaten) wird deterministisch gegen eine tmp_path-DB getestet.
"""
from __future__ import annotations

from backend import auth, db
from tests.conftest import TEST_PASSWORD


def test_users_cannot_see_each_others_edit_jobs(auth_client, second_auth_client):
    r = auth_client.post("/edit/analyze",
                         files={"video": ("v.mp4", b"junk", "video/mp4"),
                                "song": ("s.wav", b"junk", "audio/wav")},
                         data={"with_subtitles": "false"})
    assert r.status_code == 200
    jid = r.json()["job_id"]

    # Besitzer sieht den Job, der andere Nutzer bekommt ueberall 404.
    assert auth_client.get(f"/edit/{jid}").status_code == 200
    assert second_auth_client.get(f"/edit/{jid}").status_code == 404
    assert second_auth_client.get(f"/edit/{jid}/download").status_code == 404
    assert second_auth_client.post(f"/edit/{jid}/hook").status_code == 404
    other_list = second_auth_client.get("/edit").json()
    assert all(j["job_id"] != jid for j in other_list)


def test_users_cannot_see_each_others_projects(auth_client, second_auth_client):
    r = auth_client.post("/projects",
                         data={"name": "Isolationstest"},
                         files={"song": ("s.wav", b"junk", "audio/wav")})
    assert r.status_code == 200
    pid = r.json()["project_id"]

    own = auth_client.get("/projects").json()
    assert any(p["id"] == pid for p in own)
    other = second_auth_client.get("/projects").json()
    assert all(p["id"] != pid for p in other)
    assert second_auth_client.get(f"/projects/{pid}/takes").status_code == 404
    assert second_auth_client.post(
        f"/projects/{pid}/takes",
        files={"video": ("v.mp4", b"junk", "video/mp4")}).status_code == 404


def test_hook_jobs_are_isolated(auth_client, second_auth_client):
    r = auth_client.post("/hooks/analyze",
                         files={"song": ("s.wav", b"junk", "audio/wav")})
    assert r.status_code == 200
    jid = r.json()["job_id"]
    assert second_auth_client.get(f"/hooks/{jid}").status_code == 404
    assert second_auth_client.get(f"/hooks/{jid}/preview/0").status_code == 404
    other = second_auth_client.get("/hooks").json()
    assert all(j["job_id"] != jid for j in other)


def test_first_user_claims_legacy_rows(tmp_path):
    """Altdaten (user_id NULL) gehen bei der ersten Registrierung an das
    erste Konto - danach gibt es keine besitzerlosen Zeilen mehr."""
    dbp = tmp_path / "legacy.db"
    db.init_db(dbp)
    # Altdaten anlegen, wie sie vor dem Benutzer-System entstanden waeren.
    legacy_project = db.create_project("Alt-Projekt", "song.wav", db_path=dbp)
    legacy_job = db.create_edit_job("v.mp4", "s.wav", with_subtitles=False, db_path=dbp)

    db.create_invite_code("erster-code", db_path=dbp)
    db.create_invite_code("zweiter-code", db_path=dbp)
    first = auth.register_user("erster-code", "owner@example.com", "Owner",
                               TEST_PASSWORD, db_path=dbp)
    assert first["is_admin"] == 1
    assert db.get_project(legacy_project, db_path=dbp)["user_id"] == first["id"]
    assert db.get_edit_job(legacy_job, db_path=dbp)["user_id"] == first["id"]

    # Der zweite User uebernimmt nichts (es gibt nichts Besitzerloses mehr).
    second = auth.register_user("zweiter-code", "zweiter@example.com", "Zweiter",
                                TEST_PASSWORD, db_path=dbp)
    assert second["is_admin"] == 0
    assert db.get_project(legacy_project, db_path=dbp)["user_id"] == first["id"]
