"""Tests fuer den Meldeweg (DSA): melden, Liste des Betreibers, Entscheidung.

Der Ablauf ist Pflicht, sobald Fremde Inhalte hochladen - und er muss
vollstaendig sein: melden allein reicht nicht, es braucht auch eine
Reaktion, die den Inhalt tatsaechlich aus der Ansicht nimmt.
"""
from __future__ import annotations

import secrets
import uuid

from fastapi.testclient import TestClient

from backend import db
from backend.main import app
from tests.conftest import TEST_PASSWORD


def _beitrag(client, titel="Suche Refrain"):
    r = client.post("/posts", data={"title": titel, "categories": "refrain"})
    assert r.status_code == 200, r.text
    return r.json()["id"]


def _zum_admin(client) -> None:
    """Macht den eingeloggten Nutzer zum Admin (die Rechte-Vergabe selbst ist
    in test_account_admin.py geprueft)."""
    with db._connect(db.DEFAULT_DB_PATH) as conn:
        conn.execute("UPDATE users SET is_admin = 1 WHERE id = ?", (client.user["id"],))


def test_meldegruende_sind_abrufbar(client):
    r = client.get("/report-reasons")
    assert r.status_code == 200
    keys = [g["key"] for g in r.json()]
    assert "rechte" in keys  # der wichtigste Fall bei Musik: fremder Beat
    assert all(g["label"] for g in r.json())


def test_melden_und_ausblenden(auth_client, second_auth_client):
    post_id = _beitrag(auth_client)
    # Fremder meldet
    r = second_auth_client.post("/reports", data={
        "target_type": "post", "target_id": post_id,
        "reason": "rechte", "note": "Das ist mein Beat."})
    assert r.status_code == 200 and r.json()["neu"] is True

    # Der Betreiber sieht die Meldung samt Vorschau
    _zum_admin(auth_client)
    liste = auth_client.get("/admin/reports").json()
    meine = [m for m in liste if m["target_id"] == post_id]
    assert len(meine) == 1
    meldung = meine[0]
    assert meldung["reason"] == "rechte"
    assert meldung["note"] == "Das ist mein Beat."
    assert meldung["vorschau"] == "Suche Refrain"
    assert meldung["ziel_sichtbar"] is True

    # Entscheidung: ausblenden
    r = auth_client.post(f"/admin/reports/{meldung['id']}/handle",
                         data={"aktion": "ausblenden"})
    assert r.status_code == 200

    # Der Beitrag ist fuer alle weg ...
    assert second_auth_client.get(f"/posts/{post_id}").status_code == 404
    assert all(p["id"] != post_id
               for p in second_auth_client.get("/feed/discover").json())
    # ... und die Meldung ist abgearbeitet.
    assert all(m["id"] != meldung["id"] for m in auth_client.get("/admin/reports").json())


def test_behalten_laesst_den_beitrag_stehen(auth_client, second_auth_client):
    post_id = _beitrag(auth_client, "Bleibt stehen")
    second_auth_client.post("/reports", data={
        "target_type": "post", "target_id": post_id, "reason": "spam"})
    _zum_admin(auth_client)
    meldung = next(m for m in auth_client.get("/admin/reports").json()
                   if m["target_id"] == post_id)

    r = auth_client.post(f"/admin/reports/{meldung['id']}/handle",
                         data={"aktion": "behalten"})
    assert r.status_code == 200 and r.json()["status"] == "kept"
    assert second_auth_client.get(f"/posts/{post_id}").status_code == 200


def test_kommentar_melden_und_ausblenden(auth_client, second_auth_client):
    post_id = _beitrag(auth_client, "Mit Kommentar")
    k = second_auth_client.post(f"/posts/{post_id}/comments",
                                data={"body": "unangebrachter Text"})
    assert k.status_code == 200
    comment_id = k.json()["id"]

    r = auth_client.post("/reports", data={
        "target_type": "comment", "target_id": comment_id, "reason": "beleidigung"})
    assert r.status_code == 200

    _zum_admin(auth_client)
    meldung = next(m for m in auth_client.get("/admin/reports").json()
                   if m["target_id"] == comment_id)
    # Der Betreiber muss sehen, WORUM es geht, ohne erst nachzuschlagen.
    assert meldung["vorschau"] == "unangebrachter Text"
    assert meldung["post_id"] == post_id

    auth_client.post(f"/admin/reports/{meldung['id']}/handle",
                     data={"aktion": "ausblenden"})
    kommentare = second_auth_client.get(f"/posts/{post_id}/comments").json()
    assert all(k["id"] != comment_id for k in kommentare)


