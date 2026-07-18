"""API-Tests fuer den All-in-One-Editier-Flow (Sync -> Hook -> Style-Render).

Der Erfolgspfad (echte Dateien) wurde manuell verifiziert (Sync 5039ms,
Hook 25.8-44.5s). Der Render-Schritt ruft node/Chrome und laeuft nur beim
Nutzer. Hier: Styles-Katalog, 404-Faelle, Fehlerpfad.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.main import app


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


def test_styles_catalog(client):
    styles = client.get("/styles").json()["styles"]
    keys = {s["key"] for s in styles}
    assert {"clean", "vibrant", "cinematic", "warm"} <= keys
    for s in styles:
        assert s["name"] and s["description"]


def test_edit_unknown_job_404(client):
    assert client.get("/edit/nope").status_code == 404
    assert client.post("/edit/nope/hook").status_code == 404


def test_edit_analyze_bad_files_errors(client):
    r = client.post("/edit/analyze",
                    files={"video": ("v.mp4", b"junk", "video/mp4"),
                           "song": ("s.wav", b"junk", "audio/wav")},
                    data={"with_subtitles": "false"})
    assert r.status_code == 200
    jid = r.json()["job_id"]
    body = client.get(f"/edit/{jid}").json()
    assert body["status"] == "error" and body["error"]
