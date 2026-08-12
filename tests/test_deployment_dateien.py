"""Passen Dockerfile, render.yaml und docker-start.sh zusammen?

Diese drei Dateien lassen sich hier nicht ausfuehren (die Umgebung darf
keine Docker-Basis-Images laden), aber ihre Aussagen muessen
zusammenpassen. Ein Widerspruch faellt sonst erst beim Ausrollen auf - und
im schlimmsten Fall gar nicht, sondern erst, wenn nach einem Update die
Daten weg sind.

Anlass: HOOKCUT_API_DOCS war in render.yaml gesetzt, im Dockerfile aber
vergessen. Ein Dienst, der ohne render.yaml gebaut wird, haette dann die
API-Dokumentation offen gehabt.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

PROJEKT = Path(__file__).resolve().parent.parent
DOCKERFILE = (PROJEKT / "Dockerfile").read_text(encoding="utf-8")
STARTSKRIPT = (PROJEKT / "docker-start.sh").read_text(encoding="utf-8")
RENDER = yaml.safe_load((PROJEKT / "render.yaml").read_text(encoding="utf-8"))
DIENST = RENDER["services"][0]
RENDER_ENV = {e["key"]: e.get("value") for e in DIENST["envVars"]}


def _dockerfile_env() -> dict[str, str]:
    """Die ENV-Zeile des Dockerfiles (mit Zeilenfortsetzungen) einlesen."""
    ohne_umbruch = DOCKERFILE.replace("\\\n", " ")
    werte = {}
    for zeile in ohne_umbruch.splitlines():
        if zeile.startswith("ENV "):
            for paar in re.findall(r"(\w+)=(\S+)", zeile[4:]):
                werte[paar[0]] = paar[1]
    return werte


DOCKER_ENV = _dockerfile_env()

# Schalter, die online GESETZT sein muessen - und zwar an beiden Stellen
# gleich. Das Dockerfile ist die Absicherung: wird der Dienst ohne
# render.yaml angelegt, gelten nur diese Werte.
ONLINE_SCHALTER = {
    "HOOKCUT_TOOLS_ENABLED": "0",   # keine Video-Werkzeuge auf dem Server
    "HOOKCUT_LOCAL_RENDER": "0",    # dieser Prozess rendert nichts
    "HOOKCUT_SECURE_COOKIES": "1",  # Session-Cookie nur ueber HTTPS
    "HOOKCUT_INVITE_ONLY": "1",     # Tuer zu bis Schritt 7
    "HOOKCUT_API_DOCS": "0",        # keine Routen-Landkarte fuer Fremde
    # Ohne diesen sperrt die Registrierungs-Bremse alle Nutzer gemeinsam
    # aus, weil hinter dem Proxy jede Anfrage dieselbe Adresse hat.
    "HOOKCUT_TRUST_PROXY": "1",
}


@pytest.mark.parametrize("schluessel,soll", sorted(ONLINE_SCHALTER.items()))
def test_schalter_in_render_yaml(schluessel, soll):
    assert RENDER_ENV.get(schluessel) == soll, (
        f"render.yaml: {schluessel} ist {RENDER_ENV.get(schluessel)!r}, erwartet {soll!r}")


@pytest.mark.parametrize("schluessel,soll", sorted(ONLINE_SCHALTER.items()))
def test_schalter_auch_im_dockerfile(schluessel, soll):
    """Doppelt gesetzt mit Absicht: wer den Dienst von Hand anlegt statt
    ueber die render.yaml, bekommt trotzdem die sicheren Werte."""
    assert DOCKER_ENV.get(schluessel) == soll, (
        f"Dockerfile: {schluessel} ist {DOCKER_ENV.get(schluessel)!r}, erwartet {soll!r}")


def test_datenordner_zeigt_auf_die_platte():
    """Der wichtigste Zusammenhang von allen: zeigt HOOKCUT_PROJECTS_DIR
    nicht auf die angehaengte Platte, sind Konten und Hoerproben nach dem
    naechsten Ausrollen weg."""
    mount = DIENST["disk"]["mountPath"]
    assert RENDER_ENV.get("HOOKCUT_PROJECTS_DIR") == mount
    assert DOCKER_ENV.get("HOOKCUT_PROJECTS_DIR") == mount
    assert mount in STARTSKRIPT, "docker-start.sh legt den Ordner nicht an"


def test_healthcheck_gibt_es_wirklich():
    from backend.main import app
    assert DIENST["healthCheckPath"] in app.openapi()["paths"]


def test_oberflaeche_landet_wo_das_backend_sie_sucht():
    from backend import main
    erwartet = main.FRONTEND_DIR.relative_to(PROJEKT)
    assert f"./{erwartet}" in DOCKERFILE, (
        f"Dockerfile muss die gebaute Oberflaeche nach ./{erwartet} kopieren")


def test_server_pakete_haben_dieselbe_version_wie_die_grosse_liste():
    """Zwei Paketlisten, die auseinanderdriften, sind schlimmer als eine."""
    def lies(name: str) -> dict[str, str]:
        werte = {}
        for zeile in (PROJEKT / name).read_text(encoding="utf-8").splitlines():
            zeile = zeile.strip()
            if zeile and not zeile.startswith("#") and "==" in zeile:
                paket, version = zeile.split("==", 1)
                werte[paket.strip().lower()] = version.strip()
        return werte

    voll, schlank = lies("requirements.txt"), lies("requirements-server.txt")
    for paket, version in schlank.items():
        assert paket in voll, f"{paket} fehlt in requirements.txt"
        assert voll[paket] == version, (
            f"{paket}: Server {version}, volle Liste {voll[paket]}")
