"""Waechter: Jede Route ist entweder geschuetzt oder BEWUSST offen.

Die wichtigste Sicherheitsfrage der Plattform in einem Test. Neue Routen
entstehen laufend; eine davon versehentlich ohne
`Depends(auth.get_current_user)` zu lassen, faellt sonst niemandem auf -
bis Fremde die Daten abrufen.

Bewusst zur LAUFZEIT geprueft, nicht am Quelltext: `/auth/me` holt den
Nutzer im Funktionskoerper statt per Depends, und genau solche Faelle
uebersieht eine Code-Analyse. Hier wird jede Route ohne Cookie wirklich
angefragt - 401/403 heisst geschuetzt.

Kommt eine neue offene Route dazu, schlaegt dieser Test fehl. Das ist der
Sinn: Offenheit muss eine Entscheidung sein, kein Versehen. Dann gehoert
sie mit einer Begruendung in die Liste unten.
"""
from __future__ import annotations

import pytest

from backend.main import app

# (Methode, Pfad) -> warum das ohne Anmeldung erreichbar sein MUSS.
BEWUSST_OFFEN = {
    ("GET", "/health"): "Hosting-Ueberwachung (Render prueft damit den Dienst)",
    ("GET", "/betreiber"): "Impressum muss ohne Konto erreichbar sein (§ 5 DDG)",
    ("GET", "/auth/config"): "sagt der Login-Maske, ob sie ein Code-Feld braucht",
    ("POST", "/auth/register"): "Registrierung",
    ("POST", "/auth/login"): "Anmeldung",
    ("POST", "/auth/logout"): "Abmelden soll auch mit abgelaufener Sitzung gehen",
    ("GET", "/styles"): "statischer Katalog, kein Geheimnis",
    ("GET", "/platforms"): "statischer Katalog",
    ("GET", "/presets"): "statischer Katalog",
    ("GET", "/post-categories"): "statischer Katalog (Filter im Feed)",
    ("GET", "/report-reasons"): "Auswahl im Melden-Dialog",
    # Die automatische API-Dokumentation. Sie laeuft NUR lokal - online ist
    # sie abgeschaltet (HOOKCUT_API_DOCS=0 in render.yaml und Dockerfile),
    # sonst bekaeme jeder Besucher eine Landkarte aller Routen samt der
    # Admin-Wege. Dass das Abschalten wirkt, prueft
    # test_tools_switch.py::test_api_dokumentation_laesst_sich_abschalten;
    # die Tests hier laufen im lokalen Standardmodus, deshalb offen.
    ("GET", "/docs"): "nur lokal - online per HOOKCUT_API_DOCS=0 abgeschaltet",
    ("GET", "/docs/oauth2-redirect"): "gehoert zu /docs, ebenfalls nur lokal",
    ("GET", "/redoc"): "nur lokal - online per HOOKCUT_API_DOCS=0 abgeschaltet",
    ("GET", "/openapi.json"): "nur lokal - online per HOOKCUT_API_DOCS=0 abgeschaltet",
}

# Adressen mit Platzhalter brauchen einen Beispielwert.
BEISPIELE = {
    "{post_id}": "x", "{comment_id}": "x", "{job_id}": "x", "{pack_id}": "x",
    "{project_id}": "x", "{take_id}": "x", "{item_id}": "x", "{report_id}": "x",
    "{handle}": "x", "{index}": "0", "{idx}": "0", "{code}": "x",
}


def _alle_routen(routen):
    """Auch die per include_router eingehaengten.

    ACHTUNG: app.routes enthaelt fuer eingehaengte Router KEINE einzelnen
    Routen, sondern ein Sammel-Objekt. Wer nur ueber app.routes laeuft,
    sieht /auth/... und das ganze Netzwerk NICHT - und haelt eine
    unvollstaendige Pruefung faelschlich fuer vollstaendig.
    """
    for r in routen:
        unter = getattr(r, "original_router", None)
        if unter is not None:
            yield from _alle_routen(unter.routes)
        else:
            yield r


def _pruefbare_routen():
    for route in _alle_routen(app.routes):
        pfad = getattr(route, "path", "")
        methoden = getattr(route, "methods", None)
        # Der Auffang-Pfad liefert nur die Oberflaeche aus, kein Datenweg.
        if not pfad or not methoden or pfad == "/{pfad:path}":
            continue
        echt = pfad
        for platzhalter, wert in BEISPIELE.items():
            echt = echt.replace(platzhalter, wert)
        if "{" in echt:  # unbekannter Platzhalter -> hier nicht pruefbar
            continue
        for methode in sorted(methoden - {"HEAD", "OPTIONS"}):
            yield methode, pfad, echt


ROUTEN = sorted(_pruefbare_routen())


def test_es_gibt_ueberhaupt_routen_zu_pruefen():
    """Sicherung gegen einen stillen Fehlschlag der Sammel-Logik: findet sie
    nichts mehr, waeren alle Pruefungen unten leer und trotzdem gruen."""
    assert len(ROUTEN) > 60, f"nur {len(ROUTEN)} Routen gefunden - Sammel-Logik kaputt?"
    pfade = {p for _, p, _ in ROUTEN}
    for muss in ("/auth/me", "/posts", "/feed", "/admin/reports"):
        assert muss in pfade, f"{muss} fehlt - eingehaengte Router werden nicht erfasst"


@pytest.mark.parametrize("methode,pfad,adresse", ROUTEN,
                         ids=[f"{m} {p}" for m, p, _ in ROUTEN])
def test_route_ist_geschuetzt_oder_bewusst_offen(client, methode, pfad, adresse):
    antwort = client.request(methode, adresse)
    geschuetzt = antwort.status_code in (401, 403)
    begruendung = BEWUSST_OFFEN.get((methode, pfad))

    if begruendung is None:
        assert geschuetzt, (
            f"{methode} {pfad} antwortet ohne Anmeldung mit {antwort.status_code}. "
            "Entweder fehlt Depends(auth.get_current_user) - oder die Route soll "
            "wirklich offen sein, dann gehoert sie mit Begruendung in BEWUSST_OFFEN.")
    else:
        assert not geschuetzt, (
            f"{methode} {pfad} steht als bewusst offen ({begruendung}), "
            f"antwortet aber mit {antwort.status_code}.")
