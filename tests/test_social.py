"""Tests fuers Folgen (Verbindungen zwischen Musikern).

Nutzt die vorhandenen Fixtures auth_client + second_auth_client - zwei
unabhaengige Konten mit eigenem Cookie-Jar, genau fuer solche Faelle gedacht.
"""
from __future__ import annotations

from backend import db


def _handle(client) -> str:
    return client.get("/profiles/me").json()["handle"]


def test_follow_and_unfollow(auth_client, second_auth_client):
    a = _handle(auth_client)

    r = second_auth_client.post(f"/profiles/{a}/follow")
    assert r.status_code == 200
    assert r.json()["is_following"] is True
    assert r.json()["followers"] == 1

    # Aus Sicht von A: eine Person folgt mir, ich folge niemandem.
    eigen = auth_client.get("/profiles/me").json()
    assert eigen["followers"] == 1 and eigen["following"] == 0

    r2 = second_auth_client.delete(f"/profiles/{a}/follow")
    assert r2.status_code == 200
    assert r2.json()["is_following"] is False
    assert r2.json()["followers"] == 0


def test_following_twice_is_harmless(auth_client, second_auth_client):
    """Doppelklick auf "Folgen" darf keinen Fehler und keinen Doppeleintrag geben."""
    a = _handle(auth_client)
    second_auth_client.post(f"/profiles/{a}/follow")
    r = second_auth_client.post(f"/profiles/{a}/follow")
    assert r.status_code == 200
    assert r.json()["followers"] == 1


def test_unfollow_without_following_is_harmless(auth_client, second_auth_client):
    r = second_auth_client.delete(f"/profiles/{_handle(auth_client)}/follow")
    assert r.status_code == 200 and r.json()["is_following"] is False


def test_cannot_follow_self(auth_client):
    assert auth_client.post(f"/profiles/{_handle(auth_client)}/follow").status_code == 422


def test_own_profile_marks_is_self(auth_client):
    eigen = auth_client.get("/profiles/me").json()
    assert eigen["is_self"] is True
    assert eigen["is_following"] is False


def test_follow_unknown_handle_is_404(auth_client):
    assert auth_client.post("/profiles/gibtesnicht/follow").status_code == 404


def test_follow_requires_login(client):
    assert client.post("/profiles/irgendwer/follow").status_code == 401


def test_following_ids_helper(tmp_path):
    dbp = tmp_path / "f.db"
    db.init_db(dbp)
    a = db.create_user("a@example.com", "A", "h", db_path=dbp)
    b = db.create_user("b@example.com", "B", "h", db_path=dbp)
    c = db.create_user("c@example.com", "C", "h", db_path=dbp)

    db.follow(a, b, db_path=dbp)
    db.follow(a, c, db_path=dbp)
    assert sorted(db.following_ids(a, db_path=dbp)) == sorted([b, c])
    assert db.follow_counts(b, db_path=dbp) == {"followers": 1, "following": 0}
    assert db.follow_counts(a, db_path=dbp) == {"followers": 0, "following": 2}
