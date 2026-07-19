# HOOKCUT — Projekt-Übergabe / Status

> **Für jeden neuen Coding-Agenten (oder neuen Chat): ZUERST dieses Dokument
> lesen, dann README.md.** Stand: Juli 2026, Branch
> `claude/rap-video-auto-editor-s9xfvt` (alles committed).

## Was ist HOOKCUT?

All-in-One-Tool für Independent-Musiker (Zielgruppe: nicht-technisch, Deutschrap):
Handy-Performance-Video + fertiger Song rein → fertiges, gestyltes,
untertiteltes 9:16-Reel raus. Soll als kommerzielles Produkt verkauft werden.
Besitzer: YngLyric (louis), arbeitet auf Windows, non-technical — Erklärungen
einfach halten, `.bat`-Dateien zum Doppelklicken bereitstellen.

## Kern-Ablauf (der "Reel erstellen"-Assistent, web/)

1. Upload Video + Song, Untertitel ja/nein (+ optional Songtext einfügen)
2. Auto-Sync des ganzen Videos (FFT-Onset-Korrelation)
3. Optional: "Viralsten Teil suchen?" (Hook-Erkennung, Chroma-Self-Similarity)
4. Style per Knopfdruck (10 Styles: clean/vibrant/cinematic/warm/vhs/crt/
   hype/film/neon/noir) + optional Beat-Effekte (Checkbox: Glitch-Puls im
   Takt der Musik, siehe unten)
5. Unsichtbarer Hintergrund-Render → fertiges Reel (Vorschau + Download)

## Architektur (3 Teile)

```
web/      React-Dashboard (Vite, Port 5173, /api-Proxy → 8000)
          → CreateReelWizard.tsx = Haupt-Flow
backend/  Python FastAPI (Port 8000) + pipeline/-Module:
          sync_offset (Onset-Korrelation), hook_detect, transcribe
          (faster-whisper large-v3 auf Demucs-Vocal-Stem), lyrics_align
          (Nutzertext = Wahrheit, KI nur Timing), styles, beat_pulse
          (Beats -> AudioPulse-Frames), freecut_workspace
          (baut FreeCut-Projekt), render_pipeline
editor/   Fork von FreeCut (MIT, © FreeCut — LICENSE MUSS bleiben).
          Browser-Video-Editor, als HOOKCUT gebrandet. Wird als UNSICHTBARE
          Render-Engine benutzt: headless/render.mjs rendert per headless
          Chrome ein von backend generiertes project.json (--quality ultra,
          1080x1920). Hat auch einen ⚡HOOKCUT-Button im Editor (Etappe 3),
          aber Produktrichtung ist der Assistent, nicht der Editor.
```

Datenfluss Render: backend/freecut_workspace.py schreibt
`workspace/projects/<id>/project.json` + `media/<id>/{datei,metadata.json}`
→ `node editor/headless/render.mjs --workspace … --build` → final.mp4.

## Start (Windows, Doppelklick)

- `start-hookcut.bat` — Backend + Dashboard (der normale Weg)
- `start-editor.bat` — Backend + Editor (nur für Editor-Arbeit)
- `update-hookcut.bat` — git pull + Start; `cmd-hier.bat` — CMD im Ordner
- `test-render.bat` — Machbarkeitstest headless-Render (Drag&Drop-Eingabe)
- Einmalig: `pip install -r requirements.txt`, `npm install` in `web/` UND
  `editor/`. Braucht ffmpeg, Node 22+, Chrome (WebGPU!).

## Wichtige gelernte Lektionen (nicht wiederholen!)

1. **Vocal-MENGE ist kein Hook-Signal** (Rap: Strophen sind vocal-dichter als
   Hooks). Hook-Ranking = Wiederholung × Energie × Position. vocal_score nur
   informativ. Demucs bleibt für Transkription wertvoll.
2. **Untertitel:** Gesamtmix transkribieren = Katastrophe. Richtig: Demucs-
   Vocal-Stem + Whisper large-v3 + language="de" + lyrics_align (eingefügter
   Songtext wird Wort für Wort angezeigt, KI liefert nur Timing).
