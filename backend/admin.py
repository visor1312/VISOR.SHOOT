"""Admin-Werkzeuge fuers Benutzer-System (lokal, per Doppelklick-.bat).

    python -m backend.admin create-invite [--anzahl N]
    python -m backend.admin list-invites
    python -m backend.admin list-users
    python -m backend.admin reset-password [email]
    python -m backend.admin abo-geben [email] [--monate N | --unbefristet]
    python -m backend.admin abo-nehmen [email]
    python -m backend.admin abo-liste

Alles bewusst offline/lokal: Einladungscodes erzeugt der Betreiber selbst,
und "Passwort vergessen" ist bis zum Hosting (E-Mail-Versand) ein
Notfall-Reset direkt am Rechner. Alle Funktionen nehmen db_path als
Keyword, damit die Tests gegen eine Wegwerf-DB laufen koennen.

Die abo-Befehle sind der Handbetrieb, bevor ein Zahlungsanbieter
angebunden ist: Rechnung per Ueberweisung, Abo hier freischalten. Sobald
der Anbieter da ist, bleiben sie fuer Testkonten und Kulanz nuetzlich -
deshalb tragen sie provider = 'hand' ein und sind so von echten Abos
unterscheidbar.
"""
from __future__ import annotations

import argparse
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path

from backend import abo, auth, db


def create_invites(count: int = 1, db_path: str | Path = db.DEFAULT_DB_PATH) -> list[str]:
    db.init_db(db_path)
    codes = []
    for _ in range(max(1, count)):
        # ~12 Zeichen: lang genug gegen Raten, kurz genug zum Abtippen.
        codes.append(db.create_invite_code(secrets.token_urlsafe(9), db_path=db_path))
    return codes


def reset_password(email: str, new_password: str,
                   db_path: str | Path = db.DEFAULT_DB_PATH) -> None:
    """Setzt das Passwort neu und meldet alle Sitzungen des Kontos ab.
    Wirft ValueError mit deutscher Meldung bei unbekannter E-Mail oder
    ungueltigem Passwort."""
    db.init_db(db_path)
    user = db.get_user_by_email(auth.normalize_email(email), db_path=db_path)
    if not user:
        raise ValueError(f"Kein Konto mit der E-Mail-Adresse {email!r} gefunden.")
    pw_error = auth.validate_password(new_password)
    if pw_error:
        raise ValueError(pw_error)
    db.set_user_password_hash(user["id"], auth.hash_password(new_password), db_path=db_path)
    db.delete_sessions_for_user(user["id"], db_path=db_path)
    db.reset_login_failures(user["email"], db_path=db_path)


def abo_geben(email: str, monate: int = 1, unbefristet: bool = False,
              db_path: str | Path = db.DEFAULT_DB_PATH) -> str | None:
    """Premium von Hand freischalten. Gibt das Enddatum zurueck (None =
    unbefristet). Wirft ValueError mit deutscher Meldung bei unbekannter
    E-Mail.

    Verlaengern statt ueberschreiben: laeuft das Abo noch, wird ab dem
    bisherigen Ende weitergerechnet. Sonst wuerde ein Kunde, der frueh
    nachzahlt, die Resttage verlieren.
    """
    db.init_db(db_path)
    user = db.get_user_by_email(auth.normalize_email(email), db_path=db_path)
    if not user:
        raise ValueError(f"Kein Konto mit der E-Mail-Adresse {email!r} gefunden.")

    ende_iso: str | None = None
    if not unbefristet:
        jetzt = datetime.now(timezone.utc)
        bisher = db.get_subscription(user["id"], db_path=db_path)
        start = jetzt
        if abo.ist_aktiv(bisher, jetzt) and bisher.get("period_end"):
            vorhanden = abo.parse_zeit(bisher["period_end"])
            if vorhanden and vorhanden > jetzt:
                start = vorhanden
        # 30 Tage statt Kalendermonat: nachvollziehbar und ohne Sonderfaelle
        # am Monatsende (der 31. Januar plus einen Monat ist mehrdeutig).
        ende_iso = (start + timedelta(days=30 * max(1, monate))).isoformat()

    db.set_subscription(user["id"], status="active", plan=abo.PLAN_KEY,
                        period_end=ende_iso, provider=abo.PROVIDER_HAND,
                        db_path=db_path)
    return ende_iso


def abo_nehmen(email: str, db_path: str | Path = db.DEFAULT_DB_PATH) -> None:
    """Premium sofort beenden. Bewusst 'expired' statt Loeschen: so bleibt
    sichtbar, dass dieses Konto einmal Kunde war."""
    db.init_db(db_path)
    user = db.get_user_by_email(auth.normalize_email(email), db_path=db_path)
    if not user:
        raise ValueError(f"Kein Konto mit der E-Mail-Adresse {email!r} gefunden.")
    if not db.get_subscription(user["id"], db_path=db_path):
        raise ValueError(f"{email} hat gar kein Abo.")
    db.set_subscription(user["id"], status="expired", plan=abo.PLAN_KEY,
                        period_end=datetime.now(timezone.utc).isoformat(),
                        provider=abo.PROVIDER_HAND, db_path=db_path)


