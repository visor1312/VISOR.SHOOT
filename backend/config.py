"""Zentrale Konfiguration ueber Umgebungsvariablen (fuer das spaetere Hosting).

Lokal laeuft alles mit den Defaults; beim Hosting werden die Werte per
Umgebungsvariablen gesetzt. So muss kein Code angefasst werden, um HOOKCUT
online zu stellen.
"""
from __future__ import annotations

import os


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
