"""Das Musiker-Netzwerk: offene Projekte, Feed, Interesse, Kommentare.

Bewusst von main.py getrennt: dort liegt das Render-WERKZEUG (Sync, Hook,
Styles, Packs, Canvas), hier das soziale NETZWERK. Zwei Produkte, zwei
Dateien - main.py war mit beidem zusammen auf 1350 Zeilen gewachsen.

WICHTIG - hier gilt eine andere Sichtbarkeits-Regel als im Werkzeug:
Beitraege und Kommentare darf JEDES angemeldete Mitglied lesen (sonst gaebe
es keinen Feed); aendern und loeschen darf nur der Autor, und zwar mit 403
statt 404 - die Existenz eines Beitrags ist im Feed ohnehin oeffentlich, ein
"gibt es nicht" waere schlicht gelogen. Dafuer _own_public() unten; das
_own() aus main.py bleibt fuer alles Private (Projekte, Jobs, Packs, Canvas).
"""
from __future__ import annotations

import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from backend import auth, db, storage
from backend.pipeline.render_sync import _probe_duration_sec

router = APIRouter()


class UploadTooLarge(Exception):
    pass


def _save_upload_capped(upload: UploadFile, dest: Path, max_bytes: int) -> Path:
    """Datei mit harter Obergrenze speichern.

    Das _save_upload() in main.py schreibt stumpf alles auf die Platte - fuer
    die lokalen Werkzeug-Flows in Ordnung, fuer Dateien von FREMDEN aber ein
    Fuell-die-Platte-Risiko. Hier wird blockweise kopiert und beim
    Ueberschreiten sofort abgebrochen; die halbe Datei wird weggeraeumt.
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    geschrieben = 0
    try:
        with dest.open("wb") as f:
            while True:
                block = upload.file.read(64 * 1024)
                if not block:
                    break
                geschrieben += len(block)
                if geschrieben > max_bytes:
                    raise UploadTooLarge()
                f.write(block)
    except UploadTooLarge:
        dest.unlink(missing_ok=True)
        raise
    return dest


def _own_public(row: dict | None, user: dict, was: str = "Beitrag") -> dict:
    """Nur der Autor darf aendern/loeschen - siehe Modul-Docstring."""
    if not row:
        raise HTTPException(404, f"{was} nicht gefunden")
    if row.get("user_id") != user["id"]:
        raise HTTPException(403, f"Das ist nicht dein {was}.")
    return row


# Wonach in einem offenen Projekt gesucht wird. Feste Liste, weil danach
# gefiltert wird - freie Eingaben wuerden die Suche wertlos machen.
POST_CATEGORIES = {
    "refrain": "Refrain / Hook",
    "beat": "Beat / Instrumental",
    "feature": "Feature / Gastpart",
    "mixing": "Mixing / Mastering",
}

POST_AUDIO_SUFFIXES = (".mp3", ".m4a", ".wav", ".ogg")
# 30s WAV (44.1kHz, 16bit, stereo) sind ~5,3 MB - 8 MB laesst echte
# Hoerproben durch und stoppt alles, was die Platte volllaufen liesse.
POST_AUDIO_MAX_BYTES = 8 * 1024 * 1024
POST_AUDIO_MAX_SEC = 30.0
POST_AUDIO_TOLERANCE_SEC = 2.0

POST_TITLE_MAX = 120
POST_BODY_MAX = 2000
POST_GENRES_MAX = 5

# Spam-Bremse: ohne die ist ein kleines Netzwerk an einem Nachmittag zu.
POST_MAX_PER_HOUR = 10

# Meldegruende. Feste Liste statt Freitext, damit der Betreiber die Meldungen
# sortieren kann - der Freitext kommt zusaetzlich als Notiz dazu.
# "rechte" steht bewusst oben: das ist bei einem Musiker-Netzwerk der
# haeufigste Fall (fremder Beat, fremdes Sample).
REPORT_REASONS = {
    "rechte": "Verletzt meine Rechte (Beat, Sample, Text, Aufnahme)",
    "beleidigung": "Beleidigung, Bedrohung oder Hetze",
    "spam": "Spam oder Werbung",
    "illegal": "Strafbarer oder jugendgefährdender Inhalt",
    "sonstiges": "Etwas anderes",
}

REPORT_NOTE_MAX = 1000
# Auch Melden laesst sich missbrauchen (jemanden zuschuetten). 20 pro Stunde
# reicht fuer jede ehrliche Nutzung deutlich aus.
REPORT_MAX_PER_HOUR = 20

# Kommentare sind das Einfallstor fuer Belaestigung: sie landen unter FREMDEN
# Beitraegen. Ohne Bremse kamen im Test ueber eine halbe Million pro Stunde
# durch. 60 sind fuer ein Gespraech reichlich und stoppen jede Flut.
# Gezaehlt wird ueber alle Beitraege hinweg - sonst verteilt ein Skript die
# Flut einfach auf viele Beitraege.
COMMENT_MAX_PER_HOUR = 60


def _post_public(post: dict, autor_profil: dict | None = None) -> dict:
    """Beitrag so, wie ihn andere Mitglieder sehen. Der Dateipfad der
    Hoerprobe bleibt drinnen - nach aussen geht nur has_audio."""
    daten = {
        "id": post["id"],
        "user_id": post["user_id"],
        "title": post["title"],
        "body": post["body"],
        "genres": [g for g in (post["genres"] or "").split(",") if g],
        "bpm": post["bpm"],
        "categories": post.get("categories", []),
        "has_audio": bool(post["audio_path"]),
        "audio_duration_sec": post["audio_duration_sec"],
        "open_state": post["open_state"],
        "created_at": post["created_at"],
    }
    if autor_profil is not None:
        daten["author"] = auth.public_profile(autor_profil)
    return daten


def _sichtbarer_post(post_id: str) -> dict:
    """Beitrag holen oder 404. Ausgeblendetes existiert fuer Mitglieder nicht."""
    post = db.get_post(post_id)
    if not post or post["status"] != "active":
        raise HTTPException(404, "Beitrag nicht gefunden")
    return post


def _kategorien_pruefen(roh: str) -> list[str]:
    gewaehlt = [c.strip().lower() for c in roh.split(",") if c.strip()]
    gueltig = [c for c in gewaehlt if c in POST_CATEGORIES]
    if not gueltig:
        raise HTTPException(422, "Bitte mindestens eine gueltige Kategorie angeben.")
    return sorted(set(gueltig))


def _bpm_pruefen(bpm: int | None) -> int | None:
    if bpm is None or bpm == 0:
        return None
    if not 40 <= bpm <= 300:
        raise HTTPException(422, "BPM muss zwischen 40 und 300 liegen.")
    return bpm


def _hoerprobe_speichern(audio: UploadFile, post_id: str) -> tuple[Path, float]:
    """Hoerprobe pruefen und ablegen. Wirft HTTPException; der Aufrufer raeumt
    bei einem Fehler den Beitrag wieder weg."""
    suffix = Path(audio.filename or "").suffix.lower()
    if suffix not in POST_AUDIO_SUFFIXES:
        raise HTTPException(
            415, f"Nur diese Formate: {', '.join(POST_AUDIO_SUFFIXES)}")
    ziel = storage.post_audio_path(post_id, suffix)
    try:
        _save_upload_capped(audio, ziel, POST_AUDIO_MAX_BYTES)
    except UploadTooLarge:
        raise HTTPException(
            413, f"Die Hoerprobe ist zu gross (max. {POST_AUDIO_MAX_BYTES // (1024*1024)} MB).")
    try:
        dauer = _probe_duration_sec(ziel)
    except Exception:
        # ffprobe scheitert auch an Dateien, die gar kein Audio sind - das ist
        # eine Nutzereingabe, also 422 und kein 500.
        ziel.unlink(missing_ok=True)
        raise HTTPException(422, "Die Datei konnte nicht gelesen werden. Ist das wirklich Audio?")
    if dauer > POST_AUDIO_MAX_SEC + POST_AUDIO_TOLERANCE_SEC:
        ziel.unlink(missing_ok=True)
        raise HTTPException(
            422, f"Die Hoerprobe ist zu lang (max. {int(POST_AUDIO_MAX_SEC)} Sekunden).")
    return ziel, dauer


@router.get("/post-categories")
def list_post_categories():
    """Katalog fuer die Oberflaeche (oeffentlich, kein Geheimnis)."""
    return [{"key": k, "name": v} for k, v in POST_CATEGORIES.items()]


@router.post("/posts")
def create_post(title: str = Form(...), categories: str = Form(...),
                body: str = Form(""), genres: str = Form(""), bpm: int = Form(0),
                audio: UploadFile | None = File(None),
                user: dict = Depends(auth.require_verified_email)):
    titel = title.strip()
    if not titel:
        raise HTTPException(422, "Bitte einen Titel angeben.")
    kategorien = _kategorien_pruefen(categories)
    geprueftes_bpm = _bpm_pruefen(bpm)

    seit = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    if db.count_recent_posts(user["id"], seit) >= POST_MAX_PER_HOUR:
        raise HTTPException(
            429, "Du hast gerade sehr viel gepostet. Bitte versuch es spaeter noch mal.")

    genre_liste = [g.strip().replace(",", " ")[:30]
                   for g in genres.split(",") if g.strip()][:POST_GENRES_MAX]
    post_id = db.create_post(
        user_id=user["id"], title=titel[:POST_TITLE_MAX],
        body=body.strip()[:POST_BODY_MAX], genres=",".join(genre_liste),
        bpm=geprueftes_bpm, categories=kategorien,
    )
    # Die Datei braucht die ID, also erst die Zeile. Scheitert die Pruefung,
    # muss beides wieder weg - gleiches Rueckbau-Muster wie beim
    # Einladungscode in auth.register_user.
    if audio is not None and audio.filename:
        try:
            pfad, dauer = _hoerprobe_speichern(audio, post_id)
        except HTTPException:
            db.delete_post(post_id)
            shutil.rmtree(storage.post_dir(post_id), ignore_errors=True)
            raise
        db.update_post(post_id, audio_path=str(pfad), audio_duration_sec=dauer)
    return _post_public(db.get_post(post_id))


@router.get("/posts/{post_id}")
def get_post(post_id: str, _: dict = Depends(auth.get_current_user)):
    post = _sichtbarer_post(post_id)
    return _post_public(post, auth.ensure_profile(db.get_user_by_id(post["user_id"])))


@router.patch("/posts/{post_id}")
def update_post(post_id: str, title: str | None = Form(None), body: str | None = Form(None),
                open_state: str | None = Form(None), categories: str | None = Form(None),
                user: dict = Depends(auth.get_current_user)):
    _own_public(_sichtbarer_post(post_id), user)
    felder: dict = {}
    if title is not None:
        titel = title.strip()
        if not titel:
            raise HTTPException(422, "Bitte einen Titel angeben.")
        felder["title"] = titel[:POST_TITLE_MAX]
    if body is not None:
        felder["body"] = body.strip()[:POST_BODY_MAX]
    if open_state is not None:
        if open_state not in ("open", "closed"):
            raise HTTPException(422, "open_state muss 'open' oder 'closed' sein.")
        felder["open_state"] = open_state
    if categories is not None:
        db.set_post_categories(post_id, _kategorien_pruefen(categories))
    db.update_post(post_id, **felder)
    return _post_public(db.get_post(post_id))


@router.delete("/posts/{post_id}")
def delete_post(post_id: str, user: dict = Depends(auth.get_current_user)):
    _own_public(_sichtbarer_post(post_id), user)
    db.delete_post(post_id)
    # Die Hoerprobe muss mit - sonst bleibt sie fuer immer auf der Platte.
    shutil.rmtree(storage.post_dir(post_id), ignore_errors=True)
    return {"ok": True}


@router.get("/posts/{post_id}/audio")
def get_post_audio(post_id: str, _: dict = Depends(auth.get_current_user)):
    post = _sichtbarer_post(post_id)
    if not post["audio_path"] or not Path(post["audio_path"]).exists():
        raise HTTPException(404, "Keine Hoerprobe vorhanden")
    return FileResponse(post["audio_path"])


@router.post("/admin/posts/{post_id}/hide")
def admin_hide_post(post_id: str, _: dict = Depends(auth.get_admin_user)):
    """Notaus fuer den Betreiber. Der vollstaendige Melde-Ablauf fuer Nutzer
    kommt in Phase 2 - aber etwas entfernen zu koennen muss ab dem ersten
    fremden Beitrag moeglich sein."""
    if not db.get_post(post_id):
        raise HTTPException(404, "Beitrag nicht gefunden")
    db.update_post(post_id, status="hidden")
    return {"ok": True}


def _autor_aus_zeile(zeile: dict) -> dict:
    """Das per JOIN mitgelesene Autorenprofil aus einer Ergebniszeile.

    Feed und Kommentare lesen dasselbe Profil-Set mit; ohne diesen Helfer
    stuende die Feldliste zweimal da und wuerde beim naechsten neuen
    Profilfeld an einer der beiden Stellen vergessen.
    """
    return {
        "user_id": zeile["user_id"], "handle": zeile["handle"],
        "artist_name": zeile["artist_name"], "bio": zeile["bio"],
        "city": zeile["city"], "genres": zeile["author_genres"],
        "links_json": zeile["links_json"], "avatar_path": zeile["avatar_path"],
        "created_at": zeile["author_created_at"],
    }


def _feed_eintrag(zeile: dict) -> dict:
    """Feed-Zeile (Beitrag + Autorenprofil aus dem JOIN) in die Antwort."""
    return _post_public(zeile, _autor_aus_zeile(zeile))


def _mit_zaehlern(eintraege: list[dict]) -> list[dict]:
    """Interesse-/Kommentarzahlen fuer die ganze Liste in EINEM Rutsch
    nachtragen - pro Beitrag zu zaehlen waere im Feed eine unnoetige Bremse."""
    zaehler = db.post_counts([e["id"] for e in eintraege])
    for e in eintraege:
        e.update(zaehler[e["id"]])
    return eintraege


def _feed_kategorien(categories: str) -> list[str]:
    """Kategorie-Filter aus der URL - Unbekanntes wird still verworfen,
    damit ein Tippfehler nicht die ganze Seite scheitern laesst."""
    return [c for c in (x.strip().lower() for x in categories.split(",")) if c in POST_CATEGORIES]


@router.get("/feed/discover")
def feed_discover(categories: str = "", genre: str = "", open_only: bool = True,
                  before: str | None = None, limit: int = 20,
                  user: dict = Depends(auth.get_current_user)):
    """Entdecken: alle offenen Projekte. Das ist die Startansicht - wer neu
    ist, folgt noch niemandem und saehe im "Folge ich"-Feed nichts."""
    zeilen = db.list_feed(user["id"], only_following=False,
                          categories=_feed_kategorien(categories), genre=genre,
                          open_only=open_only, before=before, limit=limit)
    return _mit_zaehlern([_feed_eintrag(z) for z in zeilen])


@router.get("/feed")
def feed_following(categories: str = "", genre: str = "", open_only: bool = True,
                   before: str | None = None, limit: int = 20,
                   user: dict = Depends(auth.get_current_user)):
    """Eigene Beitraege plus die der Profile, denen man folgt."""
    zeilen = db.list_feed(user["id"], only_following=True,
                          categories=_feed_kategorien(categories), genre=genre,
                          open_only=open_only, before=before, limit=limit)
    return _mit_zaehlern([_feed_eintrag(z) for z in zeilen])


@router.get("/profiles/{handle}/posts")
def posts_by_profile(handle: str, limit: int = 50,
                     _: dict = Depends(auth.get_current_user)):
    """Beitraege einer Person - fuer die Profilseite. Zeigt auch erledigte,
    damit man sieht, woran jemand gearbeitet hat."""
    profil = db.get_profile_by_handle(handle.strip().lower())
    if not profil:
        raise HTTPException(404, "Profil nicht gefunden")
    return _mit_zaehlern(
        [_post_public(p) for p in db.list_posts_by_user(profil["user_id"], limit=limit)])


COMMENT_MAX = 1000


def _kommentar_public(zeile: dict) -> dict:
    autor = _autor_aus_zeile(zeile)
    return {"id": zeile["id"], "post_id": zeile["post_id"], "body": zeile["body"],
            "created_at": zeile["created_at"], "author": auth.public_profile(autor)}


@router.post("/posts/{post_id}/interest")
def add_interest(post_id: str, user: dict = Depends(auth.get_current_user)):
    post = _sichtbarer_post(post_id)
    if post["user_id"] == user["id"]:
        raise HTTPException(422, "Am eigenen Projekt kannst du kein Interesse zeigen.")
    db.add_interest(post_id, user["id"])
    return {"ok": True, "interested": True}


@router.delete("/posts/{post_id}/interest")
def remove_interest(post_id: str, user: dict = Depends(auth.get_current_user)):
    _sichtbarer_post(post_id)
    db.remove_interest(post_id, user["id"])
    return {"ok": True, "interested": False}


@router.get("/posts/{post_id}/interest")
def list_interest(post_id: str, user: dict = Depends(auth.get_current_user)):
    """Wer hat Interesse - mit Profil.

    Das IST der Kontaktweg: Direktnachrichten gibt es (noch) nicht, aber die
    Profile tragen die Links zu Instagram, Spotify & Co. Der Autor sieht also,
    wer helfen will, und erreicht die Person ueber ihre eigenen Kanaele.

    Die Namensliste bekommt NUR der Autor. Alle anderen sehen ihren eigenen
    Zustand und die Anzahl - so viel zeigt die Oberflaeche auch, und die
    Schnittstelle soll nicht mehr herausgeben als die Ansicht.
    """
    post = _sichtbarer_post(post_id)
    leute = db.list_interested(post_id)
    ist_autor = post["user_id"] == user["id"]
    return {
        "interested": db.has_interest(post_id, user["id"]),
        "count": len(leute),
        "people": [auth.public_profile(p) for p in leute] if ist_autor else [],
    }


@router.get("/posts/{post_id}/comments")
def list_comments(post_id: str, _: dict = Depends(auth.get_current_user)):
    _sichtbarer_post(post_id)
    return [_kommentar_public(z) for z in db.list_comments(post_id)]


@router.post("/posts/{post_id}/comments")
def create_comment(post_id: str, body: str = Form(...),
                   user: dict = Depends(auth.require_verified_email)):
    _sichtbarer_post(post_id)
    text = body.strip()
    if not text:
        raise HTTPException(422, "Bitte einen Text eingeben.")

    seit = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    if db.count_recent_comments(user["id"], seit) >= COMMENT_MAX_PER_HOUR:
        raise HTTPException(
            429, "Du hast gerade sehr viel kommentiert. Bitte versuch es später noch mal.")
    comment_id = db.create_comment(post_id, user["id"], text[:COMMENT_MAX])
    return next(k for k in (_kommentar_public(z) for z in db.list_comments(post_id))
                if k["id"] == comment_id)


@router.delete("/comments/{comment_id}")
def delete_comment(comment_id: str, user: dict = Depends(auth.get_current_user)):
    """Loeschen darf der Verfasser - UND der Eigentuemer des Beitrags: im
    eigenen Projekt aufraeumen zu koennen ist die einfachste Form von
    Hausrecht."""
    kommentar = db.get_comment(comment_id)
    if not kommentar:
        raise HTTPException(404, "Kommentar nicht gefunden")
    post = db.get_post(kommentar["post_id"])
    darf = kommentar["user_id"] == user["id"] or (post and post["user_id"] == user["id"])
    if not darf:
        raise HTTPException(403, "Das ist nicht dein Kommentar.")
    db.delete_comment(comment_id)
    return {"ok": True}


# --- Melden (DSA) ----------------------------------------------------------
# Ein auffindbarer Weg, Inhalte zu melden, UND eine Reaktion darauf sind
# Pflicht, sobald Fremde Inhalte hochladen. Der Admin-Notaus
# (/admin/posts/{id}/hide) allein reicht dafuer nicht: er setzt voraus, dass
# der Betreiber selbst etwas bemerkt.

@router.get("/report-reasons")
def list_report_reasons():
    """Katalog fuer die Auswahl im Melden-Dialog. Ohne Anmeldung lesbar wie
    die anderen statischen Kataloge auch."""
    return [{"key": k, "label": v} for k, v in REPORT_REASONS.items()]


def _meldeziel_pruefen(target_type: str, target_id: str) -> dict:
    """Gibt es das ueberhaupt? Meldungen auf Luft wuerden die Liste des
    Betreibers mit Karteileichen fuellen."""
    if target_type == "post":
        ziel = db.get_post(target_id)
    elif target_type == "comment":
        ziel = db.get_comment(target_id)
    else:
        raise HTTPException(422, "Es lassen sich nur Beiträge und Kommentare melden.")
    if not ziel:
        raise HTTPException(404, "Der gemeldete Inhalt existiert nicht (mehr).")
    return ziel


@router.post("/reports")
def create_report(target_type: str = Form(...), target_id: str = Form(...),
                  reason: str = Form(...), note: str = Form(""),
                  user: dict = Depends(auth.get_current_user)):
    if reason not in REPORT_REASONS:
        raise HTTPException(422, "Bitte einen Grund aus der Liste wählen.")
    ziel = _meldeziel_pruefen(target_type, target_id)
    if ziel["user_id"] == user["id"]:
        raise HTTPException(422, "Eigene Inhalte kannst du löschen statt melden.")

    seit = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    if db.count_recent_reports(user["id"], seit) >= REPORT_MAX_PER_HOUR:
        raise HTTPException(
            429, "Du hast gerade sehr viel gemeldet. Bitte versuch es später noch mal.")

    report_id = db.create_report(target_type, target_id, user["id"], reason,
                                 note.strip()[:REPORT_NOTE_MAX])
    # Doppelt gemeldet ist kein Fehler: fuer die meldende Person sieht es
    # genauso aus wie beim ersten Mal, und die Liste bleibt sauber.
    return {"ok": True, "neu": report_id is not None}


@router.get("/admin/reports")
def admin_list_reports(status: str = "open", _: dict = Depends(auth.get_admin_user)):
    """Arbeitsliste des Betreibers. Der gemeldete Inhalt kommt gleich mit -
    sonst muesste man fuer jede Meldung erst nachschlagen, worum es geht."""
    if status not in ("open", "hidden", "kept", "alle"):
        raise HTTPException(422, "Unbekannter Status.")
    meldungen = db.list_reports(None if status == "alle" else status)

    ergebnis = []
    for m in meldungen:
        if m["target_type"] == "post":
            ziel = db.get_post(m["target_id"])
            vorschau = ziel["title"] if ziel else None
        else:
            ziel = db.get_comment(m["target_id"])
            vorschau = ziel["body"][:200] if ziel else None
        melder = db.get_user_by_id(m["reporter_id"])
        ergebnis.append({
            "id": m["id"],
            "target_type": m["target_type"],
            "target_id": m["target_id"],
            "reason": m["reason"],
            "reason_label": REPORT_REASONS.get(m["reason"], m["reason"]),
            "note": m["note"],
            "status": m["status"],
            "created_at": m["created_at"],
            "reporter_name": melder["display_name"] if melder else "(gelöscht)",
            # None heisst: der Inhalt ist inzwischen weg (geloescht).
            "vorschau": vorschau,
            "ziel_sichtbar": bool(ziel) and ziel.get("status") == "active",
            # Zu welchem Beitrag gehoert das? Fuer den Sprung in die Ansicht.
            "post_id": m["target_id"] if m["target_type"] == "post"
                       else (ziel["post_id"] if ziel else None),
        })
    return ergebnis


@router.post("/admin/reports/{report_id}/handle")
def admin_handle_report(report_id: str, aktion: str = Form(...),
                        admin: dict = Depends(auth.get_admin_user)):
    """Entscheidung des Betreibers: Inhalt ausblenden oder Meldung ablegen.

    Die Entscheidung schliesst ALLE offenen Meldungen zu diesem Inhalt -
    haben drei Leute denselben Beitrag gemeldet, ist das eine Entscheidung
    und nicht drei.
    """
    if aktion not in ("ausblenden", "behalten"):
        raise HTTPException(422, "Aktion muss 'ausblenden' oder 'behalten' sein.")
    meldung = db.get_report(report_id)
    if not meldung:
        raise HTTPException(404, "Meldung nicht gefunden")

    if aktion == "ausblenden":
        if meldung["target_type"] == "post":
            if db.get_post(meldung["target_id"]):
                db.update_post(meldung["target_id"], status="hidden")
        elif db.get_comment(meldung["target_id"]):
            db.update_comment_status(meldung["target_id"], "hidden")

    neuer_status = "hidden" if aktion == "ausblenden" else "kept"
    db.close_reports_for_target(meldung["target_type"], meldung["target_id"],
                                neuer_status, admin["id"])
    return {"ok": True, "status": neuer_status}
