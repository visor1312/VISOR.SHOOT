"""Tests fuer die Bestaetigung der E-Mail-Adresse.

Standardmaessig AUS - ohne eigene Domain mit SPF/DKIM kaeme die Mail bei
vielen gar nicht an, und niemand koennte sich mehr anmelden. Die Tests
schalten sie deshalb gezielt ein.

Der echte Versand ueber resend.com laesst sich hier nicht pruefen (kein
Zugang, keine Domain). Geprueft wird alles davor und danach: Token anlegen,
einloesen, ablaufen, und was ein unbestaetigtes Konto darf.
"""
from __future__ import annotations

import uuid

import pytest

from backend import auth, config, db, mailer
from tests.conftest import TEST_PASSWORD


@pytest.fixture()
def gefangene_mails(monkeypatch):
    """Faengt den Versand ab, statt wirklich zu verschicken."""
    postfach: list[dict] = []

    def falscher_versand(empfaenger, betreff, text):
        postfach.append({"an": empfaenger, "betreff": betreff, "text": text})
        return True

    monkeypatch.setattr(mailer, "send", falscher_versand)
    return postfach


def _link_aus(text: str) -> str:
    zeile = next(z for z in text.splitlines() if "token=" in z)
    return zeile.strip()


def _token_aus(text: str) -> str:
    return _link_aus(text).split("token=", 1)[1]


def _registrieren(client):
    return client.post("/auth/register", json={
        "invite_code": db.create_invite_code(f"c-{uuid.uuid4().hex[:8]}"),
        "email": f"mail-{uuid.uuid4().hex[:10]}@example.com",
        "display_name": "Mail Tester", "password": TEST_PASSWORD})


def test_ausgeschaltet_aendert_sich_nichts(client, gefangene_mails, monkeypatch):
    """Der Normalfall heute: keine Mail, Konto sofort nutzbar."""
    monkeypatch.setattr(config, "EMAIL_VERIFICATION", False)
    assert _registrieren(client).status_code == 200
    assert gefangene_mails == []
    assert client.post("/posts", data={"title": "Geht sofort",
                                       "categories": "beat"}).status_code == 200


def test_bestaetigen_von_anfang_bis_ende(client, gefangene_mails, monkeypatch):
    monkeypatch.setattr(config, "EMAIL_VERIFICATION", True)
    # Erst ein anderes Konto, damit der Testnutzer nicht der erste (= Admin,
    # von der Pflicht ausgenommen) ist.
    monkeypatch.setattr(config, "EMAIL_VERIFICATION", False)
    _registrieren(client)
    monkeypatch.setattr(config, "EMAIL_VERIFICATION", True)

    r = _registrieren(client)
    assert r.status_code == 200
    assert len(gefangene_mails) == 1
    assert "bestaetige" in gefangene_mails[0]["betreff"].lower()

    # Vor der Bestaetigung: lesen ja, veroeffentlichen nein.
    assert client.get("/feed/discover").status_code == 200
    gesperrt = client.post("/posts", data={"title": "Noch nicht", "categories": "beat"})
    assert gesperrt.status_code == 403
    assert "bestaetige" in gesperrt.json()["detail"].lower()

    # Link einloesen - ausdruecklich OHNE Anmeldung (Handy).
    token = _token_aus(gefangene_mails[0]["text"])
    client.post("/auth/logout")
    assert client.post("/auth/verify-email", json={"token": token}).status_code == 200

    # Danach geht alles.
    client.post("/auth/login", json={"email": r.json()["email"], "password": TEST_PASSWORD})
    assert client.post("/posts", data={"title": "Jetzt schon",
                                       "categories": "beat"}).status_code == 200


