"""API-Tests fuer den All-in-One-Editier-Flow (Sync -> Hook -> Style-Render).

Der Erfolgspfad (echte Dateien) wurde manuell verifiziert (Sync 5039ms,
Hook 25.8-44.5s). Der Render-Schritt ruft node/Chrome und laeuft nur beim
Nutzer. Hier: Styles-Katalog, 404-Faelle, Fehlerpfad.

client/auth_client kommen aus tests/conftest.py (Benutzer-System);
/styles und /platforms sind bewusst oeffentlich (statische Kataloge).
"""
from __future__ import annotations


def test_styles_catalog(client):
    styles = client.get("/styles").json()["styles"]
    keys = {s["key"] for s in styles}
    assert {"clean", "vibrant", "cinematic", "warm"} <= keys
    for s in styles:
        assert s["name"] and s["description"]


def test_platforms_catalog(client):
    platforms = client.get("/platforms").json()["platforms"]
    keys = {p["key"] for p in platforms}
    assert {"reel", "feed", "square", "wide"} <= keys
    for p in platforms:
        assert p["name"] and p["width"] > 0 and p["height"] > 0


def test_edit_requires_login(client):
    assert client.get("/edit").status_code == 401
    assert client.get("/edit/nope").status_code == 401
    assert client.get("/edit/nope/download").status_code == 401


def test_edit_unknown_job_404(auth_client):
    assert auth_client.get("/edit/nope").status_code == 404
    assert auth_client.post("/edit/nope/hook").status_code == 404
    assert auth_client.get("/edit/nope/download").status_code == 404
    assert auth_client.get("/edit/nope/download", params={"platform": "reel"}).status_code == 404


def test_edit_outputs_listing_and_partial_download(auth_client):
    """Multi-Plattform: outputs[] zeigt pro Format ready-Status; ein noch
    nicht gerendertes Format liefert beim Download 404."""
    import json

    from backend import db

    jid = db.create_edit_job(video_path="", song_path="", with_subtitles=False,
                             user_id=auth_client.user["id"])
    db.update_edit_job(jid, platforms="reel,square",
                       outputs_json=json.dumps({"reel": "/tmp/reel.mp4"}))
    body = auth_client.get(f"/edit/{jid}").json()
    outs = body["outputs"]
    assert [o["platform"] for o in outs] == ["reel", "square"]
    assert outs[0]["ready"] is True and outs[1]["ready"] is False
    assert outs[1]["width"] == 1080 and outs[1]["height"] == 1080
    assert auth_client.get(f"/edit/{jid}/download",
                           params={"platform": "square"}).status_code == 404

    # Der Job taucht in der eigenen "Meine Reels"-Liste auf.
    listed = auth_client.get("/edit").json()
    assert any(j["job_id"] == jid for j in listed)


def test_edit_analyze_bad_files_errors(auth_client):
    r = auth_client.post("/edit/analyze",
                         files={"video": ("v.mp4", b"junk", "video/mp4"),
                                "song": ("s.wav", b"junk", "audio/wav")},
                         data={"with_subtitles": "false"})
    assert r.status_code == 200
    jid = r.json()["job_id"]
    body = auth_client.get(f"/edit/{jid}").json()
    assert body["status"] == "error" and body["error"]
