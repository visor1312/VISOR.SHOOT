"""Benutzer-System: Passwort-Hashing, Sessions, Login/Registrierung.

Design (bewusst online-tauglich, laeuft aber komplett lokal):
- Passwoerter: bcrypt (12 Runden). bcrypt verarbeitet maximal 72 BYTES
  (Umlaute zaehlen doppelt!) und wirft ab v5 einen ValueError statt still zu
  kuerzen - deshalb wird die Laenge VOR jedem hashpw/checkpw validiert.
- Sessions: Zufalls-Token (secrets.token_urlsafe) im httpOnly-Cookie; in der
  DB liegt nur der SHA-256-Hash des Tokens. Sliding Expiry: 30 Tage, wird bei
  Benutzung verlaengert (max. 1x pro 24h, sonst ein Write pro Request).
- Registrierung NUR mit Einladungscode (backend/admin.py erzeugt Codes).
  Das ERSTE Konto wird automatisch Admin und uebernimmt alle Altdaten
  (Zeilen mit user_id NULL) - danach ist jede Query ein uniformes
  WHERE user_id = ?, ohne dauerhaftes NULL-Sonderrecht.
- Login-Lockout: 5 Fehlversuche pro E-Mail -> 15 Minuten Sperre (in der DB,
  uebersteht Neustarts). Einheitliche Fehlermeldung, damit sich nicht
  herausfinden laesst, welche E-Mails registriert sind.
- Cookie-Secure-Flag kommt aus HOOKCUT_SECURE_COOKIES (lokal 0, Hosting 1).
"""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path

import bcrypt
from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from pydantic import BaseModel

from backend import config, db

SESSION_COOKIE = "hookcut_session"
SESSION_TTL = timedelta(days=30)
SESSION_REFRESH_AFTER = timedelta(hours=24)
MAX_LOGIN_FAILS = 5
LOCKOUT = timedelta(minutes=15)

PASSWORD_MIN_CHARS = 8
PASSWORD_MAX_BYTES = 72  # harte bcrypt-Grenze (Bytes, nicht Zeichen!)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _parse_iso(s: str) -> datetime:
    return datetime.fromisoformat(s)


def _secure_cookies() -> bool:
    return config.SECURE_COOKIES


def normalize_email(email: str) -> str:
    return email.strip().lower()


def validate_password(password: str) -> str | None:
    """None = ok, sonst deutsche Fehlermeldung."""
    if len(password) < PASSWORD_MIN_CHARS:
        return f"Das Passwort muss mindestens {PASSWORD_MIN_CHARS} Zeichen haben."
    if len(password.encode("utf-8")) > PASSWORD_MAX_BYTES:
        return "Das Passwort ist zu lang (maximal 72 Zeichen, Umlaute zaehlen doppelt)."
    return None


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("ascii")


def verify_password(password: str, password_hash: str) -> bool:
    if len(password.encode("utf-8")) > PASSWORD_MAX_BYTES:
        return False
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("ascii"))
    except ValueError:
        return False


# Dummy-Hash mit denselben Kosten wie ein echter: gegen ihn wird geprueft,
# wenn die E-Mail unbekannt ist. So dauert ein Login mit unbekannter und mit
# bekannter E-Mail gleich lang - sonst wuerde die Antwortzeit verraten, welche
# Adressen registriert sind (Timing-Seitenkanal / User-Enumeration), trotz
# einheitlicher Fehlermeldung.
_DUMMY_HASH = bcrypt.hashpw(b"hookcut-timing-guard", bcrypt.gensalt(rounds=12)).decode("ascii")


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("ascii")).hexdigest()


def create_session(user_id: str, db_path: str | Path = db.DEFAULT_DB_PATH) -> str:
    """Legt eine Session an und gibt das ROHE Token zurueck (fuers Cookie)."""
    token = secrets.token_urlsafe(32)
    db.insert_session(_hash_token(token), user_id, _iso(_now() + SESSION_TTL), db_path=db_path)
    return token


def get_user_for_token(token: str, db_path: str | Path = db.DEFAULT_DB_PATH) -> dict | None:
    """User zur Session oder None (unbekannt/abgelaufen). Verlaengert die
    Session gleitend, aber hoechstens einmal pro 24h."""
    token_hash = _hash_token(token)
    session = db.get_session(token_hash, db_path=db_path)
    if not session:
        return None
    now = _now()
    if _parse_iso(session["expires_at"]) < now:
        db.delete_session_row(token_hash, db_path=db_path)
        return None
    if now - _parse_iso(session["last_seen_at"]) > SESSION_REFRESH_AFTER:
        db.touch_session(token_hash, _iso(now + SESSION_TTL), db_path=db_path)
    return db.get_user_by_id(session["user_id"], db_path=db_path)


