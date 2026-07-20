"""Gemeinsame Fixtures: TestClient + eingeloggte Clients fuers Benutzer-System.

Die API-Tests laufen (bestehendes Muster) gegen die echte projects/state.db -
deshalb bekommt jeder Test-User eine einmalige E-Mail. Der httpx-Cookie-Jar
des TestClient haelt die Session ueber Requests hinweg.
"""
from __future__ import annotations

import secrets
import uuid

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
