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
import json
import re
import secrets
import shutil
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import bcrypt
from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response
from pydantic import BaseModel

from backend import config, db, storage

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


def client_ip(request: Request) -> str:
    """Die Adresse, von der die Anfrage wirklich kommt.

    Ohne Proxy ist das schlicht die Gegenstelle. Hinter einem Proxy (Render)
    ist request.client.host IMMER die Adresse des Proxys - ein Rate-Limit
    darauf wuerde alle Nutzer gemeinsam aussperren.

    ACHTUNG, hier steckt der Fehler, den fast jeder macht: X-Forwarded-For
    ist eine LISTE, und man nimmt NICHT den ersten Eintrag. Jeder Proxy
    haengt hinten die Adresse an, von der ER die Verbindung bekommen hat.
    Schickt ein Angreifer selbst "X-Forwarded-For: 1.2.3.4", steht das
    vorne, und Render haengt die echte Adresse dahinter:
        "1.2.3.4, <echte Adresse>"
    Der erste Eintrag ist also frei erfunden, der LETZTE stammt von dem
    Proxy, dem wir vertrauen. Deshalb von hinten lesen.

    Und selbst das gilt nur, wenn wirklich ein Proxy davorsteht - sonst
    koennte sich jeder eine beliebige Adresse ausdenken und jedes Limit
    umgehen. Darum der Schalter config.TRUST_PROXY (lokal aus).
    """
    if config.TRUST_PROXY:
        weitergereicht = request.headers.get("x-forwarded-for", "")
        eintraege = [t.strip() for t in weitergereicht.split(",") if t.strip()]
        if eintraege:
            return eintraege[-1]
    return request.client.host if request.client else "unbekannt"


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


_UMLAUTE = {"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"}


def make_handle(anzeigename: str, db_path: str | Path = db.DEFAULT_DB_PATH) -> str:
    """Eindeutiges Kuerzel fuer die Profil-Adresse (@name) aus dem Anzeigenamen.

    Umlaute werden ausgeschrieben, alles andere ausser a-z und 0-9 faellt weg.
    Ist das Kuerzel vergeben, wird durchnummeriert (yng, yng2, yng3 ...).
    """
    basis = anzeigename.strip().lower()
    for umlaut, ersatz in _UMLAUTE.items():
        basis = basis.replace(umlaut, ersatz)
    basis = re.sub(r"[^a-z0-9]", "", basis)[:20]
    if not basis:
        basis = "musiker"
    if not db.handle_exists(basis, db_path=db_path):
        return basis
    for n in range(2, 1000):
        kandidat = f"{basis}{n}"
        if not db.handle_exists(kandidat, db_path=db_path):
            return kandidat
    # Praktisch unerreichbar - lieber ein haessliches Kuerzel als eine Ausnahme.
    return f"{basis}{secrets.token_hex(4)}"


def ensure_profile(user: dict, db_path: str | Path = db.DEFAULT_DB_PATH) -> dict:
    """Profil holen und bei Bedarf anlegen.

    Konten aus der Zeit vor den Profilen (z.B. das des Besitzers) haben noch
    keins - statt einer Migration wird es beim ersten Zugriff nachgezogen.

    Wird aus get_current_user heraus aufgerufen, gilt also fuer JEDE
    angemeldete Anfrage. Das ist Absicht: die Listen fuer Feed, Kommentare und
    Interessenten verbinden hart mit profiles - ein Konto ohne Profil wuerde
    dort lautlos herausfallen, ohne dass irgendetwas fehlschlaegt. Statt das an
    jeder Schreibstelle einzeln zu bedenken (und eine zu vergessen), kann es
    hier gar nicht mehr passieren.

    Zwei gleichzeitige Anfragen desselben neuen Kontos koennen beide feststellen,
    dass ein Profil fehlt - deshalb wird ein Konflikt abgefangen und danach neu
    gelesen: entweder hat die andere Anfrage unser Profil angelegt (gleicher
    Schluessel), oder ein fremdes Konto hat sich das Kuerzel geschnappt, dann
    liefert make_handle beim naechsten Versuch ein anderes.
    """
    profil = db.get_profile(user["id"], db_path=db_path)
    if profil:
        return profil
    for _ in range(5):
        try:
            db.create_profile(user["id"], make_handle(user["display_name"], db_path=db_path),
                              user["display_name"], db_path=db_path)
        except sqlite3.IntegrityError:
            pass
        profil = db.get_profile(user["id"], db_path=db_path)
        if profil:
            return profil
    raise HTTPException(500, "Profil konnte nicht angelegt werden.")


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
    # Erst NACH dem Einloesen anlegen: im Rueckbau-Fall oben gibt es dann kein
    # Profil, das den Fremdschluessel auf users blockieren wuerde.
    db.create_profile(user_id, make_handle(display_name, db_path=db_path),
                      display_name, db_path=db_path)
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


