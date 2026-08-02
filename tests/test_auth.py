"""Tests fuer das Benutzer-System: Registrierung, Login, Sessions, Lockout.

API-Tests laufen gegen die echte Default-DB (bestehendes Muster, einmalige
E-Mails pro Test); die Erster-User-wird-Admin-Logik wird deterministisch
gegen eine tmp_path-DB getestet.
"""
from __future__ import annotations

import secrets
import uuid

import pytest

from backend import auth, db
from tests.conftest import TEST_PASSWORD


def _unique_email() -> str:
    return f"test-{uuid.uuid4().hex[:10]}@example.com"


def _new_invite() -> str:
    return db.create_invite_code(f"test-{secrets.token_urlsafe(9)}")


def test_register_me_logout_flow(client):
    code = _new_invite()
    email = _unique_email()
    r = client.post("/auth/register", json={
        "invite_code": code, "email": email,
        "display_name": "Flow Tester", "password": TEST_PASSWORD,
    })
    assert r.status_code == 200
    body = r.json()
    assert body["email"] == email and body["display_name"] == "Flow Tester"
    assert "password" not in body and "password_hash" not in body

    me = client.get("/auth/me")
    assert me.status_code == 200 and me.json()["email"] == email

    assert client.post("/auth/logout").status_code == 200
    assert client.get("/auth/me").status_code == 401


def test_login_after_logout(auth_client):
    email = auth_client.user_email
    assert auth_client.post("/auth/logout").status_code == 200
    r = auth_client.post("/auth/login", json={"email": email, "password": TEST_PASSWORD})
    assert r.status_code == 200
    assert auth_client.get("/auth/me").status_code == 200


def test_register_requires_valid_invite(client):
    payload = {"invite_code": "gibt-es-nicht", "email": _unique_email(),
               "display_name": "X", "password": TEST_PASSWORD}
    assert client.post("/auth/register", json=payload).status_code == 400


def test_invite_single_use(client):
    code = _new_invite()
    first = {"invite_code": code, "email": _unique_email(),
             "display_name": "Erster", "password": TEST_PASSWORD}
    assert client.post("/auth/register", json=first).status_code == 200
    second = {"invite_code": code, "email": _unique_email(),
              "display_name": "Zweiter", "password": TEST_PASSWORD}
    assert client.post("/auth/register", json=second).status_code == 400


def test_invite_claim_is_atomic(tmp_path):
    """Einloesen gewinnt nur EINMAL - die Absicherung gegen zwei
    gleichzeitige Registrierungen mit demselben Code."""
    dbp = tmp_path / "state.db"
    db.init_db(dbp)
    user_a = db.create_user("a@example.com", "A", "hash", db_path=dbp)
    user_b = db.create_user("b@example.com", "B", "hash", db_path=dbp)
    code = db.create_invite_code("code-einmal", db_path=dbp)
    assert db.mark_invite_used(code, user_a, db_path=dbp) is True
    # Zweiter Zugriff auf denselben Code darf nicht durchgehen - und darf
    # den urspruenglichen Besitzer nicht ueberschreiben.
    assert db.mark_invite_used(code, user_b, db_path=dbp) is False
    assert db.get_invite_code(code, db_path=dbp)["used_by"] == user_a


def test_register_rolls_back_user_when_invite_lost(tmp_path, monkeypatch):
    """Schnappt sich jemand den Code GENAU zwischen Konto-Anlage und
    Einloesen, darf kein halbfertiges Konto zurueckbleiben.

    Der Zustand ist von aussen nicht herstellbar (die Vorab-Pruefung faengt
    einen laengst verbrauchten Code ab), deshalb wird hier das verlorene
    Rennen simuliert: mark_invite_used meldet False.
    """
    dbp = tmp_path / "state.db"
    db.init_db(dbp)
    code = db.create_invite_code("code-weg", db_path=dbp)
    monkeypatch.setattr(db, "mark_invite_used", lambda *a, **kw: False)

    before = db.count_users(db_path=dbp)
    with pytest.raises(auth.RegisterError):
        auth.register_user(code, "neu@example.com", "Neu", TEST_PASSWORD, db_path=dbp)
    assert db.get_user_by_email("neu@example.com", db_path=dbp) is None
    assert db.count_users(db_path=dbp) == before


