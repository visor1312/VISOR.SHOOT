"""API-Tests fuer den Editor-Analyse-Endpoint (Etappe 3).

Der Erfolgs-Pfad (echtes Video + echter Song -> offset/hook-Zahlen) ist
rechenintensiv und wurde manuell mit echten Nutzer-Dateien verifiziert
(offset ~5039ms, conf 0.88, Hook 25.8-45.0s). Hier testen wir die
API-Mechanik: Job-Anlage, Status-Flow, Fehlerfall, 404.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.main import app


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


def test_analyze_unknown_job_returns_404(client):
    r = client.get("/editor/analyze/gibt-es-nicht")
    assert r.status_code == 404


def test_analyze_with_invalid_files_ends_in_error_status(client):
    # Muellbytes statt Video/Song: der Job muss sauber im Fehlerstatus landen
    # (kein Crash, kein Haengenbleiben) und den Fehler transportieren.
    r = client.post("/editor/analyze", files={
        "video": ("video.mp4", b"kein echtes video", "video/mp4"),
        "song": ("song.wav", b"kein echtes audio", "audio/wav"),
    })
    assert r.status_code == 200
    job_id = r.json()["job_id"]
    assert r.json()["status"] == "analyzing"

    # TestClient fuehrt BackgroundTasks synchron nach der Response aus.
    r = client.get(f"/editor/analyze/{job_id}")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "error"
    assert body["error"]
    assert body["result"] is None
