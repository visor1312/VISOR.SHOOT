"""Tests fuer die Bremse gegen massenhaft angelegte Konten.

Sobald die Registrierung offen ist (HOOKCUT_INVITE_ONLY=0), kann sonst ein
Skript die Plattform in Minuten mit Konten fluten.

Der heikle Teil ist NICHT das Zaehlen, sondern die Frage, WELCHE Adresse
gezaehlt wird: hinter Renders Proxy kommen alle Anfragen von derselben
Stelle, und die weitergereichte Adresse ist faelschbar. Dazu die Tests
weiter unten.
"""
from __future__ import annotations

import uuid

import pytest

from backend import auth, config, db
from tests.conftest import TEST_PASSWORD


@pytest.fixture(autouse=True)
def _bremse_zuruecksetzen():
    """Alle Tests hier teilen sich eine Wegwerf-DB (conftest.py). Ohne
    Zuruecksetzen zaehlen die Registrierungen des vorherigen Tests mit und
    das Limit schlaegt an der falschen Stelle an.

    init_db zuerst, weil das Schema sonst noch gar nicht steht: es entsteht
    beim Hochfahren der App, und dieses Fixture laeuft davor.
    """
    db.init_db(db.DEFAULT_DB_PATH)
    with db._connect(db.DEFAULT_DB_PATH) as conn:
        conn.execute("DELETE FROM signup_attempts")
    yield


def _registrieren(client, weitergereicht: str | None = None):
    kopf = {"X-Forwarded-For": weitergereicht} if weitergereicht is not None else None
    return client.post(
        "/auth/register",
        json={"invite_code": db.create_invite_code(f"c-{uuid.uuid4().hex[:8]}"),
              "email": f"bremse-{uuid.uuid4().hex[:10]}@example.com",
              "display_name": "Bremse", "password": TEST_PASSWORD},
        headers=kopf)


def test_zu_viele_konten_von_einer_adresse(client, monkeypatch):
    monkeypatch.setattr(config, "REGISTER_MAX_PER_HOUR", 3)
    for nummer in range(3):
        assert _registrieren(client).status_code == 200, f"Konto {nummer + 1}"
    r = _registrieren(client)
    assert r.status_code == 429
    assert "Anschluss" in r.json()["detail"]


def test_fehlversuche_zaehlen_nicht_mit(client, monkeypatch):
    """Wer sich beim Einladungscode vertippt, darf sich nicht selbst
    aussperren - gezaehlt werden nur gelungene Registrierungen."""
    monkeypatch.setattr(config, "REGISTER_MAX_PER_HOUR", 2)
    for _ in range(6):
        r = client.post("/auth/register", json={
            "invite_code": "gibt-es-nicht", "email": f"x-{uuid.uuid4().hex[:8]}@example.com",
            "display_name": "X", "password": TEST_PASSWORD})
        assert r.status_code == 400
    assert _registrieren(client).status_code == 200


def test_alte_eintraege_werden_weggeraeumt(tmp_path):
    """Adressen sind personenbezogen und duerfen nicht laenger liegen
    bleiben, als die Bremse sie braucht."""
    dbp = tmp_path / "bremse.db"
    db.init_db(dbp)
    db.record_signup("1.2.3.4", db_path=dbp)
    with db._connect(dbp) as conn:
        conn.execute("UPDATE signup_attempts SET created_at = '2000-01-01T00:00:00+00:00'")

    assert db.prune_signup_attempts("2020-01-01T00:00:00+00:00", db_path=dbp) == 1
    assert db.count_recent_signups("1.2.3.4", "1999-01-01T00:00:00+00:00", db_path=dbp) == 0


# --- Welche Adresse wird gezaehlt? ----------------------------------------

class _Anfrage:
    """Minimale Attrappe einer Anfrage - client_ip braucht nur diese zwei."""

    def __init__(self, gegenstelle: str, weitergereicht: str | None = None):
        self.client = type("C", (), {"host": gegenstelle})()
        self.headers = {} if weitergereicht is None else {"x-forwarded-for": weitergereicht}


def test_ohne_proxy_zaehlt_die_gegenstelle(monkeypatch):
    monkeypatch.setattr(config, "TRUST_PROXY", False)
    # Selbst wenn jemand die Kopfzeile mitschickt: ohne Proxy wird sie
    # ignoriert, sonst koennte sich jeder eine Adresse ausdenken.
    assert auth.client_ip(_Anfrage("10.0.0.1", "1.2.3.4")) == "10.0.0.1"


def test_hinter_dem_proxy_zaehlt_die_weitergereichte_adresse(monkeypatch):
    monkeypatch.setattr(config, "TRUST_PROXY", True)
    assert auth.client_ip(_Anfrage("10.0.0.1", "203.0.113.7")) == "203.0.113.7"


def test_gefaelschte_kopfzeile_gewinnt_nicht(monkeypatch):
    """Der Kern der Sache: X-Forwarded-For ist eine Liste, und der ERSTE
    Eintrag kann frei erfunden sein. Schickt ein Angreifer selbst eine
    Adresse mit, haengt der Proxy die echte HINTEN an. Wer vorne liest,
    zaehlt die Fantasie-Adresse - und jeder umgeht das Limit, indem er sie
    bei jeder Anfrage aendert."""
    monkeypatch.setattr(config, "TRUST_PROXY", True)
    getarnt = _Anfrage("10.0.0.1", "1.2.3.4, 203.0.113.7")
    assert auth.client_ip(getarnt) == "203.0.113.7"
    assert auth.client_ip(getarnt) != "1.2.3.4"


def test_leere_kopfzeile_faellt_auf_die_gegenstelle_zurueck(monkeypatch):
    monkeypatch.setattr(config, "TRUST_PROXY", True)
    assert auth.client_ip(_Anfrage("10.0.0.1", "")) == "10.0.0.1"
    assert auth.client_ip(_Anfrage("10.0.0.1")) == "10.0.0.1"


def test_limit_trennt_verschiedene_adressen(client, monkeypatch):
    """Hinter dem Proxy muss die Bremse pro Nutzer greifen, nicht fuer alle
    gemeinsam - sonst sperrt der erste Vielnutzer den Rest aus. Genau das
    ist der Fehler, den der Fahrplan als Fallstrick benannt hat."""
    monkeypatch.setattr(config, "TRUST_PROXY", True)
    monkeypatch.setattr(config, "REGISTER_MAX_PER_HOUR", 2)

    for _ in range(2):
        assert _registrieren(client, weitergereicht="198.51.100.1").status_code == 200
    assert _registrieren(client, weitergereicht="198.51.100.1").status_code == 429
    # Jemand anderes am selben Proxy darf weitermachen.
    assert _registrieren(client, weitergereicht="198.51.100.2").status_code == 200


@pytest.mark.parametrize("wert,erwartet", [("7", 7), ("0", 0), ("quatsch", 5), ("", 5)])
def test_env_int_faellt_auf_den_standard_zurueck(monkeypatch, wert, erwartet):
    """Eine vertippte Umgebungsvariable darf den Server nicht am Starten
    hindern - beim Hosting waere das ein Ausfall wegen eines Tippfehlers."""
    monkeypatch.setenv("HOOKCUT_TEST_ZAHL", wert)
    assert config._env_int("HOOKCUT_TEST_ZAHL", 5) == erwartet
