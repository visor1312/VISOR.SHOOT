"""Zentrale Konfiguration ueber Umgebungsvariablen (fuer das spaetere Hosting).

Lokal laeuft alles mit den Defaults; beim Hosting werden die Werte per
Umgebungsvariablen gesetzt. So muss kein Code angefasst werden, um HOOKCUT
online zu stellen.
"""
from __future__ import annotations

import os
from pathlib import Path


def _env_bool(name: str, default: bool) -> bool:
    val = os.environ.get(name)
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes", "on")


def _env_list(name: str, default: list[str]) -> list[str]:
    val = os.environ.get(name)
    if not val:
        return default
    return [x.strip() for x in val.split(",") if x.strip()]


def _env_int(name: str, default: int) -> int:
    """Unsinnige Werte fallen auf den Standard zurueck - eine vertippte
    Umgebungsvariable soll den Server nicht am Starten hindern."""
    val = os.environ.get(name)
    if val is None:
        return default
    try:
        return int(val.strip())
    except ValueError:
        return default


# Wo liegen die Nutzerdaten (Datenbank, Hoerproben, Videos, fertige Reels)?
# Lokal der projects/-Ordner im Projekt. Beim Hosting MUSS das auf die
# dauerhafte Festplatte zeigen (HOOKCUT_PROJECTS_DIR=/var/hookcut): der
# Container selbst ist fluechtig - alles, was in ihm liegt, ist nach dem
# naechsten Ausrollen weg, also Konten, Beitraege und Hoerproben.
# Die Datenbank folgt automatisch mit (db.DEFAULT_DB_PATH), damit EIN Schalter
# genuegt; HOOKCUT_DB kann sie einzeln woandershin legen (so machen es die
# Tests).
PROJECTS_DIR: Path = Path(
    os.environ.get("HOOKCUT_PROJECTS_DIR")
    or Path(__file__).resolve().parent.parent / "projects"
)

# Erlaubte Browser-Herkuenfte (CORS). Lokal der Vite-Dev-Server; beim Hosting
# die echte Domain(s) via HOOKCUT_CORS_ORIGINS="https://app.hookcut.de,...".
CORS_ORIGINS: list[str] = _env_list(
    "HOOKCUT_CORS_ORIGINS",
    ["http://localhost:5173", "http://127.0.0.1:5173"],
)

# Secure-Flag am Session-Cookie: lokal aus (kein HTTPS), beim Hosting an.
# Einzige Quelle - auth._secure_cookies() liest diesen Wert.
SECURE_COOKIES: bool = _env_bool("HOOKCUT_SECURE_COOKIES", False)

# Rendert dieser Prozess selbst (lokale App, In-Process-Worker)? Beim Hosting
# im Hybrid-Modell auf 0/false setzen: dann bleiben die Render-Auftraege offen
# und ein lokaler Render-Agent zieht sie ueber den /render-Vertrag ab.
LOCAL_RENDER: bool = _env_bool("HOOKCUT_LOCAL_RENDER", True)

# Registrierung nur mit Einladungscode? Als lokales Einzelplatz-Werkzeug bleibt
# das an (sichere Voreinstellung: wer das Backend erreicht, kann sich nicht
# einfach ein Konto anlegen). Die oeffentliche Musiker-Plattform setzt
# HOOKCUT_INVITE_ONLY=0 - dann ist die Registrierung fuer alle offen.
INVITE_ONLY: bool = _env_bool("HOOKCUT_INVITE_ONLY", True)

# Sind die Video-Werkzeuge verfuegbar (Reel-Assistent, Hook-Analyse, Canvas,
# Wochen-Content)? Die brauchen Chrome mit WebGPU, ffmpeg und mehrere GB an
# Modellen - das gibt es nur auf dem Rechner des Besitzers. Der gehostete
# Server setzt HOOKCUT_TOOLS_ENABLED=0: dann verschwinden sie aus der
# Oberflaeche und die Routen antworten verstaendlich, statt mitten im
# Hintergrund-Job zu scheitern.
TOOLS_ENABLED: bool = _env_bool("HOOKCUT_TOOLS_ENABLED", True)

# Die automatische API-Dokumentation (/docs, /redoc, /openapi.json). Lokal
# beim Entwickeln nuetzlich, oeffentlich aber eine fertige Landkarte der
# gesamten Schnittstelle - inklusive der Admin-Routen und aller Parameter.
# Das muss ein Fremder nicht bekommen, deshalb online aus.
API_DOCS: bool = _env_bool("HOOKCUT_API_DOCS", True)

# Steht ein Reverse-Proxy davor (Render, nginx, Cloudflare)?
#
# WARUM DAS EIN SCHALTER IST UND KEIN AUTOMATISMUS: Hinter einem Proxy
# kommen ALLE Anfragen von derselben Adresse - ein Rate-Limit auf
# request.client.host wuerde also saemtliche Nutzer GEMEINSAM aussperren.
# Die echte Adresse steht in X-Forwarded-For. Dieser Kopfzeile darf man
# aber nur trauen, wenn wirklich ein Proxy davorsteht: sonst schreibt sich
# jeder Angreifer einfach selbst eine hinein und umgeht jedes Limit.
# Lokal deshalb aus, in render.yaml an.
TRUST_PROXY: bool = _env_bool("HOOKCUT_TRUST_PROXY", False)

# Wie viele Konten darf eine Adresse pro Stunde anlegen? Ohne diese Bremse
# kann ein Skript die offene Plattform mit Konten fluten. 5 ist grosszuegig
# fuer eine WG oder ein Studio mit gemeinsamem Anschluss und trotzdem eng
# genug gegen Automatisierung.
REGISTER_MAX_PER_HOUR: int = _env_int("HOOKCUT_REGISTER_MAX_PER_HOUR", 5)
