"""Tests fuer Interesse und Kommentare.

"Ich hab Interesse" ist die Kernhandlung des Netzwerks: jemand kann bei
einem offenen Projekt helfen. Wichtig ist, dass es KEINE Sackgasse ist -
der Autor muss sehen, wer helfen will, samt Profil (dort liegen die Links
zu Instagram & Co., ueber die der Kontakt dann laeuft).
"""
from __future__ import annotations

import sqlite3

from backend import db


def _handle(client) -> str:
    return client.get("/profiles/me").json()["handle"]


def _post(client, titel="Suche Refrain"):
    r = client.post("/posts", data={"title": titel, "categories": "refrain"})
    assert r.status_code == 200, r.text
    return r.json()


def test_interest_flow(auth_client, second_auth_client):
    post = _post(auth_client)

    r = second_auth_client.post(f"/posts/{post['id']}/interest")
    assert r.status_code == 200 and r.json()["interested"] is True

    # Der Autor sieht, WER helfen will - das ist der Kontaktweg.
    sicht = auth_client.get(f"/posts/{post['id']}/interest").json()
    assert sicht["people"][0]["handle"] == _handle(second_auth_client)
    assert "email" not in sicht["people"][0]

    # Aus Sicht des Interessenten ist der Zustand gemerkt.
    assert second_auth_client.get(f"/posts/{post['id']}/interest").json()["interested"] is True

    r2 = second_auth_client.delete(f"/posts/{post['id']}/interest")
    assert r2.json()["interested"] is False
    assert auth_client.get(f"/posts/{post['id']}/interest").json()["people"] == []


def test_interest_list_is_only_for_the_author(auth_client, second_auth_client):
    """Die Namensliste ist der Kontaktweg des Autors - nicht fuer alle.

    Die Oberflaeche zeigt sie ohnehin nur ihm; die Schnittstelle darf nicht
    mehr herausgeben als die Ansicht, sonst sieht jeder mit direktem Zugriff
    mehr als vorgesehen.
    """
    post = _post(auth_client)
    second_auth_client.post(f"/posts/{post['id']}/interest")

    fremd = second_auth_client.get(f"/posts/{post['id']}/interest").json()
    assert fremd["interested"] is True   # eigener Zustand: ja
    assert fremd["count"] == 1           # Anzahl: ja
    assert fremd["people"] == []         # Namen: nein

    autor = auth_client.get(f"/posts/{post['id']}/interest").json()
    assert len(autor["people"]) == 1


def test_interest_twice_is_harmless(auth_client, second_auth_client):
    post = _post(auth_client)
    second_auth_client.post(f"/posts/{post['id']}/interest")
    second_auth_client.post(f"/posts/{post['id']}/interest")
    assert len(auth_client.get(f"/posts/{post['id']}/interest").json()["people"]) == 1


def test_no_interest_in_own_post(auth_client):
    post = _post(auth_client)
    assert auth_client.post(f"/posts/{post['id']}/interest").status_code == 422


def test_comments(auth_client, second_auth_client):
    post = _post(auth_client)
    r = second_auth_client.post(f"/posts/{post['id']}/comments",
                                data={"body": "Ich hab da was im Kopf."})
    assert r.status_code == 200
    assert r.json()["body"] == "Ich hab da was im Kopf."
    assert r.json()["author"]["handle"] == _handle(second_auth_client)

    liste = auth_client.get(f"/posts/{post['id']}/comments").json()
    assert [k["body"] for k in liste] == ["Ich hab da was im Kopf."]


def test_empty_comment_rejected(auth_client):
    post = _post(auth_client)
    assert auth_client.post(f"/posts/{post['id']}/comments",
                            data={"body": "   "}).status_code == 422


def test_long_comment_is_capped(auth_client):
    post = _post(auth_client)
    r = auth_client.post(f"/posts/{post['id']}/comments", data={"body": "x" * 5000})
    assert len(r.json()["body"]) == 1000


def test_comment_author_can_delete(auth_client, second_auth_client):
    post = _post(auth_client)
    kid = second_auth_client.post(f"/posts/{post['id']}/comments",
                                  data={"body": "weg damit"}).json()["id"]
    assert second_auth_client.delete(f"/comments/{kid}").status_code == 200


def test_post_owner_can_delete_foreign_comment(auth_client, second_auth_client):
    """Hausrecht: im eigenen Projekt aufraeumen duerfen."""
    post = _post(auth_client)
    kid = second_auth_client.post(f"/posts/{post['id']}/comments",
                                  data={"body": "spam"}).json()["id"]
    assert auth_client.delete(f"/comments/{kid}").status_code == 200
    assert auth_client.get(f"/posts/{post['id']}/comments").json() == []


def test_unrelated_user_cannot_delete_comment(auth_client, second_auth_client):
    """Weder Verfasser noch Beitrags-Eigentuemer -> 403."""
    post = _post(auth_client)
    kid = auth_client.post(f"/posts/{post['id']}/comments",
                           data={"body": "meins"}).json()["id"]
    assert second_auth_client.delete(f"/comments/{kid}").status_code == 403


def test_counts_in_feed(auth_client, second_auth_client):
    post = _post(auth_client, "Mit Zaehlern")
    second_auth_client.post(f"/posts/{post['id']}/interest")
    second_auth_client.post(f"/posts/{post['id']}/comments", data={"body": "hi"})

    eintrag = next(b for b in auth_client.get("/feed/discover").json()
                   if b["id"] == post["id"])
    assert eintrag["interest_count"] == 1
    assert eintrag["comment_count"] == 1


def test_interactions_on_hidden_post_are_404(auth_client, second_auth_client):
    post = _post(auth_client)
    db.update_post(post["id"], status="hidden")
    assert second_auth_client.post(f"/posts/{post['id']}/interest").status_code == 404
    assert second_auth_client.get(f"/posts/{post['id']}/comments").status_code == 404


def test_interest_of_profileless_account_is_visible(auth_client, second_auth_client):
    """Regression: ein Konto OHNE Profil darf nicht lautlos verschwinden.

    Die Interessenten-Liste verbindet hart mit profiles. Fehlte das Profil,
    war das Interesse zwar gespeichert, aber fuer den Autor unsichtbar - ohne
    Fehlermeldung. Seit get_current_user ein Profil garantiert, kann das nicht
    mehr passieren; hier wird der Zustand kuenstlich hergestellt.
    """
    post = _post(auth_client)
    fremder = second_auth_client.user["id"]

    # Profil direkt aus der DB entfernen - simuliert ein Konto aus der Zeit
    # vor den Profilen. Bewusst ohne db-Helfer: Profile zu loeschen ist
    # nirgends im Produktivcode vorgesehen.
    with sqlite3.connect(str(db.DEFAULT_DB_PATH)) as conn:
        conn.execute("DELETE FROM profiles WHERE user_id = ?", (fremder,))
    assert db.get_profile(fremder) is None

    # Der naechste angemeldete Aufruf zieht das Profil nach ...
    r = second_auth_client.post(f"/posts/{post['id']}/interest")
    assert r.status_code == 200
    # ... und der Autor sieht die Person.
    leute = auth_client.get(f"/posts/{post['id']}/interest").json()["people"]
    assert fremder in {p["user_id"] for p in leute}


def test_interactions_require_login(client):
    assert client.post("/posts/x/interest").status_code == 401
    assert client.get("/posts/x/comments").status_code == 401
