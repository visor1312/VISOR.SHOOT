"""Tests fuer die Musiker-Profile (oeffentliche Seite eines Kontos).

Profile sind die Grundlage des Netzwerks: ohne sie weiss niemand, wer da
postet. Entsprechend wird hier auch geprueft, was NICHT nach aussen darf.
"""
from __future__ import annotations

import pytest

from backend import auth, db
from tests.conftest import TEST_PASSWORD


def test_registration_creates_profile(tmp_path, monkeypatch):
    dbp = tmp_path / "p.db"
    db.init_db(dbp)
    monkeypatch.setattr(auth.config, "INVITE_ONLY", False)

    user = auth.register_user("", "a@example.com", "Yng Lyric", TEST_PASSWORD, db_path=dbp)
    profil = db.get_profile(user["id"], db_path=dbp)
    assert profil is not None
    # Umlaute/Leerzeichen fallen aus dem Kuerzel raus.
    assert profil["handle"] == "ynglyric"
    assert profil["artist_name"] == "Yng Lyric"


def test_handle_is_unique(tmp_path, monkeypatch):
    dbp = tmp_path / "p.db"
    db.init_db(dbp)
    monkeypatch.setattr(auth.config, "INVITE_ONLY", False)

    a = auth.register_user("", "a@example.com", "Beatmaker", TEST_PASSWORD, db_path=dbp)
    b = auth.register_user("", "b@example.com", "Beatmaker", TEST_PASSWORD, db_path=dbp)
    handles = {db.get_profile(a["id"], db_path=dbp)["handle"],
               db.get_profile(b["id"], db_path=dbp)["handle"]}
    assert handles == {"beatmaker", "beatmaker2"}


@pytest.mark.parametrize("name,erwartet", [
    ("Öz Görkem", "oezgoerkem"),
    ("!!! ???", "musiker"),      # nichts Verwertbares -> Ersatzname
    ("MC  Straße", "mcstrasse"),
])
def test_handle_generation(tmp_path, name, erwartet):
    dbp = tmp_path / "p.db"
    db.init_db(dbp)
    assert auth.make_handle(name, db_path=dbp) == erwartet


def test_ensure_profile_backfills_old_account(tmp_path):
    """Konten von vor den Profilen bekommen beim ersten Zugriff eins."""
    dbp = tmp_path / "p.db"
    db.init_db(dbp)
    user_id = db.create_user("alt@example.com", "Altes Konto", "hash", db_path=dbp)
    user = db.get_user_by_id(user_id, db_path=dbp)
    assert db.get_profile(user_id, db_path=dbp) is None

    profil = auth.ensure_profile(user, db_path=dbp)
    assert profil["handle"] == "alteskonto"
    # Zweiter Aufruf legt kein zweites an.
    assert auth.ensure_profile(user, db_path=dbp)["handle"] == "alteskonto"


def test_profile_me_and_update(auth_client):
    r = auth_client.get("/profiles/me")
    assert r.status_code == 200
    assert r.json()["artist_name"]

    r2 = auth_client.patch("/profiles/me", json={
        "artist_name": "Neuer Name",
        "bio": "Deutschrap aus Hamburg.",
        "city": "Hamburg",
        "genres": ["Deutschrap", "Trap"],
        "links": {"spotify": "https://open.spotify.com/artist/xyz"},
    })
    assert r2.status_code == 200
    body = r2.json()
    assert body["artist_name"] == "Neuer Name"
    assert body["genres"] == ["Deutschrap", "Trap"]
    assert body["links"]["spotify"].startswith("https://")


def test_profile_never_leaks_private_fields(auth_client):
    body = auth_client.get("/profiles/me").json()
    # E-Mail und Passwort-Hash gehoeren ins Konto, nicht ins oeffentliche Profil.
    assert "email" not in body
    assert "password_hash" not in body


def test_javascript_links_are_rejected(auth_client):
    """Ein `javascript:`-Link im Profil waere ein Einfallstor fuer jeden,
    der das Profil ansieht - er darf gar nicht erst gespeichert werden."""
    r = auth_client.patch("/profiles/me", json={
        "links": {"website": "javascript:alert(1)"},
    })
    assert r.status_code == 200
    assert "website" not in r.json()["links"]


def test_unknown_link_keys_are_dropped(auth_client):
    r = auth_client.patch("/profiles/me", json={
        "links": {"boeser_key": "https://example.com"},
    })
    assert r.json()["links"] == {}


def test_genres_are_capped_and_comma_safe(auth_client):
    r = auth_client.patch("/profiles/me", json={
        "genres": ["a", "b", "c", "d", "e", "f", "g"],
    })
    assert len(r.json()["genres"]) == auth.GENRES_MAX
    # Kommas im Genre wuerden die Spalte zerlegen -> werden ersetzt.
    r2 = auth_client.patch("/profiles/me", json={"genres": ["Rap,Trap"]})
    assert r2.json()["genres"] == ["Rap Trap"]


def test_empty_artist_name_rejected(auth_client):
    assert auth_client.patch("/profiles/me", json={"artist_name": "   "}).status_code == 422


def test_handle_cannot_be_changed_via_update(auth_client):
    vorher = auth_client.get("/profiles/me").json()["handle"]
    auth_client.patch("/profiles/me", json={"handle": "gekapert"})
    assert auth_client.get("/profiles/me").json()["handle"] == vorher


def test_foreign_profile_visible_but_unknown_is_404(auth_client):
    eigener = auth_client.get("/profiles/me").json()["handle"]
    assert auth_client.get(f"/profiles/{eigener}").status_code == 200
    assert auth_client.get("/profiles/gibtesnicht").status_code == 404


def test_profiles_require_login(client):
    assert client.get("/profiles/me").status_code == 401
    assert client.get("/profiles/irgendwer").status_code == 401