3. **offset_ms-Konvention** (sync_offset): positiv = Video startet mitten im
   Song. Sync-Invariante: Video-Frame 0 und Song-Frame 0 zeigen dieselbe
   Song-Zeit. Hook-Clamp: Kandidat darf ≤1s übers Video ragen (wird gekürzt).
4. **FreeCut-Interna:** sourceStart/End in QUELL-FPS-Frames. Effekte =
   `effects[{id,enabled,effect:{type:'gpu-effect',gpuEffectType,params}}]`
   — Param-Keys IMMER aus editor/src/infrastructure/gpu-effects/effects/*.ts
   verifizieren, nie raten. Untertitel = ein SubtitleSegmentItem mit cues[].
   Cover-Transform (transform.width/height) macht Video formatfüllend.
   Beat-Effekte: `audioPulse` am Effekt-Eintrag eines gpu-trigger-wave
   (sparsame beats[{frame,amplitude}] + Envelope-Params, prozedural pro Frame
   ausgewertet — Format aus editor/src/features/keyframes/utils/
   trigger-wave-motion-layer.ts, createAudioPulseModulation). Alternativ gibt
   es generische `timeline.keyframes` (property
   `effect:<gpuType>:<effectId>:<paramKey>`), fuer den Puls aber nicht noetig.
5. **Windows-Nutzer-Realität:** PowerShell blockt npm.ps1 (→ CMD oder
   npm.cmd), `Als Pfad kopieren` liefert Anführungszeichen mit, localhost ≠
   127.0.0.1 (Vite bindet localhost). Fehlermeldungen in api.ts sind bewusst
   deutsch/verständlich übersetzt.
6. **Sandbox-Grenzen (Claude Code Cloud):** kein WebGPU/Chrome-Render, kein
   HuggingFace/fbaipublicfiles-Download (Demucs/Whisper-Modelle laden nur
   beim Nutzer), editor/ npm install scheitert teils am Egress. Backend ist
   dort voll testbar, Editor/Render nur beim Nutzer.

## Zustand / Qualität

- 80+ pytest-Tests grün (tests/). Web-Build grün. Sync + Hook mit echten
  Dateien validiert (offset ~5039ms, conf 0.88 beim Testmaterial).
- Beat-Effekte (beat_pulse.py + audioPulse in freecut_workspace.py) sind
  implementiert und getestet, aber noch NICHT vom Nutzer im echten Render
  bestätigt (Sandbox kann kein Chrome-Rendern).
- Vom Nutzer end-to-end bestätigt: Sync, Hook-Flow, Styles-Render,
  9:16-Cover, Untertitel unten + exakte Lyrics.
- Legacy, funktioniert aber: Gradio-UI (frontend/app.py), alte ffmpeg-
  Effekte (effects_grading.py — durch FreeCut-Styles überholt), UploadModal
  im web/ (durch Wizard ersetzt, Datei existiert noch).

## Offene / nächste Themen (Stand der Diskussion)

1. **Beat-Effekte beim Nutzer end-to-end bestätigen** (Backend + Tests grün,
   Chrome-Render geht nur beim Nutzer). Danach ggf. Intensität/Stride
   feinjustieren (beat_pulse.py hat stride=2/4 schon, UI bewusst nur Toggle).
2. Style-Intensitäten nach Nutzer-Feedback feinjustieren.
3. Hosting/"online verfügbar" (vertagt): Empfehlung Hybrid — billige
   Python-Analyse-API + Browser-Render beim Nutzer.
4. i18n der neuen Editor-Strings (TODO in editor/HOOKCUT-FORK.md).
5. Roadmap-Ideen: Multi-Plattform-Presets, all-in-one-Strukturmodell als
   Pro-Backend (NATTEN/HF-Blocker beachten), Wort-Karaoke-Highlight.

## Stil der Zusammenarbeit mit dem Besitzer

Deutsch, kurz, ehrlich (Grenzen offen benennen), keine Fachbegriffe ohne
Erklärung, alles per `.bat` doppelklickbar machen, jeden Schritt selbst
testen soweit möglich und den Rest als klaren Nutzer-Test formulieren
("git pull → neu starten → X prüfen"). Commits + Push nach jedem Schritt.
