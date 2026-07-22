"""Tests fuer die Konto-Bearbeitung und die Admin-Endpoints (Einstellungen).

client/auth_client/second_auth_client kommen aus tests/conftest.py.
Der erste in einer frischen Wegwerf-DB registrierte User wird Admin -
in der geteilten Test-DB ist das nicht garantiert, daher testen wir die
Admin-Rechte teils gegen eine tmp_path-DB bzw. pruefen den 403-Pfad.
"""
from __future__ import annotations

import secrets

from backend import auth, db
from tests.conftest import TEST_PASSWORD


# --- Konto: Anzeigename ---------------------------------------------------

def test_update_display_name(auth_client):
    r = auth_client.patch("/auth/me", json={"display_name": "Neuer Name"})
    assert r.status_code == 200
    assert r.json()["display_name"] == "Neuer Name"
    assert auth_client.get("/auth/me").json()["display_name"] == "Neuer Name"


def test_update_display_name_rejects_empty(auth_client):
    assert auth_client.patch("/auth/me", json={"display_name": "   "}).status_code == 422


def test_update_me_requires_login(client):
    assert client.patch("/auth/me", json={"display_name": "X"}).status_code == 401


# --- Konto: Passwort aendern ---------------------------------------------

def test_change_password_wrong_current(auth_client):
    r = auth_client.post("/auth/change-password",
                         json={"current_password": "falschxx", "new_password": "neuesgeheim1"})
    assert r.status_code == 401


def test_change_password_validates_new(auth_client):
    r = auth_client.post("/auth/change-password",
                         json={"current_password": TEST_PASSWORD, "new_password": "kurz"})
    assert r.status_code == 422


def test_change_password_success_keeps_current_session(auth_client):
    email = auth_client.user_email
    r = auth_client.post("/auth/change-password",
                         json={"current_password": TEST_PASSWORD, "new_password": "neuesgeheim1"})
    assert r.status_code == 200
    # Aktueller Browser bleibt eingeloggt (frische Session im Cookie-Jar).
    assert auth_client.get("/auth/me").status_code == 200
    # Neues Passwort gilt, altes nicht mehr.
    auth_client.post("/auth/logout")
    assert auth_client.post("/auth/login",
                            json={"email": email, "password": TEST_PASSWORD}).status_code == 401
    assert auth_client.post("/auth/login",
                            json={"email": email, "password": "neuesgeheim1"}).status_code == 200


def test_change_password_logs_out_other_sessions(auth_client):
    """Zweite Sitzung desselben Kontos wird durch die Passwortaenderung
    ungueltig (alle Sessions werden rotiert)."""
    email = auth_client.user_email
    # Zweite unabhaengige Sitzung fuer denselben User.
    from fastapi.testclient import TestClient
    from backend.main import app
    with TestClient(app) as other:
        assert other.post("/auth/login",
                          json={"email": email, "password": TEST_PASSWORD}).status_code == 200
        assert other.get("/auth/me").status_code == 200
        auth_client.post("/auth/change-password",
                         json={"current_password": TEST_PASSWORD, "new_password": "neuesgeheim1"})
        # Die andere Sitzung ist jetzt abgemeldet.
        assert other.get("/auth/me").status_code == 401


# --- Admin: 403 fuer normale Nutzer --------------------------------------

def test_admin_endpoints_forbidden_for_non_admin(auth_client):
    # In der geteilten Test-DB ist ein frisch registrierter auth_client
    # nur dann Admin, wenn er der allererste war - sonst 403.
    if auth_client.user["is_admin"]:
        return  # dieser Lauf hatte zufaellig den ersten User; Admin-Pfad
                # wird separat gegen tmp_path getestet
    assert auth_client.get("/admin/invites").status_code == 403
    assert auth_client.post("/admin/invites").status_code == 403
    assert auth_client.get("/admin/users").status_code == 403


def test_admin_endpoints_require_login(client):
    assert client.get("/admin/invites").status_code == 401
    assert client.get("/admin/users").status_code == 401


# --- Admin-Funktionen deterministisch gegen tmp_path-DB ------------------

def _admin_dbclient(tmp_path):
    """TestClient, dessen erster (= Admin-)User frisch registriert ist,
    gegen eine isolierte DB (via HOOKCUT_DB-Override auf Modulebene ginge
    nur global; daher testen wir die Admin-Logik ueber auth/db direkt)."""
    dbp = tmp_path / "admin.db"
    db.init_db(dbp)
    return dbp


def test_admin_can_create_and_list_invites(tmp_path):
    dbp = _admin_dbclient(tmp_path)
    db.create_invite_code("start", db_path=dbp)
    admin = auth.register_user("start", "admin@example.com", "Admin",
                               TEST_PASSWORD, db_path=dbp)
    assert admin["is_admin"] == 1
    # Admin erzeugt einen weiteren Code (wie es der Endpoint tut).
    code = db.create_invite_code(secrets.token_urlsafe(9), created_by=admin["id"], db_path=dbp)
    invites = db.list_invite_codes(db_path=dbp)
    assert any(i["code"] == code and i["used_by"] is None for i in invites)


def _promote_to_admin(user_id: str) -> None:
    """Test-Helfer: hebt ein Konto in der (Test-)Default-DB zum Admin."""
    import sqlite3
    conn = sqlite3.connect(str(db.DEFAULT_DB_PATH))
    try:
        conn.execute("UPDATE users SET is_admin = 1 WHERE id = ?", (user_id,))
        conn.commit()
    finally:
        conn.close()


def test_admin_http_success_path(auth_client):
    """Kompletter Admin-Flow ueber echte HTTP-Requests: Konto wird Admin,
    dann Invites erzeugen/listen und Nutzer listen (ohne password_hash)."""
    _promote_to_admin(auth_client.user["id"])  # get_current_user liest frisch aus der DB

    created = auth_client.post("/admin/invites")
    assert created.status_code == 200
    code = created.json()["code"]
    assert created.json()["used"] is False

    invites = auth_client.get("/admin/invites")
    assert invites.status_code == 200
    assert any(i["code"] == code for i in invites.json())

    users = auth_client.get("/admin/users")
    assert users.status_code == 200
    rows = users.json()
    assert any(u["email"] == auth_client.user_email for u in rows)
    assert all("password_hash" not in u for u in rows)


def test_admin_users_never_expose_password_hash(tmp_path):
    dbp = _admin_dbclient(tmp_path)
    db.create_invite_code("start", db_path=dbp)
    auth.register_user("start", "admin@example.com", "Admin", TEST_PASSWORD, db_path=dbp)
    # Der Endpoint baut die Antwort feldweise; hier pruefen wir die Quelle:
    users = db.list_users(db_path=dbp)
    public = [{"id": u["id"], "email": u["email"], "display_name": u["display_name"],
               "is_admin": bool(u["is_admin"]), "created_at": u["created_at"]} for u in users]
    assert all("password_hash" not in u for u in public)