# Erlaubte Profil-Links. Bewusst eine feste Liste statt "irgendeine URL":
# so landet nichts Unerwartetes als anklickbarer Link auf fremden Profilen.
PROFILE_LINK_KEYS = ("spotify", "instagram", "youtube", "tiktok", "soundcloud", "website")
BIO_MAX = 500
CITY_MAX = 80
ARTIST_NAME_MAX = 60
GENRES_MAX = 5


def clean_link(url: str) -> str | None:
    """Nur http(s) durchlassen. Ohne diese Pruefung koennte jemand einen
    `javascript:`-Link im Profil hinterlegen, den andere anklicken."""
    url = url.strip()
    if not url:
        return None
    if not url.lower().startswith(("http://", "https://")):
        return None
    return url[:300]


def public_profile(profile: dict) -> dict:
    """Profil so, wie andere Musiker es sehen duerfen."""
    try:
        links = json.loads(profile["links_json"] or "{}")
    except ValueError:
        links = {}
    genres = [g for g in (profile["genres"] or "").split(",") if g]
    return {
        "user_id": profile["user_id"],
        "handle": profile["handle"],
        "artist_name": profile["artist_name"],
        "bio": profile["bio"],
        "city": profile["city"],
        "genres": genres,
        "links": {k: v for k, v in links.items() if k in PROFILE_LINK_KEYS},
        "has_avatar": bool(profile["avatar_path"]),
        "created_at": profile["created_at"],
    }


def profile_detail(profile: dict, viewer: dict | None = None,
                   db_path: str | Path = db.DEFAULT_DB_PATH) -> dict:
    """Profil MIT Folge-Zaehlern - fuer Profilseiten.

    Bewusst getrennt von public_profile(): im Feed haengt an jedem Beitrag ein
    Autor-Profil, und dort waeren zwei Zaehl-Abfragen pro Beitrag eine
    unnoetige Bremse. Zaehler gibt es nur da, wo sie auch angezeigt werden.
    """
    daten = public_profile(profile)
    daten.update(db.follow_counts(profile["user_id"], db_path=db_path))
    if viewer is not None:
        daten["is_self"] = viewer["id"] == profile["user_id"]
        daten["is_following"] = (
            False if daten["is_self"]
            else db.is_following(viewer["id"], profile["user_id"], db_path=db_path)
        )
    return daten


def get_current_user(hookcut_session: str | None = Cookie(default=None)) -> dict:
    """FastAPI-Dependency: liefert den eingeloggten User oder 401.

    Zieht nebenbei ein fehlendes Profil nach (siehe ensure_profile) - damit
    ist ueberall im Netzwerk garantiert, dass zu jedem Konto ein Profil
    existiert. Kostet nur beim allerersten Aufruf eines Altkontos etwas.
    """
    if not hookcut_session:
        raise HTTPException(401, "Nicht angemeldet")
    user = get_user_for_token(hookcut_session)
    if not user:
        raise HTTPException(401, "Nicht angemeldet")
    ensure_profile(user)
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
    """Was die Oberflaeche ueber diesen Server wissen muss, bevor jemand
    angemeldet ist. Bewusst oeffentlich - hier steht nichts Geheimes.

    - invite_required: zeigt die Login-Maske das Code-Feld?
    - tools_enabled:   laufen hier die Video-Werkzeuge? Auf dem gehosteten
      Server nicht (kein Chrome/WebGPU), dann blendet die Oberflaeche sie aus
      und startet auf dem Feed statt auf dem Werkzeug-Dashboard.
    """
    return {"invite_required": config.INVITE_ONLY, "tools_enabled": config.TOOLS_ENABLED}


@router.post("/register")
def auth_register(body: RegisterBody, request: Request, response: Response):
    # Bremse gegen massenhaft angelegte Konten. Gezaehlt werden nur
    # ERFOLGREICHE Registrierungen: wer sich beim Einladungscode vertippt,
    # soll sich nicht selbst aussperren - und der Missbrauch, um den es
    # geht, besteht ja gerade aus gelungenen Anmeldungen.
    ip = client_ip(request)
    seit = _iso(_now() - timedelta(hours=1))
    if db.count_recent_signups(ip, seit) >= config.REGISTER_MAX_PER_HOUR:
        raise HTTPException(
            429,
            "Von diesem Anschluss wurden gerade viele Konten angelegt. "
            "Bitte versuch es in einer Stunde noch einmal.")

    try:
        user = register_user(body.invite_code, body.email, body.display_name, body.password)
    except RegisterError as e:
        raise HTTPException(e.status_code, e.message)

    db.record_signup(ip)
    # Bei Gelegenheit aufraeumen: Adressen sollen nicht laenger liegen
    # bleiben, als die Bremse sie braucht (siehe Kommentar am Schema).
    db.prune_signup_attempts(seit)

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


class DeleteMeBody(BaseModel):
    password: str