def test_token_gilt_nur_einmal(client, gefangene_mails, monkeypatch):
    monkeypatch.setattr(config, "EMAIL_VERIFICATION", False)
    _registrieren(client)
    monkeypatch.setattr(config, "EMAIL_VERIFICATION", True)
    _registrieren(client)
    token = _token_aus(gefangene_mails[0]["text"])

    assert client.post("/auth/verify-email", json={"token": token}).status_code == 200
    zweiter = client.post("/auth/verify-email", json={"token": token})
    assert zweiter.status_code == 400


def test_unsinniges_token_wird_abgewiesen(client):
    r = client.post("/auth/verify-email", json={"token": "ausgedacht"})
    assert r.status_code == 400
    assert "ungueltig" in r.json()["detail"].lower()


def test_abgelaufenes_token(client, tmp_path):
    dbp = tmp_path / "token.db"
    db.init_db(dbp)
    user_id = db.create_user("ab@example.com", "Ab", "hash", db_path=dbp)
    db.insert_email_token(auth._hash_token("altes-token"), user_id,
                          "2000-01-01T00:00:00+00:00", db_path=dbp)
    eintrag = db.get_email_token(auth._hash_token("altes-token"), db_path=dbp)
    assert eintrag is not None and eintrag["expires_at"] < "2020"


def test_in_der_datenbank_liegt_nur_der_hash(tmp_path):
    """Wie bei den Sitzungen: wer die DB hat, darf damit keine fremde
    Adresse bestaetigen koennen."""
    dbp = tmp_path / "hash.db"
    db.init_db(dbp)
    user_id = db.create_user("h@example.com", "H", "hash", db_path=dbp)
    db.insert_email_token(auth._hash_token("geheim"), user_id,
                          "2099-01-01T00:00:00+00:00", db_path=dbp)
    assert db.get_email_token("geheim", db_path=dbp) is None
    assert db.get_email_token(auth._hash_token("geheim"), db_path=dbp) is not None


def test_neuer_link_entwertet_den_alten(tmp_path):
    """Sonst blieben beliebig viele gueltige Links im Umlauf, wenn jemand
    mehrfach auf 'noch mal schicken' drueckt."""
    dbp = tmp_path / "neu.db"
    db.init_db(dbp)
    user_id = db.create_user("n@example.com", "N", "hash", db_path=dbp)
    db.insert_email_token(auth._hash_token("erstes"), user_id,
                          "2099-01-01T00:00:00+00:00", db_path=dbp)
    db.insert_email_token(auth._hash_token("zweites"), user_id,
                          "2099-01-01T00:00:00+00:00", db_path=dbp)
    assert db.get_email_token(auth._hash_token("erstes"), db_path=dbp) is None
    assert db.get_email_token(auth._hash_token("zweites"), db_path=dbp) is not None


def test_erstes_konto_ist_ausgenommen(tmp_path, monkeypatch):
    """Der Betreiber muesste sich sonst selbst eine Mail schicken koennen,
    bevor der Versand ueberhaupt eingerichtet ist - und saesse ausgesperrt
    vor seiner eigenen Plattform."""
    dbp = tmp_path / "erster.db"
    db.init_db(dbp)
    monkeypatch.setattr(config, "EMAIL_VERIFICATION", True)
    chef = auth.register_user(db.create_invite_code("c1", db_path=dbp),
                              "chef@example.com", "Chef", TEST_PASSWORD, db_path=dbp)
    assert chef["email_verified"] == 1
    zweiter = auth.register_user(db.create_invite_code("c2", db_path=dbp),
                                 "zwei@example.com", "Zwei", TEST_PASSWORD, db_path=dbp)
    assert zweiter["email_verified"] == 0


def test_versandfehler_laesst_die_registrierung_stehen(client, monkeypatch):
    """Scheitert der Versand, darf die Registrierung NICHT fehlschlagen -
    das Konto existiert ja schon. Sonst haette jemand ein Konto, von dem er
    nichts weiss."""
    monkeypatch.setattr(config, "EMAIL_VERIFICATION", False)
    _registrieren(client)
    monkeypatch.setattr(config, "EMAIL_VERIFICATION", True)

    def kaputt(*_a, **_k):
        raise mailer.MailFehler("Postfach brennt")

    monkeypatch.setattr(mailer, "send", kaputt)
    assert _registrieren(client).status_code == 200