def _cmd_abo_geben(args: argparse.Namespace) -> None:
    email = args.email or input("E-Mail-Adresse des Kontos: ").strip()
    try:
        ende = abo_geben(email, monate=args.monate, unbefristet=args.unbefristet)
    except ValueError as e:
        print(str(e))
        return
    if ende is None:
        print(f"{email} hat jetzt selfsign Premium - unbefristet.")
    else:
        print(f"{email} hat jetzt selfsign Premium bis {ende[:10]}.")


def _cmd_abo_nehmen(args: argparse.Namespace) -> None:
    email = args.email or input("E-Mail-Adresse des Kontos: ").strip()
    try:
        abo_nehmen(email)
    except ValueError as e:
        print(str(e))
        return
    print(f"Das Abo von {email} ist beendet.")
    print("Achtung: eine laufende Zahlung beim Anbieter wird dadurch NICHT "
          "gekuendigt - das geht nur dort.")


def _cmd_abo_liste(args: argparse.Namespace) -> None:
    db.init_db()
    abos = db.list_subscriptions()
    if not abos:
        print("Noch keine Abos vergeben.")
        return
    for s in abos:
        laeuft = "laeuft" if abo.ist_aktiv(s) else "beendet"
        bis = s["period_end"][:10] if s["period_end"] else "unbefristet"
        quelle = "von Hand" if s["provider"] == abo.PROVIDER_HAND else s["provider"]
        print(f"  {s['email']}  ({s['display_name']}, {laeuft}, bis {bis}, {quelle})")


def _cmd_create_invite(args: argparse.Namespace) -> None:
    codes = create_invites(args.anzahl)
    print("Einladungscode(s) fuer die Registrierung:")
    for code in codes:
        print(f"  {code}")
    print("\nCode auf der Registrierungs-Seite eingeben (jeder Code gilt einmal).")


def _cmd_list_invites(args: argparse.Namespace) -> None:
    db.init_db()
    invites = db.list_invite_codes()
    if not invites:
        print("Noch keine Einladungscodes erzeugt.")
        return
    for inv in invites:
        status = f"verwendet von {inv['used_by_email']}" if inv["used_by"] else "offen"
        print(f"  {inv['code']}  ({status}, erstellt {inv['created_at'][:10]})")


def _cmd_list_users(args: argparse.Namespace) -> None:
    db.init_db()
    users = db.list_users()
    if not users:
        print("Noch keine Konten registriert.")
        return
    for u in users:
        role = "Admin" if u["is_admin"] else "Nutzer"
        print(f"  {u['email']}  ({u['display_name']}, {role}, seit {u['created_at'][:10]})")


def _cmd_reset_password(args: argparse.Namespace) -> None:
    import getpass

    email = args.email or input("E-Mail-Adresse des Kontos: ").strip()
    pw1 = getpass.getpass("Neues Passwort (mind. 8 Zeichen): ")
    pw2 = getpass.getpass("Neues Passwort wiederholen: ")
    if pw1 != pw2:
        print("Die Passwoerter stimmen nicht ueberein - nichts geaendert.")
        return
    try:
        reset_password(email, pw1)
    except ValueError as e:
        print(str(e))
        return
    print(f"Passwort fuer {email} wurde neu gesetzt. Alle Sitzungen wurden abgemeldet.")


def _main() -> None:
    p = argparse.ArgumentParser(prog="python -m backend.admin",
                                description="selfsign Admin-Werkzeuge (Konten & Einladungen)")
    sub = p.add_subparsers(dest="command", required=True)

    ci = sub.add_parser("create-invite", help="Einladungscode(s) erzeugen")
    ci.add_argument("--anzahl", type=int, default=1)
    ci.set_defaults(func=_cmd_create_invite)

    li = sub.add_parser("list-invites", help="Alle Einladungscodes anzeigen")
    li.set_defaults(func=_cmd_list_invites)

    lu = sub.add_parser("list-users", help="Alle Konten anzeigen")
    lu.set_defaults(func=_cmd_list_users)

    rp = sub.add_parser("reset-password", help="Passwort eines Kontos neu setzen")
    rp.add_argument("email", nargs="?", default=None)
    rp.set_defaults(func=_cmd_reset_password)

    ag = sub.add_parser("abo-geben", help="selfsign Premium freischalten")
    ag.add_argument("email", nargs="?", default=None)
    ag.add_argument("--monate", type=int, default=1,
                    help="Laufzeit in Monaten zu je 30 Tagen (Standard: 1)")
    ag.add_argument("--unbefristet", action="store_true",
                    help="Ohne Enddatum - fuer eigene Konten und Tests")
    ag.set_defaults(func=_cmd_abo_geben)

    an = sub.add_parser("abo-nehmen", help="selfsign Premium sofort beenden")
    an.add_argument("email", nargs="?", default=None)
    an.set_defaults(func=_cmd_abo_nehmen)

    al = sub.add_parser("abo-liste", help="Alle Abos anzeigen")
    al.set_defaults(func=_cmd_abo_liste)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    _main()