@router.delete("/me")
def auth_delete_me(body: DeleteMeBody, response: Response,
                   user: dict = Depends(get_current_user)):
    """Konto und alle eigenen Inhalte loeschen (DSGVO Art. 17).

    Wer sich registrieren kann, muss auch wieder gehen koennen - und zwar
    selbst, ohne den Betreiber zu fragen.

    Das Passwort wird verlangt, weil das hier unwiderruflich ist: ein
    offenstehender Browser soll nicht reichen, um ein fremdes Konto samt
    aller Beitraege zu vernichten.
    """
    full = db.get_user_by_id(user["id"])
    if not full or not verify_password(body.password, full["password_hash"]):
        raise HTTPException(401, "Das Passwort ist falsch.")

    # Der letzte Betreiber darf nicht gehen, solange noch jemand da ist:
    # sonst bleibt eine Plattform ohne Verwaltung zurueck - Meldungen koennte
    # niemand mehr bearbeiten und Einladungen niemand mehr erzeugen. Die
    # "erstes Konto wird Admin"-Regel hilft dann auch nicht mehr, weil es
    # ja schon Konten gibt.
    if full["is_admin"] and db.count_admins() <= 1 and db.count_users() > 1:
        raise HTTPException(
            409,
            "Du bist das einzige Konto mit Verwaltungsrechten. Bitte mach erst "
            "jemand anderen zum Administrator - sonst koennte niemand mehr "
            "gemeldete Inhalte bearbeiten.")

    # Erst die DB (die kennt die Beitrags-IDs), dann die Dateien. Andersherum
    # blieben bei einem Fehler Eintraege ohne Dateien zurueck.
    post_ids = db.delete_user_completely(user["id"])
    for post_id in post_ids:
        shutil.rmtree(storage.post_dir(post_id), ignore_errors=True)

    response.delete_cookie(SESSION_COOKIE, path="/")
    return {"ok": True, "geloeschte_beitraege": len(post_ids)}


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


# ---------------------------------------------------------------------------
# Musiker-Profile: die oeffentliche Seite eines Kontos (Basis fuers Netzwerk)

profiles_router = APIRouter(prefix="/profiles")


class UpdateProfileBody(BaseModel):
    artist_name: str | None = None
    bio: str | None = None
    city: str | None = None
    genres: list[str] | None = None
    links: dict[str, str] | None = None


@profiles_router.get("/me")
def profile_me(user: dict = Depends(get_current_user)):
    return profile_detail(ensure_profile(user), viewer=user)


@profiles_router.patch("/me")
def profile_update(body: UpdateProfileBody, user: dict = Depends(get_current_user)):
    ensure_profile(user)  # Altkonten haben evtl. noch keins
    felder: dict = {}

    if body.artist_name is not None:
        name = body.artist_name.strip()
        if not name:
            raise HTTPException(422, "Bitte einen Kuenstlernamen angeben.")
        felder["artist_name"] = name[:ARTIST_NAME_MAX]
    if body.bio is not None:
        felder["bio"] = body.bio.strip()[:BIO_MAX]
    if body.city is not None:
        felder["city"] = body.city.strip()[:CITY_MAX]
    if body.genres is not None:
        # Komma ist das Trennzeichen in der Spalte - darf im Genre nicht vorkommen.
        sauber = [g.strip().replace(",", " ")[:30] for g in body.genres if g.strip()]
        felder["genres"] = ",".join(sauber[:GENRES_MAX])
    if body.links is not None:
        links = {}
        for schluessel, wert in body.links.items():
            if schluessel not in PROFILE_LINK_KEYS:
                continue
            geprueft = clean_link(wert)
            if geprueft:
                links[schluessel] = geprueft
        felder["links_json"] = json.dumps(links)

    db.update_profile(user["id"], **felder)
    profil = db.get_profile(user["id"])
    assert profil is not None
    return public_profile(profil)


def _profil_per_handle(handle: str) -> dict:
    profil = db.get_profile_by_handle(handle.strip().lower())
    if not profil:
        raise HTTPException(404, "Profil nicht gefunden")
    return profil


@profiles_router.get("/{handle}")
def profile_by_handle(handle: str, user: dict = Depends(get_current_user)):
    """Fremdes Profil ansehen. Vorerst nur fuer angemeldete Nutzer - oeffentliche
    Profilseiten fuer Nicht-Angemeldete kommen mit dem Livegang."""
    return profile_detail(_profil_per_handle(handle), viewer=user)


@profiles_router.post("/{handle}/follow")
def profile_follow(handle: str, user: dict = Depends(get_current_user)):
    profil = _profil_per_handle(handle)
    if profil["user_id"] == user["id"]:
        raise HTTPException(422, "Du kannst dir nicht selbst folgen.")
    db.follow(user["id"], profil["user_id"])
    return profile_detail(profil, viewer=user)


@profiles_router.delete("/{handle}/follow")
def profile_unfollow(handle: str, user: dict = Depends(get_current_user)):
    profil = _profil_per_handle(handle)
    db.unfollow(user["id"], profil["user_id"])
    return profile_detail(profil, viewer=user)
