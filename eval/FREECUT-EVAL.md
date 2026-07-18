# FreeCut-Evaluation für HOOKCUT — Ergebnis (Teil A)

**Frage:** Kann [walterlow/freecut](https://github.com/walterlow/freecut) (MIT)
der Video-Editor-Baustein für HOOKCUT werden — und lässt sich unsere
automatische Analyse programmatisch in eine FreeCut-Timeline füttern?

**Kurzantwort: JA (klarer GO für die technische Machbarkeit).**
Die endgültige Freigabe hängt an Teil B (Editor-Gefühl + echter Export auf
einem Chrome-Rechner — das kann die Sandbox nicht testen).

---

## Was Teil A (im Code) bewiesen hat

### 1. FreeCut hat einen programmatischen Zugang — genau unseren Hybrid-Seam
- **Datei-basiertes Projektformat**: eine `project.json` + `media/<id>/<datei>`
  in einem Workspace-Ordner. Kein proprietäres Binärformat.
- **Headless Edit-CLI** (`headless/edit.mjs`, `src/headless/edit.ts`): nimmt ein
  Projekt + eine Liste von Edit-Ops (`addItem`, `trim`, `addEffect`,
  `addKeyframe`, `addTransition` …), fährt die **echte** Timeline-Logik und
  schreibt das Projekt zurück.
- **Headless Render-CLI** (`headless/render.mjs`, inkl. `Dockerfile`): rendert
  ein Projekt (oder einen Ausschnitt) per headless Chrome zu MP4/WebM —
  `--resolution 1080x1920` erzeugt **9:16 direkt**.

### 2. Das Datenmodell passt fast 1:1 auf unsere Analyse-Ausgabe
| HOOKCUT (Python, heute schon da) | FreeCut-Projekt |
|---|---|
| `compute_offset()` → `offset_ms` | Startversatz der Song-Tonspur |
| `detect_hook()` → `start/end_sec` | Trim von Video + Ton auf den Hook |
| Untertitel-Cues (`subtitles.py`) | ein `SubtitleSegmentItem` mit `cues[]` |
| 9:16 | `metadata.width/height` (1080×1920) |
| Beat-Zeiten (`beat_detect.py`) | Keyframes/Effekte an Beat-Frames |

### 3. Adapter-Prototyp funktioniert
`eval/freecut_adapter.py` erzeugt aus einer Beispiel-Analyse ein
**strukturell gültiges** `project.json`: 9:16, Video-Spur stumm, Song-Spur
hörbar (um `offset` verschoben, auf Hook getrimmt), Untertitel-Segment mit
Cues relativ zum Clip-Start. Reine Datenabbildung, keine FreeCut-Änderung.

---

## Lücken-Liste (gegen unsere heutige ffmpeg-Pipeline)

| HOOKCUT-Funktion | In FreeCut? | Aufwand für Hybrid |
|---|---|---|
| 9:16-Export | ✅ nativ (`--resolution`) | keiner |
| Song über stummes Video | ✅ Mehrspur + `muted`/`volume` | keiner |
| Untertitel einbrennen | ✅ nativ (`SubtitleSegmentItem`, burn-in) | keiner |
| Auto-Sync-Versatz setzen | ✅ über `from`/`trim` im Projekt | Adapter (Prototyp da) |
| Hook-Trim | ✅ über `trim`/`duration` | Adapter (Prototyp da) |
| Beat-synchrone Effekte (Zoom/Flash/Shake/RGB) | ⚠️ Effekte+Keyframes vorhanden, aber unsere Beat-Timings müssten als Keyframes gemappt werden | mittel (Folgeaufgabe) |
| Multi-Take-Schnitt | ✅ mehrere Clips/Split | klein–mittel |
| Upscaling (Real-ESRGAN) | ❌ nicht enthalten | bleibt serverseitig / optional |

---

## Vorbehalte (fließen in die Produktentscheidung ein)
- **Nur Chromium-Browser** (Chrome/Edge 113+, Brave/Arc) — kein Safari/Firefox.
  Für eine Musiker-Zielgruppe (viel iPhone/Safari) eine echte Einschränkung,
  wenn HOOKCUT im Browser laufen soll.
- **„Open source, not open contribution"**: MIT-Lizenz erlaubt Fork/kommerzielle
  Nutzung, aber wir müssten einen eigenen Fork pflegen und Upstream-Updates
  manuell nachziehen.
- **HuggingFace-Modelle** (FreeCuts eigene Transkription/TTS) laden beim ersten
  Nutzen nach; unsere Python-Whisper-Transkription bleibt die Alternative.
- **Sandbox-Grenzen**: `npm install` scheiterte hier an einem Netzwerk-Egress-
  Limit, und WebGPU/WebCodecs + der Google-Chrome-Kanal fehlen — deshalb kein
  echter Build/Render in der Sandbox. Das ist erwartet und Teil B.

---

## Hosting-/Kosten-Einordnung (Bezug zur „online verfügbar"-Frage)
FreeCut ermöglicht **zwei** Betriebsmodelle — wir sind nicht festgelegt:
1. **Browser-Render** (auf dem Rechner des Nutzers): Hosting = nur statische
   Dateien → **sehr günstig**, löst das Serverkosten-Problem weitgehend.
2. **Headless-Server-Render** (Dockerfile vorhanden): volle Automatik ohne
   Nutzer-Interaktion, braucht aber einen GPU-fähigen Server → teurer.

Empfohlener Zielaufbau: unsere kleine Python-Analyse-API (billig, nur Zahlen)
+ FreeCut-Browser-Render für die Bearbeitung → Alleinstellung bleibt, Kosten
niedrig.

---

## Empfehlung
**GO für einen Integrations-Prototyp — nach erfolgreichem Teil B.**
Die technische Machbarkeit ist bewiesen; offen ist nur, ob sich der Editor gut
anfühlt und der Export auf einem echten Rechner sauber läuft.

**Nächster Schritt = Teil B (auf deinem Windows-PC, Chrome):** siehe
`eval/TEIL-B-ANLEITUNG.md`. Drei Kaufentscheider prüfen:
1. Fühlt sich der Editor flüssig/gut an?
2. Klappt ein 9:16-MP4-Export mit eingebrannten Untertiteln?
3. Kann man eine zweite Tonspur (Song) über das Video legen?

Fällt Teil B positiv aus → Folgeplan: HOOKCUT-Analyse → `freecut_adapter.py`
→ FreeCut-Projekt automatisch erzeugen und im Browser öffnen.
