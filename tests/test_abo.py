"""Tests fuer das Premium-Abo: Regel, Sperre, Handbetrieb.

Die reine Regel (ist_aktiv) wird ohne Datenbank geprueft, alles andere
gegen eine Wegwerf-DB in tmp_path bzw. ueber die API mit den Fixtures aus
conftest.py.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException

from backend import abo, admin, auth, config, db
from tests.conftest import TEST_PASSWORD


def _iso(dt: datetime) -> str:
    return dt.isoformat()


JETZT = datetime(2026, 8, 13, 12, 0, tzinfo=timezone.utc)


# --- Die Regel -------------------------------------------------------------

def test_kein_abo_ist_kein_premium():
    assert abo.ist_aktiv(None) is False


def test_aktiv_mit_zukunft():
    sub = {"status": "active", "period_end": _iso(JETZT + timedelta(days=5))}
    assert abo.ist_aktiv(sub, JETZT) is True


def test_abgelaufen_ist_vorbei():
    sub = {"status": "active", "period_end": _iso(JETZT - timedelta(minutes=1))}
    assert abo.ist_aktiv(sub, JETZT) is False


def test_gekuendigt_gilt_bis_zum_ende():
    """Wer kuendigt, hat bis zum Ende der bezahlten Zeit bezahlt."""
    sub = {"status": "canceled", "period_end": _iso(JETZT + timedelta(days=3))}
    assert abo.ist_aktiv(sub, JETZT) is True
    vorbei = {"status": "canceled", "period_end": _iso(JETZT - timedelta(days=1))}
    assert abo.ist_aktiv(vorbei, JETZT) is False


def test_zahlung_offen_traegt_nicht():
    sub = {"status": "past_due", "period_end": _iso(JETZT + timedelta(days=5))}
    assert abo.ist_aktiv(sub, JETZT) is False


def test_unbefristet_gilt_immer():
    assert abo.ist_aktiv({"status": "active", "period_end": None}, JETZT) is True


def test_kaputtes_datum_gilt_als_abgelaufen():
    """Im Zweifel GEGEN den Zugang - ein unlesbarer Zeitstempel darf kein
    unbefristetes Premium werden."""
    sub = {"status": "active", "period_end": "das-ist-kein-datum"}
    assert abo.ist_aktiv(sub, JETZT) is False


def test_datum_ohne_zeitzone_wird_als_utc_gelesen():
    """Ohne diese Behandlung wirft der Vergleich TypeError (naive vs. aware)
    und das haette einen 500er statt einer Antwort gegeben."""
    sub = {"status": "active", "period_end": "2030-01-01T00:00:00"}
    assert abo.ist_aktiv(sub, JETZT) is True


# --- Datenbank -------------------------------------------------------------

def test_setzen_und_lesen(tmp_path):
    p = tmp_path / "abo.db"
    db.init_db(p)
    uid = db.create_user("a@b.de", "A", "hash", db_path=p)
    assert db.get_subscription(uid, db_path=p) is None

    db.set_subscription(uid, status="active", plan="premium",
                        period_end=_iso(JETZT + timedelta(days=30)),
                        provider="hand", db_path=p)
    sub = db.get_subscription(uid, db_path=p)
    assert sub["status"] == "active" and sub["provider"] == "hand"
    assert sub["user_id"] == uid


def test_zweites_setzen_ueberschreibt_statt_zu_scheitern(tmp_path):
    """Der Zahlungsanbieter schickt spaeter bei jedem Ereignis den ganzen
    Zustand - das darf nicht am Primaerschluessel scheitern."""
    p = tmp_path / "abo.db"
    db.init_db(p)
    uid = db.create_user("a@b.de", "A", "hash", db_path=p)
    db.set_subscription(uid, status="active", plan="premium", db_path=p)
    erst = db.get_subscription(uid, db_path=p)["created_at"]
    db.set_subscription(uid, status="expired", plan="premium", db_path=p)
    danach = db.get_subscription(uid, db_path=p)
    assert danach["status"] == "expired"
    # created_at bleibt: wann jemand zuerst Kunde wurde, geht nicht verloren.
    assert danach["created_at"] == erst


def test_abo_verschwindet_mit_dem_konto(tmp_path):
    """Ohne Aufraeumen scheitert das Loeschen an der Fremdschluessel-Regel."""
    p = tmp_path / "abo.db"
    db.init_db(p)
    uid = db.create_user("a@b.de", "A", "hash", db_path=p)
    db.set_subscription(uid, status="active", plan="premium", db_path=p)
    db.delete_user_completely(uid, db_path=p)
    assert db.get_subscription(uid, db_path=p) is None


def test_konto_mit_offenem_bestaetigungslink_laesst_sich_loeschen(tmp_path):
    """War ein Fehler: wer sich registrierte und sein Konto loeschte, BEVOR
    er die E-Mail bestaetigt hatte, lief in "FOREIGN KEY constraint failed" -
    ausgerechnet beim Loeschrecht (DSGVO Art. 17)."""
    p = tmp_path / "abo.db"
    db.init_db(p)
    uid = db.create_user("a@b.de", "A", "hash", db_path=p)
    db.insert_email_token("tokenhash", uid, _iso(JETZT + timedelta(hours=24)), db_path=p)
    db.delete_user_completely(uid, db_path=p)
    assert db.get_user_by_id(uid, db_path=p) is None


def test_liste_zeigt_name_und_adresse(tmp_path):
    p = tmp_path / "abo.db"
    db.init_db(p)
    uid = db.create_user("a@b.de", "Anna", "hash", db_path=p)
    db.set_subscription(uid, status="active", plan="premium", db_path=p)
    eintraege = db.list_subscriptions(db_path=p)
    assert len(eintraege) == 1
    assert eintraege[0]["email"] == "a@b.de"
    assert eintraege[0]["display_name"] == "Anna"


# --- Handbetrieb (CLI) -----------------------------------------------------

def test_abo_geben_und_nehmen(tmp_path):
    p = tmp_path / "abo.db"
    db.init_db(p)
    uid = db.create_user("a@b.de", "A", "hash", db_path=p)

    ende = admin.abo_geben("a@b.de", monate=1, db_path=p)
    assert ende is not None
    assert abo.ist_aktiv(db.get_subscription(uid, db_path=p)) is True

    admin.abo_nehmen("a@b.de", db_path=p)
    assert abo.ist_aktiv(db.get_subscription(uid, db_path=p)) is False
    # Nicht geloescht - es bleibt sichtbar, dass das Konto mal Kunde war.
    assert db.get_subscription(uid, db_path=p)["status"] == "expired"


def test_abo_geben_verlaengert_statt_zu_verkuerzen(tmp_path):
    """Wer frueh nachzahlt, darf seine Resttage nicht verlieren."""
    p = tmp_path / "abo.db"
    db.init_db(p)
    uid = db.create_user("a@b.de", "A", "hash", db_path=p)

    erst = admin.abo_geben("a@b.de", monate=1, db_path=p)
    zweit = admin.abo_geben("a@b.de", monate=1, db_path=p)
    assert abo.parse_zeit(zweit) > abo.parse_zeit(erst)
    # Grob zwei Monate ab jetzt, nicht einer.
    rest = abo.parse_zeit(zweit) - datetime.now(timezone.utc)
    assert timedelta(days=58) < rest < timedelta(days=61)


def test_abo_geben_nach_ablauf_rechnet_ab_jetzt(tmp_path):
    """Ein laengst abgelaufenes Abo darf beim Verlaengern nicht rueckwirkend
    aufaddiert werden - sonst kauft jemand einen Monat und hat sofort nichts."""
    p = tmp_path / "abo.db"
    db.init_db(p)
    uid = db.create_user("a@b.de", "A", "hash", db_path=p)
    db.set_subscription(uid, status="expired", plan="premium",
                        period_end=_iso(datetime.now(timezone.utc) - timedelta(days=400)),
                        db_path=p)
    ende = admin.abo_geben("a@b.de", monate=1, db_path=p)
    rest = abo.parse_zeit(ende) - datetime.now(timezone.utc)
    assert timedelta(days=28) < rest < timedelta(days=31)


def test_abo_unbefristet(tmp_path):
    p = tmp_path / "abo.db"
    db.init_db(p)
    uid = db.create_user("a@b.de", "A", "hash", db_path=p)
    assert admin.abo_geben("a@b.de", unbefristet=True, db_path=p) is None
    assert abo.ist_aktiv(db.get_subscription(uid, db_path=p)) is True


def test_abo_geben_unbekannte_adresse(tmp_path):
    p = tmp_path / "abo.db"
    db.init_db(p)
    with pytest.raises(ValueError, match="Kein Konto"):
        admin.abo_geben("gibtsnicht@b.de", db_path=p)


def test_abo_nehmen_ohne_abo(tmp_path):
    p = tmp_path / "abo.db"
    db.init_db(p)
    db.create_user("a@b.de", "A", "hash", db_path=p)
    with pytest.raises(ValueError, match="gar kein Abo"):
        admin.abo_nehmen("a@b.de", db_path=p)


def test_adresse_wird_normalisiert(tmp_path):
    """Gross-/Kleinschreibung darf beim Freischalten keine Rolle spielen -
    sonst schaltet der Betreiber ins Leere und wundert sich."""
    p = tmp_path / "abo.db"
    db.init_db(p)
    uid = db.create_user("a@b.de", "A", "hash", db_path=p)
    admin.abo_geben("  A@B.DE  ", db_path=p)
    assert abo.ist_aktiv(db.get_subscription(uid, db_path=p)) is True


# --- Sperre und /auth/me ---------------------------------------------------

def test_me_liefert_abo_zustand(auth_client):
    me = auth_client.get("/auth/me").json()
    assert me["premium"] is False
    assert me["premium_bis"] is None
    assert me["preis_cent"] == abo.PLAN_PREIS_CENT


def test_registrierung_und_login_liefern_dasselbe_wie_me(auth_client):
    """War ein Fehler: /auth/register und /auth/login lieferten das
    Nutzer-Objekt OHNE Abo-Felder. Die Oberflaeche zeigte direkt nach dem
    Anmelden deshalb "NaN €" - bis zum naechsten Neuladen."""
    me = set(auth_client.get("/auth/me").json())
    ein = auth_client.post("/auth/login", json={
        "email": auth_client.user_email, "password": TEST_PASSWORD}).json()
    assert set(ein) == me
    # Auch nach einer Namensaenderung darf nichts fehlen.
    neu = auth_client.patch("/auth/me", json={"display_name": "Neuer Name"}).json()
    assert set(neu) == me


def test_me_zeigt_freigeschaltetes_abo(auth_client):
    db.set_subscription(auth_client.user["id"], status="active", plan="premium",
                        period_end=_iso(datetime.now(timezone.utc) + timedelta(days=30)))
    me = auth_client.get("/auth/me").json()
    assert me["premium"] is True
    assert me["premium_bis"] is not None


def test_me_verraet_keine_anbieter_ids(auth_client):
    """Die Kundennummer beim Zahlungsanbieter geht das Frontend nichts an."""
    db.set_subscription(auth_client.user["id"], status="active", plan="premium",
                        provider="paddle", provider_customer_id="ctm_geheim",
                        provider_subscription_id="sub_geheim")
    me = auth_client.get("/auth/me").json()
    assert "ctm_geheim" not in str(me) and "sub_geheim" not in str(me)


def test_require_premium_sperrt_ohne_abo(auth_client, monkeypatch):
    monkeypatch.setattr(config, "PREMIUM_REQUIRED", True)
    user = db.get_user_by_id(auth_client.user["id"])
    with pytest.raises(HTTPException) as ex:
        auth.require_premium(user)
    # 402 heisst "das kostet", nicht "du darfst nicht" - daran erkennt die
    # Oberflaeche, dass sie auf die Premium-Seite schicken soll.
    assert ex.value.status_code == 402


def test_require_premium_laesst_abonnenten_durch(auth_client, monkeypatch):
    monkeypatch.setattr(config, "PREMIUM_REQUIRED", True)
    db.set_subscription(auth_client.user["id"], status="active", plan="premium",
                        period_end=_iso(datetime.now(timezone.utc) + timedelta(days=30)))
    user = db.get_user_by_id(auth_client.user["id"])
    assert auth.require_premium(user)["id"] == user["id"]


def test_lokal_sperrt_premium_niemanden_aus(auth_client):
    """Auf dem eigenen Rechner (Standard) sind es die eigenen Werkzeuge -
    sich dort selbst auszusperren waere absurd."""
    assert config.PREMIUM_REQUIRED is False
    user = db.get_user_by_id(auth_client.user["id"])
    assert auth.require_premium(user)["id"] == user["id"]


def test_config_sagt_ob_premium_noetig_ist(client):
    c = client.get("/auth/config").json()
    assert c["premium_required"] is False


# --- Die Schranke haengt auch wirklich an den Routen ----------------------
#
# Genau das fehlte beim ersten Anlauf: require_premium existierte, war aber an
# keiner Route angehaengt. Die Bezahlschranke in der Oberflaeche war damit
# reine Deko - ein Aufruf per fetch waere durchgegangen.

# (Route, Methode) - alles, was Arbeit ausloest. Bewusst hier als feste Liste
# und nicht aus der App abgeleitet: eine neue Werkzeug-Route soll auffallen,
# nicht sich selbst durchwinken.
ARBEITS_ROUTEN = [
    ("POST", "/projects"),
    ("POST", "/projects/x/takes"),
    ("POST", "/projects/x/takes/y/sync"),
    ("POST", "/hooks/analyze"),
    ("POST", "/editor/analyze"),
    ("POST", "/edit/analyze"),
    ("POST", "/edit/x/hook"),
    ("POST", "/edit/x/render"),
    ("POST", "/packs"),
    ("POST", "/canvas"),
]


@pytest.mark.parametrize("methode,pfad", ARBEITS_ROUTEN)
def test_arbeit_kostet_ein_abo(auth_client, monkeypatch, methode, pfad):
    monkeypatch.setattr(config, "PREMIUM_REQUIRED", True)
    r = auth_client.request(methode, pfad)
    # 402 muss VOR der Eingabepruefung kommen: sonst verraet ein 422, dass die
    # Route ueberhaupt gearbeitet haette.
    assert r.status_code == 402, f"{methode} {pfad} antwortet {r.status_code}"


@pytest.mark.parametrize("methode,pfad", ARBEITS_ROUTEN)
def test_mit_abo_greift_die_bezahlschranke_nicht_mehr(auth_client, monkeypatch,
                                                      methode, pfad):
    monkeypatch.setattr(config, "PREMIUM_REQUIRED", True)
    db.set_subscription(auth_client.user["id"], status="active", plan="premium",
                        period_end=_iso(datetime.now(timezone.utc) + timedelta(days=30)))
    r = auth_client.request(methode, pfad)
    assert r.status_code != 402, f"{methode} {pfad} sperrt trotz Abo"


# Lesen und Herunterladen bleibt offen: wessen Abo auslaeuft, kommt weiter an
# das, was er waehrend der bezahlten Zeit erzeugt hat.
@pytest.mark.parametrize("pfad", ["/projects", "/edit", "/packs", "/canvas"])
def test_lesen_bleibt_ohne_abo_erlaubt(auth_client, monkeypatch, pfad):
    monkeypatch.setattr(config, "PREMIUM_REQUIRED", True)
    r = auth_client.get(pfad)
    assert r.status_code == 200, f"GET {pfad} antwortet {r.status_code}"


def test_render_vertrag_bleibt_ohne_abo_erreichbar(auth_client, monkeypatch):
    """Laeuft ein Abo aus, waehrend der Agent noch rendert, muss das fertige
    Video trotzdem ankommen - sonst geht bezahlte Arbeit verloren."""
    monkeypatch.setattr(config, "PREMIUM_REQUIRED", True)
    assert auth_client.get("/render/pending").status_code == 200


def test_konto_loeschen_raeumt_das_abo_weg(auth_client):
    """Ueber die echte Route, nicht nur in der Datenbank."""
    db.set_subscription(auth_client.user["id"], status="active", plan="premium")
    uid = auth_client.user["id"]
    r = auth_client.request("DELETE", "/auth/me",
                            json={"password": "geheim123"})
    assert r.status_code == 200, r.text
    assert db.get_subscription(uid) is None
