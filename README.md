# Rap-Video Auto-Editor

Lokal laufendes Tool, um ein zum Playback mitgerapptes Handyvideo zeitlich
exakt mit der fertig produzierten Songdatei zu synchronisieren und als
9:16-Video (TikTok/Instagram) zu exportieren.

**Wichtig:** Es gibt bewusst kein KI-generiertes Lip-Sync. Die Lippenbewegungen
im Video passen bereits zum Song (Playback lief beim Filmen). Die einzige
Aufgabe ist Audio-Video-Synchronisation: die richtige Stelle im Song finden und
zeitlich exakt über das Video legen.

Aktueller Stand: **Phase 1 (Sync)** ist fertig und lauffähig.

## Setup

```bash
pip install -r requirements.txt
```

ffmpeg muss zusätzlich als Systempaket installiert sein (`apt install ffmpeg`
o.ä.) - wird nicht über pip installiert.

## Nutzung

### Gradio-Oberfläche (empfohlen für den MVP-Workflow)

```bash
python -m frontend.app
```

Öffnet eine lokale Web-Oberfläche (Standard: http://127.0.0.1:7860). Songdatei
und einen oder mehrere Video-Takes derselben Songstelle hochladen, auf
"Synchronisieren" klicken. Jeder Take wird einzeln gegen den Song
synchronisiert (eigener Zeitversatz pro Take) und als 9:16 H.264-Video
ausgegeben, inkl. Vorschau und Download.

### FastAPI-Backend (programmatischer Zugriff)

```bash
uvicorn backend.main:app --reload
```

Endpunkte:

- `POST /projects` (`name`, `song`) → `{project_id}`
- `POST /projects/{project_id}/takes` (`video`, `original_audio_mode`) → `{take_id}`
- `POST /projects/{project_id}/takes/{take_id}/sync` → führt die Pipeline aus, liefert Status/Offset/Konfidenz
- `GET /projects/{project_id}/takes/{take_id}` → Status abfragen
- `GET /projects/{project_id}/takes` → alle Takes eines Projekts
- `GET /projects/{project_id}/takes/{take_id}/download` → fertiges Video herunterladen

### Pipeline-Schritte einzeln (CLI, zum isolierten Testen)

```bash
python -m backend.pipeline.extract_audio video.mp4 audio.wav
python -m backend.pipeline.sync_offset song.wav audio.wav
python -m backend.pipeline.render_sync video.mp4 song.wav <offset_ms> output.mp4 [--original-audio-mode mute|background]
```

## Architektur

```
backend/
  pipeline/
    extract_audio.py   # Ton aus Video extrahieren (ffmpeg)
    sync_offset.py      # Zeitversatz via FFT-Cross-Correlation (scipy)
    render_sync.py       # Song synchron über Video legen, 9:16 H.264 Export (ffmpeg)
  db.py                  # SQLite: Projekte + Takes
  storage.py              # gemeinsame Verzeichnis-Konventionen (/projects/<id>/...)
  main.py                  # FastAPI-Endpunkte
frontend/
  app.py                   # Gradio-Oberfläche (ruft pipeline-Funktionen direkt auf)
projects/
  <projekt-id>/...          # Song, Takes, Zwischenergebnisse, Exporte
```

Jeder Pipeline-Schritt ist einzeln über die CLI testbar (siehe oben), bevor er
im Frontend verwendet wird.

## Wie die Synchronisation funktioniert

`sync_offset.py` lädt Songdatei und extrahierten Video-Ton, führt eine
FFT-Cross-Correlation durch und bestimmt, an welcher Stelle im Song der
Video-Clip zeitlich liegt (funktioniert auch, wenn die Songdatei viel länger
ist als der 20-30-Sekunden-Clip). Das Ergebnis ist ein `offset_ms` plus ein
`confidence`-Wert (Konfidenz der Erkennung, 0-1).

`render_sync.py` nutzt diesen Offset, um die Songspur per ffmpeg exakt über
das Video zu legen (Song wird je nach Vorzeichen des Offsets beschnitten oder
verzögert), schneidet/skaliert das Video auf 9:16 und exportiert als H.264 mit
AAC-Ton. Der Original-Videoton wird standardmäßig stummgeschaltet, kann aber
optional leise im Hintergrund mitlaufen (`--original-audio-mode background`).

Getestet mit synthetisch erzeugten Video-/Audiodateien (ffmpeg `lavfi`
Testquellen mit bekanntem, absichtlich eingebautem Zeitversatz) für sowohl
positive als auch negative Offsets - beide wurden exakt erkannt und korrekt
gerendert.

## Bekannte Grenzen (bewusst, siehe Nicht-Ziele)

- **Keine Drift-Korrektur:** Falls die Handy-Samplerate über die Videolänge
  leicht abweicht und Ton/Bild dadurch merklich auseinanderlaufen, ist das
  noch nicht behoben (Time-Stretching in kurzen Fenstern wäre die Lösung,
  aber laut Vorgabe erst bauen, wenn Tests zeigen, dass es nötig ist). Bei
  20-30-Sekunden-Clips ist das i.d.R. kein Problem.
- **Konfidenz ist ein Hinweis, keine Garantie:** Bei sehr leisem oder stark
  verzerrtem Video-Ton kann die Cross-Correlation den falschen Offset finden.
  Niedrige Konfidenz wird im UI markiert - Ergebnis dann manuell prüfen.
- **Kein KI-Lip-Sync** - bewusst nicht gebaut, siehe oben.
- **Phase 2 (Untertitel) und Phase 3 (Beat-Effekte, Grading, Upscaling)** sind
  noch nicht umgesetzt.

## Nächste Schritte

Nach deinem Test mit echtem Material (Handyvideo + Songdatei): Rückmeldung,
ob die Synchronisation sauber sitzt. Dann geht es mit Phase 2 (automatische
deutsche Untertitel via faster-whisper + manuelle Korrektur) weiter.
