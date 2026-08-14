"""Das Premium-Abo: was es kostet, wann es gilt, was es freischaltet.

EINE Stelle fuer die Frage "darf dieses Konto die Video-Werkzeuge benutzen".
Bewusst getrennt von auth.py (dort geht es um Anmeldung und Identitaet) und
frei von FastAPI: hier steht nur die Regel, die Sperre selbst haengt in
auth.py als require_premium().

Zum Aufbau: die Werkzeuge laufen NICHT auf dem gehosteten Server, sondern auf
dem Rechner des Betreibers (siehe PHASE-3-PLAN.md, Modell B). Das Abo
entscheidet also nicht "kann der Server das", sondern "darf dieses Konto
Auftraege in die Warteschlange stellen".
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from backend import db

# Es gibt vorerst genau einen Plan. Eine Liste waere ehrlicher, wenn es
# mehrere gaebe - solange es einer ist, ist eine Liste nur Ballast.
PLAN_KEY = "premium"
PLAN_NAME = "selfsign Premium"
PLAN_PREIS_CENT = 1000          # 10,00 EUR pro Monat
PLAN_WAEHRUNG = "EUR"
PLAN_INTERVALL = "monat"

# Zustaende, in denen das Abo den Zugang noch traegt. 'canceled' gehoert
# dazu: wer kuendigt, hat bis zum Ende der bezahlten Zeit bezahlt - ihm
# sofort abzudrehen waere schlicht falsch abgerechnet.
AKTIVE_STATUS = ("active", "canceled")

# Alle Zustaende, die in der Tabelle vorkommen duerfen. Wird beim Setzen
# geprueft, damit sich kein Tippfehler als "kein Premium" tarnt.
ALLE_STATUS = ("active", "canceled", "expired", "past_due")

PROVIDER_HAND = "hand"          # von Hand vergeben (Ueberweisung, Test)


def _jetzt() -> datetime:
    return datetime.now(timezone.utc)


def parse_zeit(iso: str) -> datetime | None:
    """Zeitstempel aus der Datenbank lesen. Ist er unlesbar, wird das Abo
    lieber als abgelaufen behandelt als als unbefristet gueltig - im Zweifel
    gegen den Zugang, nicht dagegen, dass jemand bezahlt hat."""
    try:
        dt = datetime.fromisoformat(iso)
    except (TypeError, ValueError):
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def ist_aktiv(sub: dict | None, jetzt: datetime | None = None) -> bool:
    """Traegt dieses Abo gerade den Zugang?"""
    if not sub:
        return False
    if sub.get("status") not in AKTIVE_STATUS:
        return False
    ende = sub.get("period_end")
    if ende is None:
        # Unbefristet gibt es nur bei Abos von Hand - siehe Tabellenkommentar.
        return True
    ende_dt = parse_zeit(ende)
    if ende_dt is None:
        return False
    return ende_dt > (jetzt or _jetzt())


def zustand(user_id: str, db_path: str | Path = db.DEFAULT_DB_PATH) -> dict:
    """Was die Oberflaeche ueber das Abo wissen muss - nie mehr.

    Anbieter-IDs bleiben absichtlich draussen: sie gehen das Frontend nichts
    an und stuenden sonst in jeder /auth/me-Antwort im Netz.
    """
    sub = db.get_subscription(user_id, db_path=db_path)
    aktiv = ist_aktiv(sub)
    return {
        "premium": aktiv,
        "premium_bis": sub.get("period_end") if sub else None,
        "premium_status": sub.get("status") if sub else None,
        "plan": PLAN_KEY,
        "preis_cent": PLAN_PREIS_CENT,
        "waehrung": PLAN_WAEHRUNG,
    }
