#!/bin/sh
# Startskript im Container. Zwei Aufgaben:
#   1. sicherstellen, dass der Datenordner existiert (dauerhafte Festplatte),
#   2. den Server starten - wahlweise unter Litestream, das die Datenbank
#      laufend zu Cloudflare R2 spiegelt.
#
# Litestream ist ABSICHTLICH optional: die Zugangsdaten fuer R2 gibt es erst,
# wenn der Besitzer dort ein Konto angelegt hat. Fehlen sie, laeuft der Server
# ganz normal ohne Sicherung - der erste Livegang soll nicht daran haengen.
# Sobald LITESTREAM_REPLICA_URL gesetzt ist, sichert er automatisch mit.
set -e

DATEN="${HOOKCUT_PROJECTS_DIR:-/var/hookcut}"
mkdir -p "$DATEN"

# Render gibt den Port ueber die Umgebung vor.
PORT="${PORT:-8000}"

if [ -n "${LITESTREAM_REPLICA_URL:-}" ]; then
  echo "Litestream aktiv: Datenbank wird nach ${LITESTREAM_REPLICA_URL} gespiegelt."
  # Beim Start zurueckholen, falls die Platte leer ist (neue Platte,
  # Plattenschaden). Die beiden Flags decken die harmlosen Faelle ab:
  #   -if-db-not-exists   Datenbank ist schon da -> nichts tun
  #   -if-replica-exists  noch keine Sicherung vorhanden -> nichts tun
  # Alles andere ist ein echter Fehler (z.B. falsche Zugangsdaten) und soll
  # den Start abbrechen: lieber sichtbar stehenbleiben als still ohne
  # Sicherung weiterlaufen. set -e sorgt dafuer.
  litestream restore -if-db-not-exists -if-replica-exists \
    -o "${DATEN}/state.db" "${LITESTREAM_REPLICA_URL}"
  exec litestream replicate -exec \
    "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT}" \
    "${DATEN}/state.db" "${LITESTREAM_REPLICA_URL}"
fi

echo "ACHTUNG: LITESTREAM_REPLICA_URL ist nicht gesetzt - die Datenbank wird NICHT gesichert."
exec uvicorn backend.main:app --host 0.0.0.0 --port "${PORT}"
