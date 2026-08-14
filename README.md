# selfsign — *Sign yourself.*

**Das Netzwerk für Independent Artists**, mit den Werkzeugen dahinter —
vom Handyvideo zum release-fertigen Social-Media-Clip.

> **Gerade den Rechner angemacht?** → `START-AM-PC.md` ist die
> Schritt-für-Schritt-Anleitung: aktualisieren, starten, ausprobieren.
> Kurzfassung: **`update-selfsign.bat` doppelklicken.**
>
> **Logo, Farben, Name:** `MARKE.md`. Dort steht auch, wie du die
> Original-Logodatei mit einem Handgriff eintauschst.

Lokal laufendes Tool, um ein zum Playback mitgerapptes Handyvideo zeitlich
exakt mit der fertig produzierten Songdatei zu synchronisieren und als
9:16-Video (TikTok/Instagram) zu exportieren.

**Wichtig:** Es gibt bewusst kein KI-generiertes Lip-Sync. Die Lippenbewegungen
im Video passen bereits zum Song (Playback lief beim Filmen). Die einzige
Aufgabe ist Audio-Video-Synchronisation: die richtige Stelle im Song finden und
zeitlich exakt über das Video legen.

Aktueller Stand: **Ausbaustufe 1 (Sync)**, **2 (Untertitel)**, **3 (Effekte,
Grading, Upscaling)** und die **Hook-Erkennung** sind fertig und lauffähig.

> Diese Nummern meinen die Ausbaustufen des **Werkzeugs**. Der Fahrplan in
> `PROJEKT-STATUS.md` zählt davon getrennt die Phasen der **Plattform**
> (Phase 1 = Netzwerk, Phase 2 = live stellen). Zwei Zählungen für zwei
> verschiedene Dinge — nicht verwechseln.

## Neu: das Netzwerk für Musiker

Seit August 2026 ist selfsign nicht mehr nur ein Werkzeug für dich allein,
sondern der Anfang einer **Plattform für Independent-Musiker**.

Unter **„Offene Projekte"** in der Seitenleiste kannst du posten, woran du
arbeitest und was dir noch fehlt — „Strophe steht, Hook fehlt", „suche einen
Beat", „brauche jemanden fürs Mixing". Andere Musiker sehen das, können sich
melden und mit dir zusammenarbeiten.

- **Posten:** Titel, was du suchst (Refrain, Beat, Feature, Mixing), Text,
  Genres, BPM und optional eine **Hörprobe bis 30 Sekunden**.
- **Finden:** Der Reiter *Entdecken* zeigt alle offenen Projekte; mit den
  Knöpfen oben filterst du nach dem, was du anbieten kannst. *Folge ich*
  zeigt nur Musiker, denen du folgst.
- **Melden:** „Ich hab Interesse" drücken oder kommentieren. Wer ein Projekt
  gepostet hat, sieht alle Interessenten **mit ihren Profilen** — inklusive
  der Links zu Instagram, Spotify & Co. Darüber läuft der Kontakt.
- **Aufräumen:** Hat sich jemand gefunden, setzt du dein Projekt auf
  **„erledigt"**. Dann verschwindet es aus den offenen Anfragen, und niemand
  antwortet mehr auf etwas Abgeschlossenes.

