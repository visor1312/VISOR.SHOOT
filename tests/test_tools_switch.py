"""Tests fuer den Werkzeug-Schalter (HOOKCUT_TOOLS_ENABLED).

Auf dem gehosteten Server gibt es kein Chrome mit WebGPU, kein ffmpeg-Modell
und keine mehrere GB grossen Whisper-Dateien. Ohne diesen Schalter wuerden die
Render-Routen dort einen Hintergrund-Job starten, der still scheitert - und der
neugierige Musiker klickt als Erstes genau darauf. Geprueft wird deshalb:
alles, was schwere Arbeit startet, antwortet abgeschaltet mit 503; alles, was
nur liest, funktioniert weiter; und das NETZWERK bleibt vollstaendig nutzbar.
"""
from __future__ import annotations

import pytest

from backend import main


@pytest.fixture()
def werkzeug_aus(monkeypatch):
    monkeypatch.setattr(main.config, "TOOLS_ENABLED", False)


def test_config_meldet_den_zustand(client, monkeypatch):
    monkeypatch.setattr(main.config, "TOOLS_ENABLED", False)
    assert client.get("/auth/config").json()["tools_enabled"] is False
    monkeypatch.setattr(main.config, "TOOLS_ENABLED", True)
    assert client.get("/auth/config").json()["tools_enabled"] is True


def test_schwere_routen_geben_503(auth_client, werkzeug_aus):
    """Jede Route, die einen Render- oder Analyse-Job startet."""
    faelle = [
        ("post", "/projects", {"data": {"name": "X"}, "files": {"song": ("s.wav", b"x")}}),
        ("post", "/projects/egal/takes", {"files": {"video": ("v.mp4", b"x")}}),
        ("post", "/projects/egal/takes/egal/sync", {}),
        ("post", "/hooks/analyze", {"files": {"song": ("s.wav", b"x")}}),
        ("post", "/editor/analyze", {"files": {"video": ("v.mp4", b"x"), "song": ("s.wav", b"x")}}),
        ("post", "/edit/analyze", {"files": {"video": ("v.mp4", b"x"), "song": ("s.wav", b"x")}}),
        ("post", "/edit/egal/hook", {}),
        ("post", "/edit/egal/render", {"data": {"style": "clean"}}),
        ("post", "/packs", {"files": {"video": ("v.mp4", b"x"), "song": ("s.wav", b"x")}}),
        ("post", "/canvas", {"files": {"video": ("v.mp4", b"x"), "song": ("s.wav", b"x")}}),
    ]
    for methode, pfad, kwargs in faelle:
        antwort = getattr(auth_client, methode)(pfad, **kwargs)
        assert antwort.status_code == 503, f"{pfad} gab {antwort.status_code}"
        # Die Meldung muss erklaeren, nicht nur scheitern.
        assert "Rechner" in antwort.json()["detail"]


def test_lesende_routen_funktionieren_weiter(auth_client, werkzeug_aus):
    """Listen duerfen nicht mitgesperrt werden - sonst bricht das Dashboard,
    falls jemand die Seite doch aufruft."""
    for pfad in ("/projects", "/edit", "/hooks", "/packs", "/canvas"):
        assert auth_client.get(pfad).status_code == 200, pfad


def test_netzwerk_bleibt_voll_nutzbar(auth_client, werkzeug_aus):
    """Der eigentliche Zweck: online laeuft das Netzwerk, nur die Werkzeuge
    fehlen."""
    r = auth_client.post("/posts", data={"title": "Geht auch ohne Werkzeuge",
                                         "categories": "refrain"})
    assert r.status_code == 200
    assert auth_client.get("/feed/discover").status_code == 200
    assert auth_client.get("/profiles/me").status_code == 200


def test_eingeschaltet_bleibt_alles_beim_alten(auth_client, monkeypatch):
    """Lokal (Standard) darf der Schalter nichts blockieren."""
    monkeypatch.setattr(main.config, "TOOLS_ENABLED", True)
    # Ohne gueltige Datei scheitert die Route fachlich - aber NICHT mit 503.
    antwort = auth_client.post("/edit/gibtesnicht/hook")
    assert antwort.status_code != 503


def test_api_dokumentation_laesst_sich_abschalten(tmp_path):
    """Online muss /docs weg sein.

    Die automatische Dokumentation listet sonst jedem Besucher saemtliche
    Routen samt Parametern auf - auch die Admin-Routen. Der Schalter wird
    beim Bau der Anwendung gelesen, deshalb ein eigener Prozess.
    """
    import os
    import subprocess
    import sys
    from pathlib import Path

    projekt = Path(__file__).resolve().parent.parent
    # Auf den STATUS zu schauen reicht hier NICHT: ist die Oberflaeche
    # gebaut, faengt der Auffang-Pfad jede unbekannte Adresse ab und liefert
    # brav 200 mit der HTML-Seite. Entscheidend ist der INHALT - kommt noch
    # das Schema mit allen Routen zurueck?
    skript = (
        "from fastapi.testclient import TestClient\n"
        "from backend.main import app\n"
        "with TestClient(app) as c:\n"
        "    for pfad in ('/docs', '/redoc', '/openapi.json'):\n"
        "        text = c.get(pfad).text.lower()\n"
        "        schema = '\"paths\"' in text or 'swagger-ui' in text or 'redoc.standalone' in text\n"
        "        print(pfad, schema)\n"
    )

    def lauf(docs: str) -> dict[str, bool]:
        e = subprocess.run(
            [sys.executable, "-c", skript], cwd=projekt, capture_output=True, text=True,
            env={**os.environ, "PYTHONPATH": str(projekt),
                 "HOOKCUT_DB": str(tmp_path / f"docs-{docs}.db"),
                 "HOOKCUT_API_DOCS": docs})
        assert e.returncode == 0, e.stderr
        return {z.split()[0]: z.split()[1] == "True" for z in e.stdout.strip().splitlines()}

    an = lauf("1")
    assert all(an.values()), f"lokal soll die Doku erreichbar sein: {an}"

    aus = lauf("0")
    verraeterisch = sorted(p for p, schema in aus.items() if schema)
    assert not verraeterisch, f"gibt online weiter die Routen preis: {verraeterisch}"
