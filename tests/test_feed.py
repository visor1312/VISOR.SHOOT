"""Tests fuer den Feed.

Zwei Ansichten: "Entdecken" (alle offenen Projekte, die Startansicht) und
"Folge ich". Der Kaltstart-Fall ist der wichtigste: wer neu ist, folgt
niemandem - Entdecken muss trotzdem etwas zeigen, sonst ist das Netzwerk
fuer Neulinge leer und sie kommen nicht wieder.
"""
from __future__ import annotations

from backend import db


def _handle(client) -> str:
    return client.get("/profiles/me").json()["handle"]


def _post(client, titel, kategorien="refrain", **extra):
    r = client.post("/posts", data={"title": titel, "categories": kategorien, **extra})
    assert r.status_code == 200, r.text
    return r.json()


def _titel(antwort) -> list[str]:
    return [b["title"] for b in antwort.json()]


def test_discover_shows_strangers_without_following(auth_client, second_auth_client):
    """Der Kaltstart-Fall - der Grund, warum Entdecken die Startansicht ist."""
    _post(auth_client, "Suche Refrain")
    treffer = second_auth_client.get("/feed/discover")
    assert treffer.status_code == 200
    assert "Suche Refrain" in _titel(treffer)


def test_following_feed_is_empty_without_follows(auth_client, second_auth_client):
    _post(auth_client, "Nur fuer Folger")
    assert _titel(second_auth_client.get("/feed")) == []


def test_following_feed_after_follow(auth_client, second_auth_client):
    _post(auth_client, "Jetzt sichtbar")
    second_auth_client.post(f"/profiles/{_handle(auth_client)}/follow")
    assert "Jetzt sichtbar" in _titel(second_auth_client.get("/feed"))


def test_own_posts_appear_in_own_feed(auth_client):
    """Eigene Beitraege gehoeren in den eigenen Feed - man folgt sich nicht selbst."""
    _post(auth_client, "Mein eigener")
    assert "Mein eigener" in _titel(auth_client.get("/feed"))


def test_feed_carries_author_profile(auth_client, second_auth_client):
    _post(auth_client, "Mit Autor")
    eintrag = next(b for b in second_auth_client.get("/feed/discover").json()
                   if b["title"] == "Mit Autor")
    # Ohne mitgelieferten Autor muesste die Oberflaeche pro Beitrag nachladen.
    assert eintrag["author"]["handle"] == _handle(auth_client)
    assert "email" not in eintrag["author"]


def test_category_filter(auth_client, second_auth_client):
    _post(auth_client, "Brauche Beat", kategorien="beat")
    _post(auth_client, "Brauche Hook", kategorien="refrain")

    nur_beat = _titel(second_auth_client.get("/feed/discover?categories=beat"))
    assert "Brauche Beat" in nur_beat and "Brauche Hook" not in nur_beat

    # Mehrere Kategorien = ODER.
    beides = _titel(second_auth_client.get("/feed/discover?categories=beat,refrain"))
    assert "Brauche Beat" in beides and "Brauche Hook" in beides


def test_unknown_category_is_ignored_not_fatal(auth_client):
    """Ein Tippfehler in der URL darf nicht die ganze Seite scheitern lassen."""
    _post(auth_client, "Da")
    r = auth_client.get("/feed/discover?categories=quatsch")
    assert r.status_code == 200
    assert "Da" in _titel(r)


def test_genre_filter_matches_partially(auth_client):
    """'rap' soll auch 'Deutschrap' finden - hier ist Teiltreffer gewollt."""
    _post(auth_client, "Deutschrap-Projekt", genres="Deutschrap")
    _post(auth_client, "Techno-Projekt", genres="Techno")
    treffer = _titel(auth_client.get("/feed/discover?genre=rap"))
    assert "Deutschrap-Projekt" in treffer and "Techno-Projekt" not in treffer


def test_closed_projects_are_hidden_by_default(auth_client):
    """Erledigte Anfragen sollen niemanden mehr beschaeftigen."""
    post = _post(auth_client, "Schon erledigt")
    auth_client.patch(f"/posts/{post['id']}", data={"open_state": "closed"})

    assert "Schon erledigt" not in _titel(auth_client.get("/feed/discover"))
    # Auf Wunsch trotzdem sichtbar.
    assert "Schon erledigt" in _titel(auth_client.get("/feed/discover?open_only=false"))


def test_hidden_posts_never_appear(auth_client, second_auth_client):
    post = _post(auth_client, "Ausgeblendet")
    db.update_post(post["id"], status="hidden")
    assert "Ausgeblendet" not in _titel(second_auth_client.get("/feed/discover"))
    assert "Ausgeblendet" not in _titel(second_auth_client.get("/feed/discover?open_only=false"))


def test_paging_has_no_duplicates(auth_client):
    for i in range(5):
        _post(auth_client, f"Seite {i}")

    erste = auth_client.get("/feed/discover?limit=2").json()
    assert len(erste) == 2
    zweite = auth_client.get(f"/feed/discover?limit=2&before={erste[-1]['created_at']}").json()
    ids_erste = {b["id"] for b in erste}
    assert ids_erste.isdisjoint({b["id"] for b in zweite})


def test_newest_first(auth_client):
    _post(auth_client, "Alt")
    _post(auth_client, "Neu")
    titel = _titel(auth_client.get("/feed/discover"))
    assert titel.index("Neu") < titel.index("Alt")


def test_posts_by_profile(auth_client, second_auth_client):
    offen = _post(auth_client, "Offen")
    erledigt = _post(auth_client, "Erledigt")
    auth_client.patch(f"/posts/{erledigt['id']}", data={"open_state": "closed"})

    r = second_auth_client.get(f"/profiles/{_handle(auth_client)}/posts")
    assert r.status_code == 200
    titel = [b["title"] for b in r.json()]
    # Auf dem Profil zeigen wir auch Erledigtes - man sieht, woran jemand arbeitet.
    assert "Offen" in titel and "Erledigt" in titel
    assert offen["id"] in {b["id"] for b in r.json()}


def test_feed_requires_login(client):
    assert client.get("/feed").status_code == 401
    assert client.get("/feed/discover").status_code == 401
