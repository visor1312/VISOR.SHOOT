"""Gemeinsame Fixtures: TestClient + eingeloggte Clients fuers Benutzer-System.

WICHTIG: HOOKCUT_DB wird HIER gesetzt, BEVOR irgendein backend-Modul
importiert wird - alle API-Tests laufen damit gegen eine Wegwerf-DB statt
gegen die echte projects/state.db. (Sonst wuerde z.B. der erste Test-User
per Backfill die Altdaten des Betreibers uebernehmen.) Einmalige E-Mails
pro Test-User, weil die Wegwerf-DB pro pytest-Lauf geteilt wird. Der
httpx-Cookie-Jar des TestClient haelt die Session ueber Requests hinweg.
"""
from __future__ import annotations

import os
import secrets
import tempfile
import uuid
from pathlib import Path

os.environ.setdefault(
    "HOOKCUT_DB", str(Path(tempfile.mkdtemp(prefix="hookcut-tests-")) / "state.db"))

import pytest
from fastapi.testclient import TestClient

from backend import db
from backend.main import app

TEST_PASSWORD = "geheim123"


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


def _register(c: TestClient) -> TestClient:
    code = db.create_invite_code(f"test-{secrets.token_urlsafe(9)}")
    email = f"test-{uuid.uuid4().hex[:10]}@example.com"
    r = c.post("/auth/register", json={
        "invite_code": code, "email": email,
        "display_name": "Testuser", "password": TEST_PASSWORD,
    })
    assert r.status_code == 200, r.text
    c.user = r.json()  # type: ignore[attr-defined]  # praktisch fuer Ownership-Tests
    c.user_email = email  # type: ignore[attr-defined]
    return c


@pytest.fixture()
def auth_client(client):
    """Frisch registrierter, eingeloggter Client (client.user = User-Dict)."""
    return _register(client)


@pytest.fixture()
def second_auth_client():
    """Zweiter, unabhaengiger eingeloggter Client (eigener Cookie-Jar)."""
    with TestClient(app) as c:
        yield _register(c)
