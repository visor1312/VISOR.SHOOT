"""Admin-Werkzeuge fuers Benutzer-System (lokal, per Doppelklick-.bat).

    python -m backend.admin create-invite [--anzahl N]
    python -m backend.admin list-invites
    python -m backend.admin list-users
    python -m backend.admin reset-password [email]

Alles bewusst offline/lokal: Einladungscodes erzeugt der Betreiber selbst,
und "Passwort vergessen" ist bis zum Hosting (E-Mail-Versand) ein
Notfall-Reset direkt am Rechner. Alle Funktionen nehmen db_path als
Keyword, damit die Tests gegen eine Wegwerf-DB laufen koennen.
"""
from __future__ import annotations

import argparse
import secrets
from pathlib import Path

from backend import auth, db


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
                                description="HOOKCUT Admin-Werkzeuge (Konten & Einladungen)")
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

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    _main()
