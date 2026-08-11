"""Tests fuer offene Projekte (Beitraege) - der Kern des Netzwerks.

Hier gilt eine ANDERE Sichtbarkeits-Regel als beim Rest des Projekts: lesen
darf jedes angemeldete Mitglied, aendern/loeschen nur der Autor (403 statt
404, weil die Existenz im Feed ohnehin oeffentlich ist). Genau das wird
unten geprueft - zusammen mit den Upload-Grenzen, ohne die ein Fremder die
Platte volllaufen lassen koennte.
"""
from __future__ import annotations

import math
import struct
import wave

from backend import db, network, storage


def _wav_bytes(sekunden: float, rate: int = 8000) -> bytes:
    """Echte, kurze WAV-Datei im Speicher (ffprobe muss sie lesen koennen)."""
    from io import BytesIO
    puffer = BytesIO()
    with wave.open(puffer, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        for i in range(int(sekunden * rate)):
            wert = int(3000 * math.sin(2 * math.pi * 440 * i / rate))
            w.writeframes(struct.pack("<h", wert))
    return puffer.getvalue()


def _post(client, titel="Suche Refrain", kategorien="refrain", **extra):
    daten = {"title": titel, "categories": kategorien, **extra}
    return client.post("/posts", data=daten)


def test_create_and_read_post(auth_client):
    r = _post(auth_client, body="90 BPM, Deutschrap", genres="Deutschrap, Trap", bpm=90)
    assert r.status_code == 200, r.text
    post = r.json()
    assert post["title"] == "Suche Refrain"
    assert post["categories"] == ["refrain"]
    assert post["genres"] == ["Deutschrap", "Trap"]
    assert post["bpm"] == 90
    assert post["open_state"] == "open"
    assert post["has_audio"] is False

    gelesen = auth_client.get(f"/posts/{post['id']}")
    assert gelesen.status_code == 200
    # Der Feed braucht den Autor mitgeliefert, sonst eine Extra-Abfrage pro Beitrag.
    assert gelesen.json()["author"]["handle"]


def test_post_with_audio(auth_client):
    r = auth_client.post("/posts", data={"title": "Mit Probe", "categories": "beat"},
                         files={"audio": ("probe.wav", _wav_bytes(2.0), "audio/wav")})
    assert r.status_code == 200, r.text
    post = r.json()
    assert post["has_audio"] is True
    assert 1.5 < post["audio_duration_sec"] < 2.5
    assert auth_client.get(f"/posts/{post['id']}/audio").status_code == 200


def test_audio_too_long_is_rejected_and_leaves_nothing(auth_client):
    """Zu lange Hoerprobe -> 422, und weder Beitrag noch Datei bleiben liegen."""
    vorher = db.count_recent_posts(auth_client.user["id"], "2000-01-01T00:00:00+00:00")
    r = auth_client.post("/posts", data={"title": "Zu lang", "categories": "beat"},
                         files={"audio": ("lang.wav", _wav_bytes(35.0), "audio/wav")})
    assert r.status_code == 422
    assert db.count_recent_posts(auth_client.user["id"], "2000-01-01T00:00:00+00:00") == vorher


def test_audio_too_large_is_rejected(auth_client):
    """Ueber der Groessengrenze -> 413. Wichtig: der Upload wird ABGEBROCHEN,
    nicht erst komplett geschrieben und dann geprueft."""
    zu_gross = b"\x00" * (network.POST_AUDIO_MAX_BYTES + 1024)
    r = auth_client.post("/posts", data={"title": "Zu gross", "categories": "beat"},
                         files={"audio": ("gross.wav", zu_gross, "audio/wav")})
    assert r.status_code == 413


def test_garbage_file_is_422_not_500(auth_client):
    """Eine als .wav getarnte Textdatei ist Nutzereingabe, kein Serverfehler."""
    r = auth_client.post("/posts", data={"title": "Kein Audio", "categories": "beat"},
                         files={"audio": ("fake.wav", b"das ist kein audio", "audio/wav")})
    assert r.status_code == 422


def test_wrong_extension_is_rejected(auth_client):
    r = auth_client.post("/posts", data={"title": "Falsch", "categories": "beat"},
                         files={"audio": ("schad.exe", b"MZ\x00\x00", "application/octet-stream")})
    assert r.status_code == 415


def test_invalid_category_rejected(auth_client):
    assert _post(auth_client, kategorien="gibtesnicht").status_code == 422
    assert _post(auth_client, kategorien="").status_code == 422


def test_bpm_range(auth_client):
    assert _post(auth_client, bpm=10).status_code == 422
    assert _post(auth_client, bpm=999).status_code == 422
    assert _post(auth_client, bpm=0).json()["bpm"] is None  # 0 = keine Angabe


def test_title_required(auth_client):
    assert _post(auth_client, titel="   ").status_code == 422


def test_long_text_is_capped(auth_client):
    r = _post(auth_client, titel="T" * 300, body="B" * 5000)
    assert len(r.json()["title"]) == network.POST_TITLE_MAX
    assert len(r.json()["body"]) == network.POST_BODY_MAX


def test_close_and_reopen_project(auth_client):
    """Wenn sich jemand gefunden hat, muss der Beitrag zugemacht werden
    koennen - sonst antworten Leute auf laengst erledigte Anfragen."""
    post_id = _post(auth_client).json()["id"]
    r = auth_client.patch(f"/posts/{post_id}", data={"open_state": "closed"})
    assert r.status_code == 200 and r.json()["open_state"] == "closed"
    assert auth_client.patch(f"/posts/{post_id}", data={"open_state": "quatsch"}).status_code == 422


def test_foreign_post_readable_but_not_editable(auth_client, second_auth_client):
    """Der Kern der neuen Sichtbarkeits-Regel."""
    post_id = _post(auth_client).json()["id"]

    # B darf lesen - das ist der Sinn eines Feeds.
    assert second_auth_client.get(f"/posts/{post_id}").status_code == 200
    # Aber nicht aendern oder loeschen. 403, nicht 404: der Beitrag existiert
    # sichtbar, ein "gibt es nicht" waere gelogen.
    assert second_auth_client.patch(f"/posts/{post_id}", data={"title": "gekapert"}).status_code == 403
    assert second_auth_client.delete(f"/posts/{post_id}").status_code == 403
    assert auth_client.get(f"/posts/{post_id}").json()["title"] == "Suche Refrain"


def test_delete_removes_audio_file(auth_client):
    r = auth_client.post("/posts", data={"title": "Weg damit", "categories": "beat"},
                         files={"audio": ("probe.wav", _wav_bytes(1.0), "audio/wav")})
    post_id = r.json()["id"]
    ordner = storage.post_dir(post_id)
    assert ordner.exists()

    assert auth_client.delete(f"/posts/{post_id}").status_code == 200
    assert auth_client.get(f"/posts/{post_id}").status_code == 404
    # Die Datei muss mit - sonst bleibt sie fuer immer auf der Platte.
    assert not ordner.exists()


def test_hidden_post_is_invisible(auth_client, second_auth_client):
    """Ausgeblendetes existiert fuer Mitglieder nicht - auch die Hoerprobe nicht."""
    r = auth_client.post("/posts", data={"title": "Wird versteckt", "categories": "beat"},
                         files={"audio": ("probe.wav", _wav_bytes(1.0), "audio/wav")})
    post_id = r.json()["id"]
    db.update_post(post_id, status="hidden")

    assert second_auth_client.get(f"/posts/{post_id}").status_code == 404
    assert second_auth_client.get(f"/posts/{post_id}/audio").status_code == 404
    # Auch der Autor selbst sieht ihn nicht mehr.
    assert auth_client.get(f"/posts/{post_id}").status_code == 404


def test_only_admin_can_hide(auth_client, second_auth_client):
    post_id = _post(auth_client).json()["id"]
    # second_auth_client ist kein Admin (der erste registrierte User war es).
    assert second_auth_client.post(f"/admin/posts/{post_id}/hide").status_code == 403


def test_spam_brake(auth_client, monkeypatch):
    monkeypatch.setattr(network, "POST_MAX_PER_HOUR", 3)
    for _ in range(3):
        assert _post(auth_client).status_code == 200
    assert _post(auth_client).status_code == 429


def test_posts_require_login(client):
    assert client.get("/posts/irgendwas").status_code == 401
    assert client.post("/posts", data={"title": "X", "categories": "beat"}).status_code == 401


def test_category_catalog_is_public(client):
    r = client.get("/post-categories")
    assert r.status_code == 200
    assert {c["key"] for c in r.json()} == set(network.POST_CATEGORIES)
