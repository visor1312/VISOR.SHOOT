"""Tests fuer die Betreiberangaben (Impressum, Datenschutz, AGB).

Der Endpunkt ist bewusst OHNE Anmeldung erreichbar: ein Impressum hinter
einer Anmeldemaske waere keins (§ 5 DDG verlangt, dass es von jeder Seite
aus in hoechstens zwei Klicks erreichbar ist).
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from backend import betreiber

PROJEKT = Path(__file__).resolve().parent.parent


def test_betreiber_ohne_anmeldung_erreichbar(client):
    r = client.get("/betreiber")
    assert r.status_code == 200
    daten = r.json()
    # Die Pflichtangaben duerfen nie leer sein - eine leere Anschrift im
    # Impressum ist schlimmer als gar keine Seite.
    for feld in ("name", "strasse", "plz", "ort", "land", "email"):
        assert daten[feld].strip(), f"{feld} ist leer"
    assert "@" in daten["email"]


def test_betreiber_verraet_keine_geheimnisse(client):
    """Der Endpunkt ist oeffentlich - es darf nur drinstehen, was ohnehin
    auf der Seite steht (kein Passwort-Hash, keine Zugangsdaten)."""
    daten = client.get("/betreiber").json()
    erlaubt = {"name", "strasse", "plz", "ort", "land", "email", "telefon",
               "plattform_name", "hoster_name", "hoster_ort", "hoster_region"}
    assert set(daten) == erlaubt


def test_telefon_darf_fehlen():
    """Eine Telefonnummer ist nicht zwingend (EuGH C-298/07), solange die
    E-Mail-Adresse da ist. Leer heisst: wird gar nicht erst angezeigt."""
    assert "telefon" in betreiber.als_dict()


def test_angaben_per_umgebungsvariable_austauschbar(tmp_path):
    """Ein Umzug oder der Wechsel auf eine Geschaeftsadresse darf KEINEN
    neuen Programmstand brauchen - sonst haengt die Adressaenderung an mir.
    Die Werte werden beim Import gelesen, deshalb ein eigener Prozess."""
    umgebung = {**os.environ,
                "PYTHONPATH": str(PROJEKT),
                "HOOKCUT_DB": str(tmp_path / "state.db"),
                "HOOKCUT_BETREIBER_NAME": "Musterfirma GmbH",
                "HOOKCUT_BETREIBER_STRASSE": "Musterweg 1",
                "HOOKCUT_BETREIBER_PLZ": "12345",
                "HOOKCUT_BETREIBER_ORT": "Musterstadt",
                "HOOKCUT_BETREIBER_EMAIL": "kontakt@example.com",
                "HOOKCUT_BETREIBER_TELEFON": "+49 123 456789"}
    ergebnis = subprocess.run(
        [sys.executable, "-c",
         "from backend import betreiber\n"
         "d = betreiber.als_dict()\n"
         "print(d['name'], '|', d['strasse'], '|', d['plz'], d['ort'], "
         "'|', d['email'], '|', d['telefon'])\n"],
        cwd=PROJEKT, env=umgebung, capture_output=True, text=True)
    assert ergebnis.returncode == 0, ergebnis.stderr
    assert ergebnis.stdout.strip() == (
        "Musterfirma GmbH | Musterweg 1 | 12345 Musterstadt "
        "| kontakt@example.com | +49 123 456789")
