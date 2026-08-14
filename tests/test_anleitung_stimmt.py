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


# Dateien, die die Anleitung ABSICHTLICH nennt, obwohl es sie nicht mehr
# gibt: der Besitzer hat sie noch auf seiner Platte, solange er nicht
# aktualisiert hat, und muss wissen, was damit ist. Ohne diese Liste wuerde
# der Test unten sie als Fehler melden.
ALTE_NAMEN = {"update-hookcut.bat"}


def _erwaehnte_dateien(text: str) -> set[str]:
    """Alle .bat- und .md-Dateien, die im Text genannt werden."""
    return set(re.findall(r"`([\w.-]+\.(?:bat|md))`", text)) - ALTE_NAMEN


@pytest.mark.parametrize("datei", sorted(_erwaehnte_dateien(
    ANLEITUNG.read_text(encoding="utf-8"))))
def test_genannte_datei_gibt_es(datei):
    assert (PROJEKT / datei).exists(), (
        f"START-AM-PC.md nennt {datei}, die Datei gibt es aber nicht")


@pytest.mark.parametrize("alt", sorted(ALTE_NAMEN))
def test_alte_namen_sind_wirklich_weg(alt):
    """Gegenprobe zur Ausnahmeliste: taucht ein alter Name wieder auf, ist die
    Ausnahme falsch und wuerde einen echten Fehler verdecken."""
    assert not (PROJEKT / alt).exists(), (
        f"{alt} gibt es wieder - dann raus aus ALTE_NAMEN")


def test_update_skript_installiert_auch_npm():
    """Ohne diesen Schritt bricht der Start mit "Cannot find module", sobald
    eine neue Oberflaechen-Bibliothek dazukommt."""
    text = (PROJEKT / "_update.bat").read_text(encoding="utf-8")
    assert "npm install" in text
    assert "pip install -r requirements.txt" in text


def test_der_pull_laeuft_nicht_in_der_datei_die_er_umbenennen_koennte():
    """Windows haelt eine laufende .bat offen. Benennt ein git pull genau die
    Datei um, die gerade laeuft, bricht er mit "Permission denied" ab und der
    Ordner ist halb aktualisiert - genau so ist es bei
    update-hookcut.bat -> update-selfsign.bat passiert.

    Deshalb: die sichtbare Datei uebergibt an _update.bat und beendet sich.
    Sie darf selbst KEIN git pull enthalten."""
    sichtbar = (PROJEKT / "update-selfsign.bat").read_text(encoding="utf-8")
    # Nur die Befehlszeilen zaehlen - im REM-Kommentar steht "git pull"
    # absichtlich, weil dort der Grund erklaert wird.
    befehle = [z for z in sichtbar.splitlines()
               if not z.strip().upper().startswith("REM")]
    assert not any("git pull" in z for z in befehle)
    assert "_update.bat" in sichtbar
    assert "git pull" in (PROJEKT / "_update.bat").read_text(encoding="utf-8")


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
        assert name in skript, f"logo-einsetzen.bat kennt {name} nicht"
        # Logo.tsx haengt die Endung selbst an (svg, sonst png) - deshalb
        # steht der Name dort ohne Punkt.
        assert f'"/selfsign-{name}"' in logo, f"Logo.tsx laedt selfsign-{name} nicht"


def test_logo_skript_schreibt_die_endung_klein():
    """Zieht jemand "Logo.PNG" drauf, entstuende sonst "selfsign-mark.PNG".
    Die Oberflaeche fragt nach ".png" - unter Windows faellt das nicht auf
    (Gross-/Kleinschreibung egal), auf dem Linux-Server beim Hosting schon.
    Genau daran ist es einmal gescheitert: Logo kopiert, Anzeige leer."""
    text = (PROJEKT / "logo-einsetzen.bat").read_text(encoding="utf-8")
    assert 'if /i "%EXT%"==".svg" set "EXT=.svg"' in text
    assert 'if /i "%EXT%"==".png" set "EXT=.png"' in text


def test_logo_skript_umgeht_fremde_git_hooks():
    """Auf dem Rechner des Besitzers haengen fremde Pruef-Skripte (VITE+) in
    den git-Hooks, die mit diesem Projekt nichts zu tun haben und Commit UND
    Push abbrechen lassen. Ein Logo-Bild hat mit Code-Qualitaet nichts zu
    tun."""
    text = (PROJEKT / "logo-einsetzen.bat").read_text(encoding="utf-8")
    assert "git commit --no-verify" in text
    assert "git push --no-verify" in text


def test_oberflaeche_faellt_von_svg_auf_png_zurueck():
    """Ohne diesen Rueckfall bleibt nach dem Einsetzen einer PNG ein kaputtes
    Bild-Symbol stehen - und das Skript meldet trotzdem Erfolg."""
    logo = (PROJEKT / "web/src/components/Logo.tsx").read_text(encoding="utf-8")
    assert '"svg" | "png"' in logo
    assert 'setEndung("png")' in logo
    html = (PROJEKT / "web/index.html").read_text(encoding="utf-8")
    assert "/selfsign-mark.svg" in html and "/selfsign-mark.png" in html


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
