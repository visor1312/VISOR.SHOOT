"""Tests fuer "Konto loeschen" (DSGVO Art. 17) - und fuer das Loeschen
einzelner Beitraege, an dem es haengt.

Wer sich registrieren kann, muss auch wieder gehen koennen. Und "geloescht"
muss heissen: Konto weg, Inhalte weg, Dateien weg, Anmeldung nicht mehr
moeglich - nicht "aus der Ansicht genommen".
"""
from __future__ import annotations

import io
import wave

from backend import db, storage
from tests.conftest import TEST_PASSWORD


def _wav(sekunden: float = 1.0, rate: int = 8000) -> bytes:
    puffer = io.BytesIO()
    with wave.open(puffer, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(bytes(int(rate * sekunden) * 2))
    return puffer.getvalue()


def _beitrag(client, titel="Suche Refrain", mit_audio=False):
    dateien = {"audio": ("probe.wav", _wav(), "audio/wav")} if mit_audio else None
    r = client.post("/posts", data={"title": titel, "categories": "refrain"},
                    files=dateien)
    assert r.status_code == 200, r.text
    return r.json()["id"]


# --- Der Bug, der die Loeschung blockierte --------------------------------

def test_kommentierter_beitrag_laesst_sich_loeschen(auth_client, second_auth_client):
    """Regression: Fremdschluessel sind an (PRAGMA foreign_keys = ON). Wurde
    ein Beitrag kommentiert, scheiterte das Loeschen mit einem 500er - also
    genau dann, wenn der Beitrag Erfolg hatte."""
    post_id = _beitrag(auth_client, "Wird kommentiert")
    assert second_auth_client.post(f"/posts/{post_id}/comments",
                                   data={"body": "Kann ich machen"}).status_code == 200
    assert second_auth_client.post(f"/posts/{post_id}/interest").status_code == 200

    r = auth_client.delete(f"/posts/{post_id}")
    assert r.status_code == 200, r.text
    assert auth_client.get(f"/posts/{post_id}").status_code == 404


def test_geloeschter_beitrag_nimmt_meldungen_mit(auth_client, second_auth_client):
    """Sonst bleibt beim Betreiber eine Meldung liegen, die ins Leere zeigt."""
    post_id = _beitrag(auth_client, "Gemeldet und geloescht")
    second_auth_client.post("/reports", data={
        "target_type": "post", "target_id": post_id, "reason": "spam"})
    auth_client.delete(f"/posts/{post_id}")
    assert not [m for m in db.list_reports(None) if m["target_id"] == post_id]


# --- Konto loeschen --------------------------------------------------------

def test_konto_loeschen_raeumt_alles_weg(auth_client, second_auth_client):
    user_id = auth_client.user["id"]
    email = auth_client.user_email
    post_id = _beitrag(auth_client, "Verschwindet mit", mit_audio=True)
    ordner = storage.post_dir(post_id)
    assert ordner.exists()

    # Jemand anderes hinterlaesst Spuren am Beitrag - die muessen mit weg.
    second_auth_client.post(f"/posts/{post_id}/comments", data={"body": "Interessant"})
    second_auth_client.post(f"/posts/{post_id}/interest")

    r = auth_client.request("DELETE", "/auth/me", json={"password": TEST_PASSWORD})
    assert r.status_code == 200, r.text
    assert r.json()["geloeschte_beitraege"] == 1

    # Konto weg, Profil weg, Beitrag weg, Datei weg.
    assert db.get_user_by_id(user_id) is None
    assert db.get_profile(user_id) is None
    assert db.get_post(post_id) is None
    assert not ordner.exists()

    # Abgemeldet - und Anmelden geht nicht mehr.
    assert auth_client.get("/auth/me").status_code == 401
    assert auth_client.post("/auth/login",
                            json={"email": email, "password": TEST_PASSWORD}).status_code == 401

    # Fuer die anderen ist der Beitrag ebenfalls verschwunden.
    assert second_auth_client.get(f"/posts/{post_id}").status_code == 404


def test_konto_loeschen_braucht_das_passwort(auth_client):
    """Ein offenstehender Browser darf nicht reichen, um ein Konto samt
    aller Beitraege zu vernichten."""
    post_id = _beitrag(auth_client, "Bleibt bestehen")
    r = auth_client.request("DELETE", "/auth/me", json={"password": "falsch123"})
    assert r.status_code == 401
    # Nichts passiert: Konto und Beitrag stehen noch.
    assert auth_client.get("/auth/me").status_code == 200
    assert auth_client.get(f"/posts/{post_id}").status_code == 200


def test_konto_loeschen_braucht_anmeldung(client):
    assert client.request("DELETE", "/auth/me",
                          json={"password": TEST_PASSWORD}).status_code == 401


def test_kommentare_unter_fremden_beitraegen_verschwinden(auth_client, second_auth_client):
    """Loescht jemand sein Konto, gehen auch seine Kommentare unter FREMDEN
    Beitraegen weg - sonst blieben Wortmeldungen einer Person stehen, die es
    nicht mehr gibt (und der Feed faellt ueber das fehlende Profil)."""
    post_id = _beitrag(auth_client, "Bleibt stehen")
    second_auth_client.post(f"/posts/{post_id}/comments", data={"body": "Ich melde mich"})
    assert len(auth_client.get(f"/posts/{post_id}/comments").json()) == 1

    r = second_auth_client.request("DELETE", "/auth/me", json={"password": TEST_PASSWORD})
    assert r.status_code == 200

    # Der fremde Beitrag lebt weiter, der Kommentar ist weg.
    assert auth_client.get(f"/posts/{post_id}").status_code == 200
    assert auth_client.get(f"/posts/{post_id}/comments").json() == []


def test_folgen_verschwinden_in_beide_richtungen(auth_client, second_auth_client):
    """Ein geloeschtes Konto darf nirgends mehr als Folger oder Gefolgter
    haengen - sonst zeigen Zaehler und Feeds auf jemanden, den es nicht
    mehr gibt."""
    handle_a = auth_client.get("/profiles/me").json()["handle"]
    a_id = auth_client.user["id"]
    b_id = second_auth_client.user["id"]
    assert second_auth_client.post(f"/profiles/{handle_a}/follow").status_code == 200
    assert db.is_following(b_id, a_id) is True

    r = second_auth_client.request("DELETE", "/auth/me", json={"password": TEST_PASSWORD})
    assert r.status_code == 200

    # Direkt in der Tabelle nachsehen: die Zeile muss weg sein, egal in
    # welcher Richtung sie stand.
    with db._connect(db.DEFAULT_DB_PATH) as conn:
        uebrig = conn.execute(
            "SELECT COUNT(*) AS n FROM follows WHERE follower_id = ? OR followee_id = ?",
            (b_id, b_id)).fetchone()["n"]
    assert uebrig == 0


def test_einladungscode_bleibt_verbraucht(client, tmp_path):
    """Sonst holt man sich durch Loeschen und Neuanlegen unbegrenzt
    Einladungen zurueck."""
    dbp = tmp_path / "einladung.db"
    db.init_db(dbp)
    code = db.create_invite_code("einmal-nur", db_path=dbp)
    user_id = db.create_user("weg@example.com", "Weg", "hash", db_path=dbp)
    db.create_profile(user_id, "weg", "Weg", db_path=dbp)
    assert db.mark_invite_used(code, user_id, db_path=dbp) is True

    db.delete_user_completely(user_id, db_path=dbp)

    eintrag = db.get_invite_code(code, db_path=dbp)
    assert eintrag is not None, "der Code selbst darf nicht verschwinden"
    assert eintrag["used_by"] is None       # Verweis aufs Konto ist geloest
    assert eintrag["used_at"] is not None   # ... aber verbraucht bleibt verbraucht


def test_letzter_admin_kann_sich_nicht_loeschen(auth_client, second_auth_client):
    """Sonst bleibt eine Plattform ohne Verwaltung zurueck: niemand koennte
    mehr gemeldete Inhalte bearbeiten oder Einladungen erzeugen - und die
    "erstes Konto wird Admin"-Regel greift nicht, weil es ja Konten gibt."""
    with db._connect(db.DEFAULT_DB_PATH) as conn:
        # Genau ein Admin im System: dieser hier.
        conn.execute("UPDATE users SET is_admin = 0")
        conn.execute("UPDATE users SET is_admin = 1 WHERE id = ?", (auth_client.user["id"],))

    r = auth_client.request("DELETE", "/auth/me", json={"password": TEST_PASSWORD})
    assert r.status_code == 409
    assert "Administrator" in r.json()["detail"]
    assert auth_client.get("/auth/me").status_code == 200  # Konto lebt

    # Mit einem zweiten Admin geht es.
    with db._connect(db.DEFAULT_DB_PATH) as conn:
        conn.execute("UPDATE users SET is_admin = 1 WHERE id = ?",
                     (second_auth_client.user["id"],))
    r = auth_client.request("DELETE", "/auth/me", json={"password": TEST_PASSWORD})
    assert r.status_code == 200, r.text


def test_einzelnes_konto_darf_immer_gehen(client, tmp_path):
    """Ist man der einzige Nutzer ueberhaupt, ist Loeschen unkritisch: das
    naechste Konto wird wieder automatisch Admin."""
    dbp = tmp_path / "allein.db"
    db.init_db(dbp)
    from backend import auth
    allein = auth.register_user(db.create_invite_code("c", db_path=dbp),
                                "allein@example.com", "Allein", TEST_PASSWORD, db_path=dbp)
    assert allein["is_admin"] == 1
    assert db.count_admins(db_path=dbp) == 1 and db.count_users(db_path=dbp) == 1
    # Die Sperre greift nur, wenn noch jemand ANDERES da ist.
    db.delete_user_completely(allein["id"], db_path=dbp)
    assert db.count_users(db_path=dbp) == 0
