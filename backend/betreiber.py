"""Betreiberdaten fuer Impressum, Datenschutz und AGB - AN EINER STELLE.

Wer diese Angaben aendern will (Umzug, spaeter eine Geschaeftsadresse statt
der Privatadresse), aendert NUR diese Datei - oder setzt beim Hosting die
passenden Umgebungsvariablen, dann braucht es nicht einmal einen neuen
Programmstand:

    HOOKCUT_BETREIBER_NAME, HOOKCUT_BETREIBER_STRASSE,
    HOOKCUT_BETREIBER_PLZ, HOOKCUT_BETREIBER_ORT,
    HOOKCUT_BETREIBER_EMAIL, HOOKCUT_BETREIBER_TELEFON

Rechtlicher Hintergrund (§ 5 DDG, seit 2024 anstelle des TMG): noetig sind
Name, ladungsfaehige Anschrift (ein Postfach genuegt NICHT) und Angaben fuer
eine schnelle elektronische Kontaktaufnahme - die E-Mail-Adresse gehoert
zwingend dazu. Eine Telefonnummer ist nach der Rechtsprechung des EuGH
(C-298/07) nicht zwingend, solange ein anderer schneller Weg besteht;
deshalb ist sie hier optional und bleibt leer, wenn nichts gesetzt ist.

ACHTUNG: Diese Angaben sind auf der Webseite oeffentlich sichtbar - das ist
der Zweck eines Impressums. Bei einer Privatadresse heisst das: die
Wohnanschrift ist oeffentlich. Bewusst so entschieden; austauschbar, sobald
es eine Geschaeftsadresse gibt.
"""
from __future__ import annotations

import os

NAME: str = os.environ.get("HOOKCUT_BETREIBER_NAME", "Louis Trajanoski")
STRASSE: str = os.environ.get("HOOKCUT_BETREIBER_STRASSE", "Uhlandstraße 14")
PLZ: str = os.environ.get("HOOKCUT_BETREIBER_PLZ", "40764")
ORT: str = os.environ.get("HOOKCUT_BETREIBER_ORT", "Langenfeld")
LAND: str = os.environ.get("HOOKCUT_BETREIBER_LAND", "Deutschland")
EMAIL: str = os.environ.get("HOOKCUT_BETREIBER_EMAIL", "Louis.Trajanoski@yahoo.de")
# Optional - leer heisst: wird auf der Seite gar nicht erst angezeigt.
TELEFON: str = os.environ.get("HOOKCUT_BETREIBER_TELEFON", "")

# Wie die Plattform nach aussen heisst. Steht hier, damit eine spaetere
# Umbenennung (eigener Name, eigene Domain) eine Zeile ist und keine Suche
# quer durch die Oberflaeche.
PLATTFORM_NAME: str = os.environ.get("HOOKCUT_PLATTFORM_NAME", "selfsign")

# Wer den Dienst technisch betreibt. Gehoert in die Datenschutzerklaerung,
# weil dort Daten verarbeitet werden (Auftragsverarbeitung).
HOSTER_NAME: str = os.environ.get("HOOKCUT_HOSTER_NAME", "Render Services, Inc.")
HOSTER_ORT: str = os.environ.get(
    "HOOKCUT_HOSTER_ORT", "525 Brannan Street, San Francisco, CA 94107, USA")
# Wo die Server tatsaechlich stehen (render.yaml: region frankfurt).
HOSTER_REGION: str = os.environ.get("HOOKCUT_HOSTER_REGION", "Frankfurt am Main, Deutschland")


def als_dict() -> dict[str, str]:
    """Fuer den oeffentlichen Endpunkt /betreiber - die Oberflaeche baut die
    Rechtsseiten daraus, damit die Angaben nicht doppelt gepflegt werden."""
    return {
        "name": NAME,
        "strasse": STRASSE,
        "plz": PLZ,
        "ort": ORT,
        "land": LAND,
        "email": EMAIL,
        "telefon": TELEFON,
        "plattform_name": PLATTFORM_NAME,
        "hoster_name": HOSTER_NAME,
        "hoster_ort": HOSTER_ORT,
        "hoster_region": HOSTER_REGION,
    }