def test_zustellart_log_verschickt_nichts(monkeypatch, capsys):
    """Die Standard-Zustellart schreibt die Mail ins Serverfenster - so
    laesst sich der Ablauf ohne Domain ausprobieren."""
    monkeypatch.setattr(config, "MAIL_BACKEND", "log")
    assert mailer.send("wer@example.com", "Betreff", "Inhalt mit Link") is True
    ausgabe = capsys.readouterr().out
    assert "wer@example.com" in ausgabe and "Inhalt mit Link" in ausgabe


def test_unbekannte_zustellart_faellt_auf(monkeypatch):
    monkeypatch.setattr(config, "MAIL_BACKEND", "brieftaube")
    with pytest.raises(mailer.MailFehler):
        mailer.send("wer@example.com", "B", "T")


def test_resend_ohne_zugangsschluessel(monkeypatch):
    monkeypatch.setattr(config, "MAIL_BACKEND", "resend")
    monkeypatch.setattr(config, "RESEND_API_KEY", "")
    with pytest.raises(mailer.MailFehler):
        mailer.send("wer@example.com", "B", "T")


def test_bestaetigungsmail_hat_eine_wartezeit(client, gefangene_mails, monkeypatch):
    """Ohne Wartezeit laesst sich das Gratis-Kontingent des Mail-Dienstes in
    einer Minute verbrennen - im Sicherheits-Durchgang wurden 50 von 50
    Anforderungen angenommen."""
    monkeypatch.setattr(config, "EMAIL_VERIFICATION", False)
    _registrieren(client)                      # erstes Konto: ausgenommen
    monkeypatch.setattr(config, "EMAIL_VERIFICATION", True)
    _registrieren(client)                      # dieses ist unbestaetigt
    assert len(gefangene_mails) == 1

    gebremst = client.post("/auth/resend-verification")
    assert gebremst.status_code == 429
    assert "Postfach" in gebremst.json()["detail"]
    assert len(gefangene_mails) == 1, "trotz Bremse wurde verschickt"


def test_nach_der_wartezeit_geht_es_wieder(client, gefangene_mails, monkeypatch):
    monkeypatch.setattr(config, "EMAIL_VERIFICATION", False)
    _registrieren(client)
    monkeypatch.setattr(config, "EMAIL_VERIFICATION", True)
    r = _registrieren(client)

    # Den vorhandenen Link kuenstlich altern lassen.
    with db._connect(db.DEFAULT_DB_PATH) as conn:
        conn.execute("UPDATE email_tokens SET created_at = '2000-01-01T00:00:00+00:00' "
                     "WHERE user_id = ?", (r.json()["id"],))

    assert client.post("/auth/resend-verification").status_code == 200
    assert len(gefangene_mails) == 2


def test_bestaetigtes_konto_loest_keinen_versand_aus(client, gefangene_mails, monkeypatch):
    """Wer schon bestaetigt ist, bekommt keine Mail mehr - und laeuft auch
    nicht in die Wartezeit."""
    # Bei ausgeschalteter Pruefung angelegt = von vornherein bestaetigt.
    # (Sich auf "erstes Konto ist ausgenommen" zu verlassen geht hier nicht:
    # alle Tests teilen sich eine DB, es gibt also laengst andere Konten.)
    monkeypatch.setattr(config, "EMAIL_VERIFICATION", False)
    _registrieren(client)
    monkeypatch.setattr(config, "EMAIL_VERIFICATION", True)

    r = client.post("/auth/resend-verification")
    assert r.status_code == 200 and r.json()["bereits_bestaetigt"] is True
    assert gefangene_mails == []
