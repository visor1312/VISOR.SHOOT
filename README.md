# Rap-Video Auto-Editor

Lokal laufendes Tool, um ein zum Playback mitgerapptes Handyvideo zeitlich
exakt mit der fertig produzierten Songdatei zu synchronisieren und als
9:16-Video (TikTok/Instagram) zu exportieren.

**Wichtig:** Es gibt bewusst kein KI-generiertes Lip-Sync. Die Lippenbewegungen
im Video passen bereits zum Song (Playback lief beim Filmen). Die einzige
Aufgabe ist Audio-Video-Synchronisation: die richtige Stelle im Song finden und
zeitlich exakt über das Video legen.

Aktueller Stand: **Phase 1 (Sync)**, **Phase 2 (Untertitel)** und **Phase 3
(Effekte, Grading, Upscaling)** sind fertig und lauffähig.

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

**Upscaling (Phase 3) ist optional** und braucht zusätzliche, in
`requirements.txt` nur auskommentierte Pakete (torch/basicsr/realesrgan).
Installation in zwei Schritten (siehe Abschnitt "Upscaling" für den Grund):

```bash
pip install torch torchvision opencv-python
pip install --no-build-isolation basicsr realesrgan
```

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

Darunter: **Farbgrading & Beat-Effekte** (Farbpreset waehlen, vier Effekte
mit Intensitaetsregler 0-1: Zoom-Pulse, Flash, Shake, RGB-Split-Kick, alle
takgenau auf die erkannten Taktschlaege dieses Takes). Wurden **mindestens 2
Takes** erfolgreich synchronisiert, erscheint darunter der Bereich
**Multi-Take-Schnitt**: Wechsel-Rhythmus (jeden/jeden 2./jeden 4. Takt) und
Take-Reihenfolge (fest/zufaellig) waehlen, ein Klick erzeugt einen
durchgehenden Song mit taktgenau geschnittenem Bildwechsel zwischen den Takes.

Ganz unten pro Take: **Upscaling** (optional, siehe Warnhinweis im UI zur
Rechenzeit) - wirkt auf die zuletzt erzeugte Version dieses Takes (mit
Effekten > mit Untertiteln > nur Sync).

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

# Phase 3 (Beat-Erkennung, Effekte/Grading, Upscaling):
python -m backend.pipeline.beat_detect output.mp4 --json > beats.json
python -m backend.pipeline.effects_grading output.mp4 out_fx.mp4 --beats-json beats.json \
  --color-preset cold_urban --zoom 0.15 --flash 0.3 --shake 0.5 --rgb-split 0.5
python -m backend.pipeline.upscale out_fx.mp4 out_upscaled.mp4 --scale 2   # optional, langsam auf CPU

# Phase 3 (Multi-Take-Schnitt, config.json mit takes/song_path/beat_times_sec):
python -m backend.pipeline.multitake_cut config.json multitake_cut.mp4 --beat-interval 2 --order-mode fixed
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
    beat_detect.py          # Taktschlaege erkennen (librosa.beat.beat_track)
    effects_grading.py       # Farbpresets + beat-synchrone Effekte (ffmpeg eq/crop/rgbashift/sendcmd)
    multitake_cut.py          # Taktgenauer Schnitt zwischen mehreren synchronisierten Takes
    upscale.py                 # Optionales Real-ESRGAN-Upscaling (PyTorch, CPU oder CUDA)
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

## Wie Phase 3 funktioniert

**Beat-Erkennung** (`beat_detect.py`) laeuft wie Transkription/Subtitles auf
der bereits synchronisierten Output-Tonspur - Taktschlaege liegen also direkt
im Zeitrahmen des fertigen Videos.

**Farbgrading** nutzt ffmpegs `eq`-Filter mit vier Presets (`natural`,
`warm_gold`, `cold_urban`, `high_contrast_mono`). Die **Beat-Effekte** sind
technisch zweigeteilt:
- Flash (Helligkeit) und Shake (Positions-Wackeln) nutzen zeitvariable
  ffmpeg-Filterausdruecke (`eq`/`crop` mit `t`-Referenz), die zu jedem
  erkannten Takt einen kurzen, abklingenden Impuls erzeugen.
- Zoom-Pulse und RGB-Split-Kick nutzen ffmpegs `sendcmd`-Mechanismus, weil
  die dafuer noetigen Filterparameter (`crop`s Breite/Hoehe, `rgbashift`s
  Kanal-Versatz) keine `t`-Ausdruecke unterstuetzen, aber zur Laufzeit per
  Kommando aenderbar sind - der Effekt springt zu jedem Takt kurz auf einen
  Extremwert und wieder zurueck.

**Multi-Take-Schnitt** (`multitake_cut.py`) berechnet zuerst das
gemeinsame Zeitfenster im Song, das ALLE hochgeladenen Takes abdecken (aus
`offset_ms` + Videolaenge jedes Takes), filtert die erkannten Taktschlaege
darauf, bildet Schnittpunkte im gewaehlten Rhythmus (jeder/jeder 2./jeder 4.
Takt) und weist jedem Segment reihum oder zufaellig einen Take zu. Beim
Rendern wird aus jedem Take nur der zum Segment passende Bildausschnitt
(per `trim`) entnommen und aneinandergehaengt (`concat`) - der Ton kommt
komplett unangetastet aus der durchgehenden Songdatei, daher kein Sprung im
Ton trotz Bildschnitten.

**Upscaling** (`upscale.py`) nutzt bewusst die PyTorch-Referenzimplementierung
von Real-ESRGAN (PyPI-Pakete `realesrgan`/`basicsr`) statt eines
ncnn-Vulkan-Builds, damit es auf jeder Maschine per einfachem `pip install`
laeuft (mit oder ohne dedizierte GPU) statt einen plattformspezifischen
Vulkan-Binary-Download zu brauchen. Nutzt automatisch CUDA, falls verfuegbar,
sonst CPU. Das Modell wird beim ersten Aufruf automatisch von GitHub
heruntergeladen (ca. 64 MB). Verarbeitung erfolgt Frame fuer Frame (Video
wird dafuer temporaer in Einzelbilder zerlegt und danach wieder
zusammengesetzt, Originalton bleibt erhalten).

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
- **Takterkennung** ist wie Whisper nicht perfekt - bei sehr leiser oder
  percussion-armer Musik kann sie ungenau sein; wirkt sich auf Beat-Effekte
  und Multi-Take-Schnitt aus.
- **Multi-Take-Schnitt** braucht mindestens 2 erfolgreich synchronisierte
  Takes, die sich im Song ausreichend ueberlappen (dieselbe Songstelle).
- **Upscaling ist optional, langsam (auf reiner CPU ohne GPU koennen es
  leicht mehrere zehn Minuten bis Stunden pro Video werden, nicht nur ein
  paar Minuten) und erfindet keine neuen Bilddetails** - nur eine glaettere
  Hochskalierung als einfache Interpolation. Zusaetzliche Pakete
  (torch/basicsr/realesrgan) muessen separat installiert werden (siehe
  Setup), das Modell wird beim ersten Aufruf automatisch heruntergeladen.

## Nächste Schritte

Alle drei Phasen sind bereit zum Testen mit echtem Material - insbesondere
Multi-Take-Schnitt und Upscaling profitieren von Material mit mehreren Takes
bzw. laengeren Testlaeufen, die im Rahmen dieser Session nicht vollstaendig
durchgefuehrt werden konnten (siehe Testabschnitte in den jeweiligen
Pipeline-Dateien / Commits fuer Details, was bereits validiert wurde).
