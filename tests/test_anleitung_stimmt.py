"""Zeigt die Anleitung fuer den Besitzer auf Dateien, die es wirklich gibt?

START-AM-PC.md ist das, was der Besitzer liest, wenn er den Rechner
anmacht. Wird eine .bat-Datei umbenannt oder geloescht, steht dort eine
Anweisung, die ins Leere fuehrt - und er sitzt vor einem Doppelklick, der
nichts tut. Genau dieser Fall ist hier abgesichert.

Anlass: in update-selfsign.bat stand jahrelang der Kommentar, _frontend.bat
ziehe die npm-Pakete beim Start nach. Das stimmte nie - _frontend.bat ruft
"npm run dev" auf, und das installiert nichts.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

PROJEKT = Path(__file__).resolve().parent.parent
ANLEITUNG = PROJEKT / "START-AM-PC.md"


def test_anleitung_existiert():
    assert ANLEITUNG.exists(), "START-AM-PC.md fehlt - README verweist darauf"


def _erwaehnte_dateien(text: str) -> set[str]:
    """Alle .bat- und .md-Dateien, die im Text genannt werden."""
    return set(re.findall(r"`([\w.-]+\.(?:bat|md))`", text))


@pytest.mark.parametrize("datei", sorted(_erwaehnte_dateien(
    ANLEITUNG.read_text(encoding="utf-8"))))
def test_genannte_datei_gibt_es(datei):
    assert (PROJEKT / datei).exists(), (
        f"START-AM-PC.md nennt {datei}, die Datei gibt es aber nicht")


def test_update_skript_installiert_auch_npm():
    """Ohne diesen Schritt bricht der Start mit "Cannot find module", sobald
    eine neue Oberflaechen-Bibliothek dazukommt."""
    text = (PROJEKT / "update-selfsign.bat").read_text(encoding="utf-8")
    assert "npm install" in text
    assert "pip install -r requirements.txt" in text


def test_testmodus_setzt_den_richtigen_schalter():
    text = (PROJEKT / "_backend-premium.bat").read_text(encoding="utf-8")
    assert "HOOKCUT_PREMIUM_REQUIRED=1" in text
    # Der Schalter muss VOR dem Serverstart gesetzt werden, sonst liest
    # backend/config.py ihn nie.
    assert text.index("HOOKCUT_PREMIUM_REQUIRED=1") < text.index("uvicorn")


def test_logo_skript_kennt_alle_drei_zieldateien():
    """MARKE.md nennt drei Dateinamen - logo-einsetzen.bat muss genau die
    erzeugen und Logo.tsx genau die laden. Sonst legt das Skript das Logo an
    eine Stelle, die niemand liest, und der Besitzer sucht den Fehler bei
    sich."""
    skript = (PROJEKT / "logo-einsetzen.bat").read_text(encoding="utf-8")
    logo = (PROJEKT / "web/src/components/Logo.tsx").read_text(encoding="utf-8")
    for name in ("mark", "lockup-h", "lockup-v"):
        assert f"selfsign-%ZIEL%" in skript or name in skript, \
            f"logo-einsetzen.bat kennt {name} nicht"
        assert f"/selfsign-{name}." in logo, f"Logo.tsx laedt selfsign-{name} nicht"


def test_nachgebaute_marke_ist_als_solche_gekennzeichnet():
    """Sonst haelt sie irgendwann jemand fuer das Original - auch ich beim
    naechsten Mal."""
    svg = (PROJEKT / "web/public/selfsign-mark.svg").read_text(encoding="utf-8")
    assert "NACHGEBAUT" in svg.upper()


def test_abo_skript_ruft_die_echten_befehle():
    """Die Menuepunkte muessen zu backend/admin.py passen."""
    text = (PROJEKT / "selfsign-abo.bat").read_text(encoding="utf-8")
    for befehl in ("abo-liste", "abo-geben", "abo-nehmen"):
        assert befehl in text, f"selfsign-abo.bat ruft {befehl} nicht auf"
    assert "--unbefristet" in text