def delete_session(token: str, db_path: str | Path = db.DEFAULT_DB_PATH) -> None:
    db.delete_session_row(_hash_token(token), db_path=db_path)


class RegisterError(Exception):
    def __init__(self, status_code: int, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.message = message


def register_user(invite_code: str, email: str, display_name: str, password: str,
                  db_path: str | Path = db.DEFAULT_DB_PATH) -> dict:
    """Kompletter Registrierungs-Ablauf. Wirft RegisterError mit Status+Text.

    Ob ein Einladungscode noetig ist, entscheidet config.INVITE_ONLY: als
    lokales Werkzeug ja, als offene Plattform nein (HOOKCUT_INVITE_ONLY=0).
    Im offenen Modus wird ein mitgeschickter Code schlicht ignoriert.
    """
    email = normalize_email(email)
    display_name = display_name.strip()
    if not email or "@" not in email:
        raise RegisterError(422, "Bitte eine gueltige E-Mail-Adresse angeben.")
    if not display_name:
        raise RegisterError(422, "Bitte einen Anzeigenamen angeben.")
    pw_error = validate_password(password)
    if pw_error:
        raise RegisterError(422, pw_error)

    invite = None
    if config.INVITE_ONLY:
        invite = db.get_invite_code(invite_code.strip(), db_path=db_path)
        if not invite or invite["used_by"]:
            raise RegisterError(400, "Einladungscode ungueltig oder schon verwendet.")
    if db.get_user_by_email(email, db_path=db_path):
        raise RegisterError(409, "Diese E-Mail-Adresse ist schon registriert.")

    # Erstes Konto = Admin + uebernimmt alle Altdaten (user_id NULL).
    is_first = db.count_users(db_path=db_path) == 0
    user_id = db.create_user(email, display_name, hash_password(password),
                             is_admin=is_first, db_path=db_path)
    # Der Code wird nur eingeloest, wenn er JETZT noch frei ist. Hat ihn
    # zwischenzeitlich jemand anderes verbraucht (zwei gleichzeitige
    # Registrierungen mit demselben Code), wird das eben angelegte Konto
    # wieder entfernt - sonst entstuenden zwei Konten aus einer Einladung.
    if invite is not None and not db.mark_invite_used(invite["code"], user_id, db_path=db_path):
        db.delete_user(user_id, db_path=db_path)
        raise RegisterError(400, "Einladungscode ungueltig oder schon verwendet.")
    if is_first:
        db.claim_orphan_rows(user_id, db_path=db_path)
    user = db.get_user_by_id(user_id, db_path=db_path)
    assert user is not None
    return user


def check_login(email: str, password: str,
                db_path: str | Path = db.DEFAULT_DB_PATH) -> dict:
    """Prueft Zugangsdaten inkl. Lockout. Wirft RegisterError (401/429)."""
    email = normalize_email(email)
    attempt = db.get_login_attempt(email, db_path=db_path)
    now = _now()
    if attempt and attempt["locked_until"] and _parse_iso(attempt["locked_until"]) > now:
        raise RegisterError(
            429, "Zu viele Fehlversuche. Bitte in 15 Minuten erneut versuchen.")

    user = db.get_user_by_email(email, db_path=db_path)
    # bcrypt IMMER laufen lassen (gegen den Dummy-Hash, wenn es die E-Mail
    # nicht gibt), damit die Login-Dauer nichts ueber die Existenz verraet.
    password_ok = verify_password(password, user["password_hash"] if user else _DUMMY_HASH)
    if user and password_ok:
        db.reset_login_failures(email, db_path=db_path)
        db.delete_expired_sessions(_iso(now), db_path=db_path)
        return user

    # Fehlversuch zaehlen (auch fuer unbekannte E-Mails - kein Unterschied
    # nach aussen). Beim Erreichen der Grenze wird die Sperre gesetzt.
    fails_so_far = attempt["fail_count"] if attempt else 0
    locked_until = _iso(now + LOCKOUT) if fails_so_far + 1 >= MAX_LOGIN_FAILS else None
    db.record_login_failure(email, locked_until, db_path=db_path)
    raise RegisterError(401, "E-Mail oder Passwort falsch.")


def public_user(user: dict) -> dict:
    """Nur die Felder, die das Frontend sehen darf (nie der Passwort-Hash)."""
    return {"id": user["id"], "email": user["email"],
            "display_name": user["display_name"], "is_admin": bool(user["is_admin"])}


def get_current_user(hookcut_session: str | None = Cookie(default=None)) -> dict:
    """FastAPI-Dependency: liefert den eingeloggten User oder 401."""
    if not hookcut_session:
        raise HTTPException(401, "Nicht angemeldet")
    user = get_user_for_token(hookcut_session)
    if not user:
        raise HTTPException(401, "Nicht angemeldet")
    return user


def get_admin_user(user: dict = Depends(get_current_user)) -> dict:
    """FastAPI-Dependency: nur fuer Admin-Konten (sonst 403)."""
    if not user["is_admin"]:
        raise HTTPException(403, "Nur fuer Admins")
    return user


def _set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=SESSION_COOKIE, value=token,
        max_age=int(SESSION_TTL.total_seconds()),
        httponly=True, samesite="lax", secure=_secure_cookies(), path="/",
    )


