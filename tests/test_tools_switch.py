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
