#!/bin/bash
# Installiert die Abhaengigkeiten, damit Tests, Build und Linter in einer
# frischen Claude-Code-Session sofort laufen.
#
# Hintergrund: Die Cloud-Umgebung startet den Container neu (und faellt
# gelegentlich auf einen aelteren Stand zurueck). Ohne diesen Hook fehlen
# dann z.B. react-router-dom oder bcrypt, und der erste Build/Test bricht ab.
#
# Laeuft NUR in der Cloud-Umgebung - auf dem Windows-Rechner des Besitzers
# machen das start-hookcut.bat / update-hookcut.bat.
set -euo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

cd "${CLAUDE_PROJECT_DIR:-$(dirname "$0")/../..}"

# demucs (Vocal-Separation) laesst sich in der Cloud-Umgebung nicht bauen -
# es gibt kein passendes Wheel, und der Build scheitert an setuptools. Das
# Paket ist laut vocal_separation.py bewusst OPTIONAL (is_demucs_available()
# faellt sauber auf den Librosa-Pfad zurueck), und die Modelle liessen sich
# hier ohnehin nicht herunterladen. Also herausfiltern, statt den ganzen
# Install daran scheitern zu lassen (spart ausserdem ~1,5 Minuten).
REQ_TMP="$(mktemp)"
trap 'rm -f "$REQ_TMP"' EXIT
grep -v '^demucs' requirements.txt > "$REQ_TMP"

echo "[HOOKCUT] Python-Pakete installieren (ohne demucs, siehe Kommentar)..."
python -m pip install --quiet --disable-pip-version-check -r "$REQ_TMP"

echo "[HOOKCUT] npm-Pakete fuer web/ installieren..."
npm install --prefix web --no-audit --no-fund --silent

# editor/ (FreeCut-Fork) wird bewusst ausgelassen: der Render laeuft nur auf
# dem Rechner des Besitzers (Chrome/WebGPU) und die Installation scheitert
# hier teils am Netzwerk. Fuer Tests, Build und Linter wird sie nicht gebraucht.

# Kurzer Selbsttest - lieber hier laut scheitern als spaeter mitten im Build.
python - <<'PY'
import importlib.util
fehlt = [m for m in ("fastapi", "bcrypt", "librosa", "pytest")
         if not importlib.util.find_spec(m)]
if fehlt:
    raise SystemExit("[HOOKCUT] FEHLER: Pakete fehlen: " + ", ".join(fehlt))
PY

echo "[HOOKCUT] Fertig."