def test_doppelt_melden_ist_kein_fehler(auth_client, second_auth_client):
    post_id = _beitrag(auth_client, "Doppelt")
    erste = second_auth_client.post("/reports", data={
        "target_type": "post", "target_id": post_id, "reason": "spam"})
    zweite = second_auth_client.post("/reports", data={
        "target_type": "post", "target_id": post_id, "reason": "spam"})
    assert erste.status_code == 200 and erste.json()["neu"] is True
    # Zweiter Klick sieht fuer den Nutzer gleich aus, legt aber nichts Neues an.
    assert zweite.status_code == 200 and zweite.json()["neu"] is False

    _zum_admin(auth_client)
    assert len([m for m in auth_client.get("/admin/reports").json()
                if m["target_id"] == post_id]) == 1


def test_eine_entscheidung_schliesst_alle_meldungen(auth_client, second_auth_client):
    """Melden zwei Leute denselben Beitrag, ist das EINE Entscheidung -
    sonst bleiben nach dem Ausblenden Karteileichen in der Liste."""
    post_id = _beitrag(auth_client, "Von mehreren gemeldet")
    second_auth_client.post("/reports", data={
        "target_type": "post", "target_id": post_id, "reason": "spam"})

    # Dritter Melder mit EIGENEM Cookie-Speicher. Wichtig: die Fixtures
    # client und auth_client sind derselbe TestClient - wer sich darauf neu
    # registriert, wirft die Sitzung des Admins weg.
    with TestClient(app) as dritter:
        code = db.create_invite_code(f"test-{secrets.token_urlsafe(9)}")
        r = dritter.post("/auth/register", json={
            "invite_code": code, "email": f"dritt-{uuid.uuid4().hex[:8]}@example.com",
            "display_name": "Dritter", "password": TEST_PASSWORD})
        assert r.status_code == 200, r.text
        assert dritter.post("/reports", data={
            "target_type": "post", "target_id": post_id,
            "reason": "illegal"}).status_code == 200

    _zum_admin(auth_client)
    offen = [m for m in auth_client.get("/admin/reports").json()
             if m["target_id"] == post_id]
    assert len(offen) == 2
    auth_client.post(f"/admin/reports/{offen[0]['id']}/handle",
                     data={"aktion": "ausblenden"})
    assert not [m for m in auth_client.get("/admin/reports").json()
                if m["target_id"] == post_id]


def test_eigene_inhalte_meldet_man_nicht(auth_client):
    post_id = _beitrag(auth_client, "Meins")
    r = auth_client.post("/reports", data={
        "target_type": "post", "target_id": post_id, "reason": "spam"})
    assert r.status_code == 422


def test_unsinnige_meldungen_werden_abgewiesen(auth_client):
    post_id = _beitrag(auth_client, "Zielscheibe")
    # unbekannter Grund
    assert auth_client.post("/reports", data={
        "target_type": "post", "target_id": post_id,
        "reason": "gefaellt-mir-nicht"}).status_code == 422
    # unbekannte Art
    assert auth_client.post("/reports", data={
        "target_type": "profil", "target_id": post_id,
        "reason": "spam"}).status_code == 422
    # Ziel gibt es nicht
    assert auth_client.post("/reports", data={
        "target_type": "post", "target_id": "gibt-es-nicht",
        "reason": "spam"}).status_code == 404


def test_melden_braucht_ein_konto(client):
    assert client.post("/reports", data={
        "target_type": "post", "target_id": "x", "reason": "spam"}).status_code == 401


def test_meldeliste_ist_nur_fuer_den_betreiber(auth_client):
    """Die Liste enthaelt Namen von Meldenden und gemeldete Inhalte - das
    darf kein normales Mitglied sehen."""
    assert auth_client.get("/admin/reports").status_code == 403
    assert auth_client.post("/admin/reports/x/handle",
                            data={"aktion": "behalten"}).status_code == 403