# ---------------------------------------------------------------------------
# Routen

router = APIRouter(prefix="/auth")


class RegisterBody(BaseModel):
    # Im offenen Modus (Plattform) schickt die Oberflaeche gar keinen Code mit.
    invite_code: str = ""
    email: str
    display_name: str
    password: str


class LoginBody(BaseModel):
    email: str
    password: str


@router.get("/config")
def auth_config():
    """Was die Login-Maske wissen muss, bevor jemand angemeldet ist:
    Wird ein Einladungscode verlangt? Bewusst oeffentlich (kein Geheimnis)."""
    return {"invite_required": config.INVITE_ONLY}


@router.post("/register")
def auth_register(body: RegisterBody, response: Response):
    try:
        user = register_user(body.invite_code, body.email, body.display_name, body.password)
    except RegisterError as e:
        raise HTTPException(e.status_code, e.message)
    _set_session_cookie(response, create_session(user["id"]))
    return public_user(user)


@router.post("/login")
def auth_login(body: LoginBody, response: Response):
    try:
        user = check_login(body.email, body.password)
    except RegisterError as e:
        raise HTTPException(e.status_code, e.message)
    _set_session_cookie(response, create_session(user["id"]))
    return public_user(user)


@router.post("/logout")
def auth_logout(response: Response, hookcut_session: str | None = Cookie(default=None)):
    if hookcut_session:
        delete_session(hookcut_session)
    response.delete_cookie(SESSION_COOKIE, path="/")
    return {"ok": True}


@router.get("/me")
def auth_me(hookcut_session: str | None = Cookie(default=None)):
    return public_user(get_current_user(hookcut_session))


class UpdateMeBody(BaseModel):
    display_name: str


@router.patch("/me")
def auth_update_me(body: UpdateMeBody, user: dict = Depends(get_current_user)):
    name = body.display_name.strip()
    if not name:
        raise HTTPException(422, "Bitte einen Anzeigenamen angeben.")
    db.set_user_display_name(user["id"], name)
    return public_user(db.get_user_by_id(user["id"]))


class ChangePasswordBody(BaseModel):
    current_password: str
    new_password: str


@router.post("/change-password")
def auth_change_password(body: ChangePasswordBody, response: Response,
                         user: dict = Depends(get_current_user)):
    # Volle User-Row (mit Hash) laden - die Dependency liefert nur die
    # oeffentlichen Felder ueber get_user_for_token -> get_user_by_id, das
    # aber die ganze Row zurueckgibt; zur Sicherheit frisch holen.
    full = db.get_user_by_id(user["id"])
    if not full or not verify_password(body.current_password, full["password_hash"]):
        raise HTTPException(401, "Das aktuelle Passwort ist falsch.")
    pw_error = validate_password(body.new_password)
    if pw_error:
        raise HTTPException(422, pw_error)
    db.set_user_password_hash(user["id"], hash_password(body.new_password))
    # Alle Sitzungen abmelden (auch andere Geraete), dann fuer den aktuellen
    # Browser eine frische Session ausstellen - man bleibt hier eingeloggt.
    db.delete_sessions_for_user(user["id"])
    _set_session_cookie(response, create_session(user["id"]))
    return {"ok": True}


# ---------------------------------------------------------------------------
# Admin-Routen (nur fuer Admin-Konten): Einladungen & Nutzerverwaltung

admin_router = APIRouter(prefix="/admin")


def _public_invite(inv: dict) -> dict:
    return {"code": inv["code"], "created_at": inv["created_at"],
            "used_by_email": inv.get("used_by_email"), "used": inv["used_by"] is not None}


@admin_router.get("/invites")
def admin_list_invites(_: dict = Depends(get_admin_user)):
    return [_public_invite(i) for i in db.list_invite_codes()]


@admin_router.post("/invites")
def admin_create_invite(admin: dict = Depends(get_admin_user)):
    code = db.create_invite_code(secrets.token_urlsafe(9), created_by=admin["id"])
    inv = db.get_invite_code(code)
    return _public_invite({**inv, "used_by_email": None})


@admin_router.get("/users")
def admin_list_users(_: dict = Depends(get_admin_user)):
    # Niemals den password_hash ausliefern.
    return [
        {"id": u["id"], "email": u["email"], "display_name": u["display_name"],
         "is_admin": bool(u["is_admin"]), "created_at": u["created_at"]}
        for u in db.list_users()
    ]
