# HOOKCUT als EIN Dienst: Node baut die Oberflaeche, Python liefert sie
# zusammen mit der API aus. Zwei Stufen, damit Node und die halbe
# npm-Welt nicht im fertigen Image landen.
#
# WICHTIG: Dieses Image betreibt NUR das Netzwerk. Die Video-Werkzeuge
# brauchen Chrome mit WebGPU und mehrere GB an Modellen - die laufen auf
# dem Rechner des Besitzers (HOOKCUT_TOOLS_ENABLED=0, siehe unten).

# --- Stufe 1: Oberflaeche bauen -------------------------------------------
FROM node:22-slim AS oberflaeche
WORKDIR /bau

# Erst nur die Paketlisten kopieren: solange die sich nicht aendern,
# benutzt Docker den zwischengespeicherten npm-Schritt wieder.
COPY web/package.json web/package-lock.json ./
RUN npm ci

COPY web/ ./
# Baut nach /bau/dist (tsc -b && vite build).
RUN npm run build


# --- Stufe 2: Server ------------------------------------------------------
FROM python:3.11-slim

# ffmpeg/ffprobe: ohne ffprobe wird JEDE hochgeladene Hoerprobe abgelehnt
# (backend/network.py prueft damit die Laenge). Kein Python-Paket, sondern
# ein Systemprogramm - deshalb hier und nicht in requirements-server.txt.
RUN apt-get update \
 && apt-get install -y --no-install-recommends ffmpeg curl ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# Litestream spiegelt die SQLite-Datenbank laufend zu Cloudflare R2. Das
# Programm liegt schon im Image; ob es benutzt wird, entscheidet allein
# LITESTREAM_REPLICA_URL (siehe docker-start.sh) - so blockiert der noch
# fehlende R2-Zugang den ersten Livegang nicht.
# ACHTUNG beim Hochziehen der Version: die Datei heisst OHNE "v" und mit
# "x86_64" (nicht "amd64") - der naheliegende Name ergibt einen 404 und der
# Bau bricht ab.
ARG LITESTREAM_VERSION=0.5.16
RUN curl -fsSL -o /tmp/litestream.deb \
      "https://github.com/benbjohnson/litestream/releases/download/v${LITESTREAM_VERSION}/litestream-${LITESTREAM_VERSION}-linux-x86_64.deb" \
 && dpkg -i /tmp/litestream.deb \
 && rm /tmp/litestream.deb \
 && litestream version

WORKDIR /app

# Nur die schlanke Liste: fastapi, uvicorn, bcrypt, python-multipart.
# requirements.txt waere hier falsch - librosa und Co. sind rund 1,5 GB, und
# demucs laesst sich in so einem Image gar nicht bauen.
COPY requirements-server.txt ./
RUN pip install --no-cache-dir -r requirements-server.txt

COPY backend/ ./backend/
# Die gebaute Oberflaeche muss unter web/dist liegen - genau dort sucht
# backend/main.py sie (FRONTEND_DIR, ganz am Ende der Datei).
COPY --from=oberflaeche /bau/dist ./web/dist

COPY docker-start.sh ./
RUN chmod +x docker-start.sh

# Voreinstellungen fuers Hosting. Alles hier ist ueberschreibbar - render.yaml
# setzt dieselben Werte noch einmal sichtbar, damit man sie nicht im
# Dockerfile suchen muss.
ENV HOOKCUT_TOOLS_ENABLED=0 \
    HOOKCUT_LOCAL_RENDER=0 \
    HOOKCUT_SECURE_COOKIES=1 \
    HOOKCUT_INVITE_ONLY=1 \
    HOOKCUT_PROJECTS_DIR=/var/hookcut \
    PORT=8000

EXPOSE 8000
CMD ["./docker-start.sh"]