def test_duplicate_email_case_insensitive(client):
    email = _unique_email()
    r = client.post("/auth/register", json={
        "invite_code": _new_invite(), "email": email,
        "display_name": "A", "password": TEST_PASSWORD,
    })
    assert r.status_code == 200
    r2 = client.post("/auth/register", json={
        "invite_code": _new_invite(), "email": email.upper(),
        "display_name": "B", "password": TEST_PASSWORD,
    })
    assert r2.status_code == 409


@pytest.mark.parametrize("bad_pw", ["kurz", "x" * 80, "ü" * 40])
def test_password_rules(client, bad_pw):
    r = client.post("/auth/register", json={
        "invite_code": _new_invite(), "email": _unique_email(),
        "display_name": "PW Test", "password": bad_pw,
    })
    assert r.status_code == 422


def test_wrong_password_unified_message(auth_client):
    email = auth_client.user_email
    auth_client.post("/auth/logout")
    r = auth_client.post("/auth/login", json={"email": email, "password": "falsch123"})
    assert r.status_code == 401
    assert r.json()["detail"] == "E-Mail oder Passwort falsch."
    # Unbekannte E-Mail: exakt dieselbe Meldung (kein User-Enumeration).
    r2 = auth_client.post("/auth/login",
                          json={"email": _unique_email(), "password": "falsch123"})
    assert r2.status_code == 401
    assert r2.json()["detail"] == r.json()["detail"]


def test_login_runs_hash_for_unknown_email(monkeypatch):
    """Timing-Schutz: auch bei unbekannter E-Mail wird ein bcrypt-Vergleich
    ausgefuehrt (gegen den Dummy-Hash), damit die Antwortzeit die Existenz
    eines Kontos nicht verraet."""
    calls = {"n": 0}
    real = auth.verify_password

    def counting_verify(pw, h):
        calls["n"] += 1
        return real(pw, h)

    monkeypatch.setattr(auth, "verify_password", counting_verify)
    try:
        auth.check_login("gibtesnicht@example.com", "irgendwas123",
                         db_path=auth.db.DEFAULT_DB_PATH)
    except auth.RegisterError:
        pass
    assert calls["n"] == 1  # bcrypt lief trotz unbekannter E-Mail


def test_login_lockout_after_five_failures(client):
    email = _unique_email()  # Lockout zaehlt auch fuer unbekannte Adressen
    for _ in range(5):
        r = client.post("/auth/login", json={"email": email, "password": "falsch123"})
        assert r.status_code == 401
    r = client.post("/auth/login", json={"email": email, "password": "falsch123"})
    assert r.status_code == 429


def test_session_cookie_is_httponly_and_hashed(client):
    code = _new_invite()
    r = client.post("/auth/register", json={
        "invite_code": code, "email": _unique_email(),
        "display_name": "Cookie Test", "password": TEST_PASSWORD,
    })
    set_cookie = r.headers["set-cookie"]
    assert "HttpOnly" in set_cookie and "SameSite=lax" in set_cookie
    token = client.cookies.get(auth.SESSION_COOKIE)
    assert token
    # In der DB liegt nur der Hash, nie das rohe Token.
    assert db.get_session(token) is None
    assert db.get_session(auth._hash_token(token)) is not None


def test_first_user_becomes_admin(tmp_path):
    dbp = tmp_path / "auth.db"
    db.init_db(dbp)
    db.create_invite_code("code-eins", db_path=dbp)
    db.create_invite_code("code-zwei", db_path=dbp)
    first = auth.register_user("code-eins", "a@example.com", "Erster",
                               TEST_PASSWORD, db_path=dbp)
    second = auth.register_user("code-zwei", "b@example.com", "Zweiter",
                                TEST_PASSWORD, db_path=dbp)
    assert first["is_admin"] == 1
    assert second["is_admin"] == 0


def test_expired_session_is_rejected(tmp_path):
    dbp = tmp_path / "auth.db"
    db.init_db(dbp)
    db.create_invite_code("code", db_path=dbp)
    user = auth.register_user("code", "c@example.com", "Ablauf",
                              TEST_PASSWORD, db_path=dbp)
    token = secrets.token_urlsafe(32)
    db.insert_session(auth._hash_token(token), user["id"],
                      "2000-01-01T00:00:00+00:00", db_path=dbp)
    assert auth.get_user_for_token(token, db_path=dbp) is None
    # abgelaufene Session wurde dabei geloescht
    assert db.get_session(auth._hash_token(token), db_path=dbp) is None
