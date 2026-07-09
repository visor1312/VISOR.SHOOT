# Rap-Video Auto-Editor

Lokal laufendes Tool, um ein zum Playback mitgerapptes Handyvideo zeitlich
exakt mit der fertig produzierten Songdatei zu synchronisieren und als
9:16-Video (TikTok/Instagram) zu exportieren.

**Wichtig:** Es gibt bewusst kein KI-generiertes Lip-Sync. Die Lippenbewegungen
im Video passen bereits zum Song (Playback lief beim Filmen). Die einzige
Aufgabe ist Audio-Video-Synchronisation: die richtige Stelle im Song finden und
zeitlich exakt über das Video legen.

Aktueller Stand: **Phase 1 (Sync)** und **Phase 2 (Untertitel)** sind fertig
und lauffähig, beide mit echtem Handymaterial getestet.

## Setup

```bash
pip install -r requirements.txt
```

ffmpeg muss zusätzlich als Systempaket installiert sein (`apt install ffmpeg`
o.ä.) - wird nicht über pip installiert.

`faster-whisper` (Phase 2) lädt beim ersten Aufruf automatisch ein
Spracherkennungsmodell von Hugging Face herunter (je nach Modellgröße
100 MB - ~3 GB, siehe Abschnitt "Untertitel"). Dafür ist beim ersten Mal
Internetzugang nötig, danach läuft alles offline.

## Nutzung

### Gradio-Oberfläche (empfohlen für den MVP-Workflow)

```bash
python -m frontend.app
```

Öffnet eine lokale Web-Oberfläche (Standard: http://127.0.0.1:7860). Songdatei
und einen oder mehrere Video-Takes derselben Songstelle hochladen, auf
"Synchronisieren" klicken. Jeder Take wird einzeln gegen den Song
synchronisiert (eigener Zeitversatz pro Take) und als 9:16 H.264-Video
ausgegeben, inkl. Vorschau, Download, sowie einer eigenen Anzeige für
Zeitversatz (ms) und Konfidenz.

Pro Take kann danach "Transkribieren" geklickt werden (Whisper-Modellgröße und
Sprache waehlbar). Das erkannte Transkript erscheint als editierbare Tabelle
(Start/Ende/Wort) - **bitte immer pruefen und korrigieren**, bevor auf
"Untertitel rendern" geklickt wird (Whisper macht bei Rap-Slang/Dialekt
Fehler). Danach steht ein zweites Video mit eingebrannten Untertiteln zum
Download bereit, optional im TikTok-typischen Karaoke-Stil (aktuelles Wort
farblich hervorgehoben).

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

# Phase 2 (Untertitel):
python -m backend.pipeline.transcribe output.mp4 --language de --model-size large-v3 --json > words.json
python -m backend.pipeline.subtitles words.json subs.ass --karaoke --burn-into output.mp4 --burn-out output_with_subs.mp4
```

## Architektur

```
backend/
  pipeline/
    extract_audio.py   # Ton aus Video extrahieren (ffmpeg)
    sync_offset.py      # Zeitversatz via Onset-Einhuellenden-Kreuzkorrelation (scipy/librosa)
    render_sync.py       # Song synchron über Video legen, 9:16 H.264 Export (ffmpeg)
    transcribe.py         # Deutsche Transkription mit Wort-Zeitstempeln (faster-whisper)
    subtitles.py           # Wort-Zeitstempel -> ASS-Datei (+ Karaoke-Stil), Einbrennen (ffmpeg)
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

`sync_offset.py` lädt Songdatei und extrahierten Video-Ton, berechnet daraus
die Lautstärke-/Onset-Einhüllende (nicht das Rohsignal) und kreuzkorreliert
diese, um zu bestimmen, an welcher Stelle im Song der Video-Clip zeitlich
liegt (funktioniert auch, wenn die Songdatei viel länger ist als der
20-30-Sekunden-Clip). Das Ergebnis ist ein `offset_ms` plus ein
`confidence`-Wert (Konfidenz der Erkennung, 0-1).

Die Einhüllende statt des Rohsignals zu nutzen, war ein Ergebnis des Tests mit
echtem Handymaterial: Eine per Telefonmikro aufgenommene Performance (Raumhall,
Lautsprecher-/Mikro-Verzerrung) korreliert im Rohsignal nur schwach mit einer
sauber aufgenommenen Songreferenz (Konfidenz ~0.1 trotz korrektem Offset),
während die Einhüllende denselben Offset mit deutlich höherer Konfidenz
(~0.45-0.8) findet.

`render_sync.py` nutzt diesen Offset, um die Songspur per ffmpeg exakt über
das Video zu legen (Song wird je nach Vorzeichen des Offsets beschnitten oder
verzögert), schneidet/skaliert das Video auf 9:16 und exportiert als H.264 mit
AAC-Ton. Der Original-Videoton wird standardmäßig stummgeschaltet, kann aber
optional leise im Hintergrund mitlaufen (`--original-audio-mode background`).

Getestet sowohl mit synthetisch erzeugten Video-/Audiodateien (bekannter,
absichtlich eingebauter Zeitversatz, positiv und negativ) als auch mit echtem,
selbst gefilmtem Handymaterial (61 Sek. Performance-Video gegen eine
Songreferenz aus einer Screen-Recording) - in beiden Fällen wurde der Offset
exakt erkannt und durch Hörprobe bestätigt.

## Wie die Untertitel funktionieren

`transcribe.py` transkribiert die bereits **synchronisierte** Output-Audiospur
(nicht die rohe Songdatei) mit faster-whisper und liefert Wort-Zeitstempel, die
direkt im Zeitrahmen des fertigen Videos liegen - keine zusätzliche
Offset-Verrechnung nötig. Sprache ist per Default Deutsch, kann aber pro Take
auf Englisch umgestellt werden (falls der Songtext teils englisch ist).

Im Gradio-Frontend erscheint das Transkript als editierbare Tabelle
(Start/Ende/Wort) - **das ist ein Pflicht-Schritt, kein Nice-to-have**, da
Whisper bei Rap-Slang/Dialekt zuverlässig Fehler macht.

`subtitles.py` gruppiert die (korrigierten) Wörter zu Untertitelzeilen
(Zeilenumbruch bei Sprechpause, zu langer Zeilendauer oder zu vielen Zeichen),
schreibt eine ASS-Datei und brennt sie per ffmpeg (`ass`-Filter, libass) ins
Video ein. Zwei Stile stehen zur Wahl: normale Zeilen oder TikTok-typischer
Karaoke-Stil, bei dem das gerade gesprochene Wort gelb hervorgehoben wird.

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
- **Whisper-Genauigkeit:** Keine Garantie für fehlerfreie automatische
  Untertitel - die Korrekturtabelle im Frontend ist deshalb ein Pflicht-Schritt.
- **Whisper-Geschwindigkeit:** Läuft komplett auf der CPU (keine GPU-Pflicht,
  kein Cloud-Zwang). Größere Modelle (medium/large-v3) sind genauer, aber
  spürbar langsamer als kleinere (tiny/base/small) - bei schwacher CPU lohnt
  sich ein kleineres Modell zum Ausprobieren.
- **Phase 3 (Beat-Effekte, Multi-Take-Schnitt, Farbgrading, Upscaling)** ist
  noch nicht umgesetzt.

## Nächste Schritte

Phase 1 und 2 sind bereit zum Testen mit echtem Material. Rückmeldung, ob
Sync und Untertitel wie erwartet funktionieren, dann geht es mit Phase 3
(Beat-Effekte, Multi-Take-Schnitt, Farbgrading, optionales Upscaling) weiter.