**Dein Profil** (Seitenleiste → „Mein Profil") ist das, was andere von dir
sehen: Künstlername, Stadt, Genres, Kurzbeschreibung und deine Links.
Deine E-Mail bleibt privat. Trag die Links ein — darüber melden sich Leute
bei dir.

> **Hinweis:** Solange selfsign nur auf deinem Rechner läuft, bist du der
> einzige Nutzer. Das Netzwerk entfaltet seinen Sinn erst, wenn es online
> steht — das ist der nächste große Schritt (siehe `PROJEKT-STATUS.md`,
> Abschnitt „Fahrplan").

Die alte Seite „Offene Projekte" für deine **eigenen** Aufnahmen heißt jetzt
**„Meine Aufnahmen"** — sonst gäbe es den Namen zweimal.

## Anmeldung & Konten

selfsign hat ein Benutzer-System: Login, Registrierung und pro Konto ein
eigenes Dashboard (jeder sieht nur seine eigenen Projekte, Reels und
Hook-Analysen). Es ist bewusst schon „online-tauglich" gebaut (sichere
Passwort-Speicherung, Sitzungen, saubere Datentrennung), läuft aber komplett
lokal auf deinem Rechner.

**Erste Einrichtung (einmalig nach dem Update):**

1. `pip install -r requirements.txt` ausführen — es kommt eine neue
   Bibliothek dazu (`bcrypt`, fürs sichere Passwort-Speichern). **Ohne diesen
   Schritt startet das Backend nicht** (es meldet dann `No module named
   'bcrypt'` im Backend-Fenster).
2. `selfsign-einladung.bat` doppelklicken → es erscheint ein **Einladungscode**.
   Registrierung geht nur mit so einem Code (du vergibst sie als Betreiber).
3. selfsign starten (`start-selfsign.bat`), die Login-Seite öffnet sich →
   „Mit Einladungscode registrieren" → Code, E-Mail, Anzeigename und Passwort
   eingeben. **Das erste Konto wird automatisch Admin und übernimmt alle schon
   vorhandenen Projekte/Reels.**

**Einladungspflicht ein-/ausschalten:** Auf deinem Rechner bleibt sie an —
das ist sicherer, weil sonst jeder, der dein Backend erreicht, sich ein Konto
anlegen könnte. Die spätere öffentliche Plattform setzt die Umgebungsvariable
`HOOKCUT_INVITE_ONLY=0`, dann ist die Registrierung für alle offen und das
Code-Feld verschwindet automatisch aus der Login-Maske.

**Weitere Konten:** am bequemsten direkt in selfsign unter **Einstellungen →
Einladungscodes → „Neuen Code erzeugen"** (nur als Admin sichtbar). Alternativ
weiterhin per `selfsign-einladung.bat`.

**Die Oberfläche hat jetzt echte Seiten** (über die Sidebar, mit eigenen
Adressen wie `/reels`, `/einstellungen`): Dashboard, Hook Generator,
Wochen-Content, Meine fertigen Reels, Offene Projekte und Einstellungen. Unter
**Einstellungen** lassen sich Anzeigename und Passwort ändern; als Admin
zusätzlich Einladungscodes erzeugen und alle Nutzer sehen — dafür ist keine
Kommandozeile mehr nötig. Bereiche, die noch nicht gebaut sind (Analytics,
Datenbanken …), zeigen eine ehrliche „Demnächst"-Seite statt eines toten Links.

**Wochen-Content (Content-Pakete):** Der Baustein gegen das größte Problem
von Indie-Musikern — konsistent posten, ohne auszubrennen. Ein Song + Video →
mehrere fertige Posts auf einen Schlag: selfsign kombiniert automatisch die
besten Hook-Stellen mit den gewählten Looks und Formaten (z.B. 2 Hooks × 3
Styles × 2 Formate = 12 Videos), genug für eine ganze Woche. Jedes Video wird
einzeln gerendert (der Assistent zeigt live „x/y fertig") und ist einzeln
herunterladbar. Der Rechenaufwand vervielfacht sich entsprechend — auf dem
eigenen Rechner ist das gewollt (kostenlos), fürs spätere Hosting bleibt das
Rendern deshalb bewusst lokal (siehe unten).

**Spotify Canvas:** Ein kurzer (3–8 Sekunden), sich wiederholender, **stummer**
9:16-Clip, der auf Spotify das Cover ersetzt — Tracks mit Canvas bekommen
deutlich mehr Streams. Video + Song hochladen, Länge und Look wählen, „auf den
Hook schneiden" → selfsign nimmt den energiereichsten Moment, rendert ihn als
9:16 und entfernt den Ton (Spotify spielt den Song selbst). Danach in **Spotify
for Artists** beim Track „Canvas hinzufügen" und die heruntergeladene Datei
wählen. Menü in der Sidebar: **„Spotify Canvas"**.

**Passwort vergessen:** Solange selfsign nur lokal läuft, gibt es bewusst
keinen „Passwort vergessen"-Link (dafür bräuchte es einen E-Mail-Versand, der
erst mit dem späteren Online-Hosting kommt). Stattdessen am selfsign-Rechner
`selfsign-passwort-reset.bat` doppelklicken und den Anweisungen folgen.

**Wichtig:** Immer über `http://localhost:5173` einloggen (so öffnet auch
`start-selfsign.bat` den Browser), nicht über `127.0.0.1:5173` — die Anmeldung
ist an die Adresse gebunden, über die du dich eingeloggt hast.

Admin-Werkzeuge auf der Kommandozeile (optional):

```bash
python -m backend.admin create-invite [--anzahl N]   # Einladungscode(s)
python -m backend.admin list-invites                  # Codes + Status
python -m backend.admin list-users                    # alle Konten
python -m backend.admin reset-password [email]        # Passwort neu setzen
```

## Premium-Abo (Handbetrieb)

Die Video-Werkzeuge sind das kostenpflichtige Angebot, das Netzwerk bleibt
frei. **Auf deinem eigenen Rechner kostet nichts etwas** — dort ist der
Schalter `HOOKCUT_PREMIUM_REQUIRED` aus, es sind ja deine Werkzeuge und deine
Rechenzeit. Online steht er auf `1`.

**Selbst ansehen, was ein Kunde sieht:** `selfsign-premium-test.bat`
doppelklicken. Startet selfsign einmalig mit den Schaltern, die online gelten —
dein Konto hat kein Abo, du siehst also die Bezahlschranke. Ändert nichts an
deinen Daten; der nächste normale Start ist wieder wie vorher.

Solange kein Zahlungsanbieter angebunden ist (das ist Schritt 5 aus
`PHASE-3-PLAN.md`), vergibst du Abos von Hand: Rechnung schicken, Zahlung
abwarten, freischalten. **`selfsign-abo.bat` doppelklicken** — es erscheint ein
Menü:

1. Alle Abos anzeigen
2. Premium freischalten (1 Monat)
3. Premium freischalten (12 Monate)
4. Premium unbefristet (für dein eigenes Konto und für Tests)
5. Premium beenden

Gut zu wissen:

* **Freischalten verlängert, es überschreibt nicht.** Wer früh nachzahlt,
  verliert seine Resttage nicht — es wird ab dem bisherigen Ende weitergerechnet.
* **Beenden löscht das Abo nicht**, es setzt es auf „abgelaufen". So bleibt
  sichtbar, dass jemand mal Kunde war.
* Ein Monat sind 30 Tage. Bewusst so — „31. Januar plus ein Monat" ist
  mehrdeutig, 30 Tage sind es nie.
* Wer kündigt, behält Premium **bis zum Ende der bezahlten Zeit**. Alles
  andere wäre falsch abgerechnet.
* Sobald ein Zahlungsanbieter da ist, bleiben diese Befehle für Testkonten und
  Kulanzfälle nützlich. Von Hand vergebene Abos stehen in der Liste als
  „von Hand".

**Was Premium sperrt und was nicht:** Bezahlt wird die *Arbeit* — ein Projekt
anlegen, synchronisieren, analysieren, rendern. **Lesen und Herunterladen
bleiben offen.** Wenn ein Abo ausläuft, kommt der Nutzer weiterhin an alles,
was er in der bezahlten Zeit erzeugt hat. Alles andere hieße, ihm bezahlte
Ergebnisse wegzunehmen.

Dasselbe auf der Kommandozeile:

```bash
python -m backend.admin abo-geben [email] --monate 12   # freischalten
python -m backend.admin abo-geben [email] --unbefristet # ohne Enddatum
python -m backend.admin abo-nehmen [email]              # sofort beenden
python -m backend.admin abo-liste                       # alle Abos
```

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

### selfsign-Editor (neuer Produkt-Kern, `editor/`)

Vollwertiger Browser-Video-Editor (Fork von [FreeCut](https://github.com/walterlow/freecut),
MIT — Timeline, ~60 GPU-Effekte, Übergänge, Untertitel mit manueller
Korrektur, 9:16-Export) plus unser Alleinstellungsmerkmal als Toolbar-Button
**„⚡ selfsign"**: Video + Song aus der Media-Library wählen → die lokale
Python-Analyse berechnet Sync-Versatz + beste Hook-Stelle → ein Klick legt
beides fertig synchron und auf den Hook getrimmt auf zwei neue Spuren
(Video stumm, Song an). Danach normal im Editor verfeinern und exportieren.

Start: `start-editor.bat` doppelklicken (startet Analyse-Backend auf Port
8000 + Editor auf Port 5173, öffnet Chrome). Einmalig vorher: im Ordner
`editor/` ein `npm install`. **Nur Chrome/Edge** (WebGPU). Details:
`editor/selfsign-FORK.md`.

### React-Dashboard (primäre Oberfläche, `web/`)

Das designte selfsign-Dashboard (React + Vite + Tailwind, Dark-Theme) liegt
unter `web/`. Es ist **die primäre Produkt-Oberfläche** und spricht das
FastAPI-Backend (`backend/main.py`) über `/api/...` an (im Dev-Server als
Proxy auf `127.0.0.1:8000` konfiguriert). Bequemster Start: einfach
`start-selfsign.bat` doppelklicken (startet Backend + Frontend + Browser).

```bash
cd web
npm install        # einmalig
npm run dev        # startet auf http://127.0.0.1:5173
```

Aktueller Stand: Dashboard (Kennzahlen, Projektliste mit Download,
Hook-Analysen-Panel — alles echte Daten aus dem Backend), Upload-Workflow
(Projekt + Take anlegen, synchronisieren, herunterladen) und Viral Hook
Detector (inkl. Vocal-Separation, sofern `demucs` installiert ist).

Herzstück ist der **„Reel erstellen"-Assistent**: Video + Song hochladen
(optional mit Untertiteln und eingefügtem Songtext), Auto-Sync, optional den
viralsten Teil suchen lassen, Look per Knopfdruck wählen — dazu die Checkbox
**„Beat-Effekte"**: ein Glitch-Puls (Welle + Farbsaum + Glow, FreeCuts
Trigger-Wave mit AudioPulse) zuckt auf jedem erkannten Taktschlag, laute
Schläge stärker als leise (`backend/pipeline/beat_pulse.py` erkennt die
Beats im gewählten Song-Fenster und liefert sie als Puls-Liste an den
unsichtbaren FreeCut-Render). Findet die Beat-Erkennung nichts (z.B. sehr
percussion-arme Musik), wird ohne Puls gerendert statt abzubrechen.

Dazu **Multi-Plattform-Export**: vor der Look-Auswahl lassen sich mehrere
Zielformate anhaken — 9:16 (TikTok/Reels/Shorts, Standard), 4:5 (Insta-Feed),
1:1 (quadratisch) und 16:9 (YouTube). Analyse, Sync, Hook und Untertitel
laufen einmal, danach wird jedes Format einzeln gerendert (Render-Zeit
vervielfacht sich entsprechend; der Assistent zeigt "Format X von Y"). Das
Video fuellt jedes Format automatisch formatfuellend (Cover-Zuschnitt),
Untertitel-Groesse skaliert mit der Bildhoehe. Am Ende gibt es pro Format
einen eigenen Download (`backend/pipeline/platforms.py`, GET `/platforms`).

Der Upload-Workflow bietet zusätzlich:

- **12 Editing-Presets** (`backend/pipeline/presets.py`, GET `/presets`):
  benannte Kombinationen aus Color Grading, beat-synchronen Effekten
  (Zoom-Kick, Flash, Shake, RGB-Split), Finish-Filtern (Vignette, Korn,
  Schärfe, Blur, curves-Looks) und Schnitt-Rhythmus (`beat_stride`:
  Effekt auf jedem 1./2./4. Beat). Presets: Pur, Golden Hour, Urban Ice,
  Noir, Beat Pulse, Flash, Shake, Glitch, VHS Retro, Vintage Film,
  Dreamy, Hard Trap.
- **Automatische Untertitel** (Toggle, Sprache de/en): Whisper-Modell
  "small" (~460 MB einmaliger Download) transkribiert die Audiospur des
  fertigen Videos, Karaoke-ASS wird eingebrannt. Job-Status durchläuft
  `processing -> effects -> subtitles -> done`.

### Multi-Take-Schnitt und Upscaling

Zwei fertige Pipeline-Bausteine, die es noch nicht ins Dashboard
geschafft haben: `backend/pipeline/multitake_cut.py` (taktgenauer
Bildwechsel zwischen mehreren Takes desselben Songabschnitts) und
`backend/pipeline/upscale.py` (Hochskalieren, braucht torch, siehe
Abschnitt „Upscaling"). Beide sind getestet und einsatzbereit; ihre
frühere Bedienoberfläche (ein Gradio-Prototyp aus der Anfangszeit) wurde
im August 2026 entfernt, weil das React-Dashboard sie abgelöst hat und
nichts mehr dorthin führte. Sie warten auf eine Anbindung im Dashboard.

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

# Hook-Erkennung (nur die Songdatei noetig, kein Video). Nutzt automatisch
# Demucs-Vocal-Separation, falls installiert; --no-vocals ueberspringt sie:
python -m backend.pipeline.hook_detect song.wav --target-duration 20 --json
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
    hook_detect.py              # Findet den wahrscheinlichsten Hook-/Refrain-Abschnitt eines Songs
  db.py                  # SQLite: Projekte + Takes
  storage.py              # gemeinsame Verzeichnis-Konventionen (/projects/<id>/...)
  main.py                  # FastAPI-Endpunkte (Werkzeug)
  network.py               # das Netzwerk: Beiträge, Feed, Interesse, Meldungen
  auth.py                  # Konten, Sitzungen, Profile
  betreiber.py             # Impressum-Angaben, an EINER Stelle
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

Weil Whisper bei Rap-Slang und Dialekt zuverlässig Fehler macht, ist der
eingefügte Songtext im Assistenten der bessere Weg: dann gilt **dein Text**
als Wahrheit und die Erkennung liefert nur noch das Timing
(`pipeline/lyrics_align.py`).

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

## Wie die Hook-Erkennung funktioniert

Loest ein Problem, das VOR dem Filmen auftritt: viele Indie-Artists wissen
nicht, welche 15-30 Sekunden ihres eigenen Songs am ehesten als Social-Media-
Hook funktionieren. `hook_detect.py` nutzt eine Standard-MIR-Technik
("Chorus-Detection via Self-Similarity"):

1. `detect_beats()` aus `beat_detect.py` liefert Taktschlaege, daraus werden
   Takt-Grenzen abgeleitet (4 Beats = 1 Takt, 4/4 angenommen).
2. Beat-synchrones Chroma (`librosa.feature.chroma_cqt`, pro Takt gemittelt)
   beschreibt den harmonischen Inhalt jedes Taktes.
3. Eine Self-Similarity-Matrix zwischen allen Takten findet fuer jedes
   Kandidatenfenster (Laenge ~ Zieldauer, an Taktgrenzen ausgerichtet) die
   beste Uebereinstimmung mit einer ANDEREN, nicht ueberlappenden Stelle im
   Song - der Refrain ist typischerweise der Abschnitt, der sich am
   eindeutigsten wiederholt. **Die Wiederholung ist das mit Abstand
   wichtigste Signal fuer einen Hook.**
4. Zusaetzlich wird die relative Lautstaerke (RMS) jedes Fensters ggue. dem
   Songdurchschnitt berechnet - Refrains sind meist energiereicher als
   Strophen.
5. **Position:** Fenster in den ersten 10% des Songs werden mild abgewertet -
   Intros wiederholen sich oft, sind aber selten der Hook.

Wiederholung x Energie x Position ergeben das Ranking; fuers UI wird daraus
zusaetzlich ein **Viral-Score (0-100)** abgeleitet.

Ergebnis: ein Top-Vorschlag plus Alternativen, jeweils mit Zeitbereich und
Teil-Scores - Transparenz-Prinzip wie bei `confidence` in `sync_offset.py`.

### Verworfener Ansatz: Vocal-Menge (gelernte Lektion)

Ein Zwischenstand ("Hook-Score 2.0") hat via [Demucs](https://github.com/facebookresearch/demucs)
(`vocal_separation.py`, bleibt fuer kuenftige Experimente im Repo) die Vocals
vom Beat getrennt und **Vocal-Praesenz + Flow-Dichte** ins Ranking multipliziert
- unter der Annahme "viel Gesang = Hook". Beim ersten Test an echtem Rap-
Material war das **nachweislich schlechter**: Bei Rap wird in den STROPHEN am
dichtesten/schnellsten gerappt, nicht im Hook - die Vocal-Menge zog die
Auswahl also systematisch zu den Strophen. Daher steuern Vocal-Features das
Ranking **nicht mehr** (`vocal_score` wird bei uebergebenem Stem nur noch
informativ berechnet). Der konzeptionell richtige Vocal-Ansatz waere die
*Wiederholung der Vocal-Linie* (Hook-Text/Melodie wiederholt sich, Strophen-
Text nicht) - ein moegliches kuenftiges Feature, das aber sauber an echtem
Material validiert werden muss, bevor es das Ranking beeinflusst.

Im React-Dashboard: Karte "Viral Hook Detector" -> Song hochladen -> die
Analyse laeuft als Hintergrund-Job (`POST /hooks/analyze`, Polling ueber
`GET /hooks/{job_id}`), jeder Kandidat hat eine anhoerbare MP3-Vorschau
(`GET /hooks/{job_id}/preview/{index}`).

**Wichtige Einschraenkung, mit echtem Songmaterial gefunden:** Bei Rap/Hip-Hop
laeuft der Beat oft durchgehend unter Strophe UND Refrain weiter (anders als
z.B. Pop, wo sich oft die Akkorde aendern) - die chroma-basierte Erkennung
ist dadurch weniger trennscharf als bei Genres mit klarem harmonischem
Strophe/Refrain-Kontrast. Score-Werte immer mit anhoeren/gegenpruefen, nicht
blind vertrauen (gleiches Prinzip wie bei der Sync-Konfidenz).

Fuer bereits gefilmte Takes: Da der erkannte Hook-Bereich ausserhalb dessen
liegen kann, was tatsaechlich gefilmt wurde (das Video deckt ja nur einen
Ausschnitt des Songs ab), probiert das Tool automatisch Top-Vorschlag und
Alternativen der Reihe nach durch und nimmt die erste, die vollstaendig im
gefilmten Material liegt - passt keine, wird das transparent gemeldet
(inkl. Hinweis, welchen Songbereich man beim naechsten Take mitfilmen sollte).

## Mit Claude Code am eigenen Rechner weiterarbeiten

Das Projekt ist so vorbereitet, dass ein neuer Claude-Chat sofort weiß, worum
es geht: `CLAUDE.md` wird automatisch gelesen (kurze Orientierung + Regeln),
die Tiefe steht in `PROJEKT-STATUS.md` (Architektur, Fahrplan, Sicherheit,
gelernte Lektionen). Einfach Claude Code im Projektordner starten.

Nützliche erste Sätze für einen neuen Chat:
- „Lies CLAUDE.md und PROJEKT-STATUS.md und sag mir, wo wir stehen."
- „Was ist der nächste Schritt laut Fahrplan?"

**Wenn beim Start eine Fehlermeldung zu `.claude/hooks/session-start.sh`
kommt:** Dieses Skript installiert in der Cloud-Umgebung automatisch die
Abhängigkeiten. Auf Windows wird es nicht gebraucht (das macht
`update-selfsign.bat`) und es beendet sich sofort selbst — falls Windows es
trotzdem nicht ausführen kann, kannst du die Datei `.claude/settings.json`
gefahrlos löschen. Am Projekt ändert sich dadurch nichts.

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
- **Hook-Erkennung ist ein Vorschlag, keine Garantie** - besonders bei
  Genres mit durchgehendem Beat (siehe oben) immer per Ohr gegenpruefen.
  Braucht mindestens ~8 Takte (genuegend erkannte Taktschlaege) im Song.

## Roadmap (All-in-One-App fuer Indie-Musiker)

Naechste sinnvolle Bausteine, in ungefaehrer Prioritaet: Multi-Plattform-
Export-Presets (TikTok/Reels/Shorts/Story gleichzeitig aus einem Take,
baut direkt auf `render_sync.py` auf) → Batch/Multi-Version-Generator
(mehrere Preset-Kombinationen automatisch durchprobieren) → Smart-Link/EPK-
Landingpage (Pre-Save-Links, Social-Links im Look des Videos - erster
Schritt Richtung Distribution/Business-Seite, aber neuer Baustein
ausserhalb der Video-Pipeline mit eigenen Hosting-Ueberlegungen).

Hook-Erkennung, moegliche Pro-Ausbaustufe: das MIT-lizenzierte
Struktur-Modell [mir-aidj/all-in-one](https://github.com/mir-aidj/all-in-one)
labelt Songabschnitte direkt als chorus/verse/bridge (beste bekannte
Open-Source-Qualitaet), braucht aber schwere Dependencies (NATTEN muss auf
Windows aus dem Quellcode gebaut werden, Modelle kommen von HuggingFace) -
als optionales Cloud-/Server-Backend sinnvoll, nicht als lokale
Pflicht-Dependency. Ebenfalls geprueft und verworfen: dennisvdang/
chorus-detection (Lizenz unklar), pychorus (technisch identisch zu unserem
librosa-Ansatz).

## Nächste Schritte

Alle Bausteine sind bereit zum Testen mit echtem Material - insbesondere
Multi-Take-Schnitt und Upscaling profitieren von Material mit mehreren Takes
bzw. laengeren Testlaeufen, die im Rahmen dieser Session nicht vollstaendig
durchgefuehrt werden konnten (siehe Testabschnitte in den jeweiligen
Pipeline-Dateien / Commits fuer Details, was bereits validiert wurde).
