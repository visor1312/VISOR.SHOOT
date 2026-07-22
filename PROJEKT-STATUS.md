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
   Takt der Musik, siehe unten) + Zielformate anhaken (Multi-Plattform:
   reel 9:16 / feed 4:5 / square 1:1 / wide 16:9, pipeline/platforms.py)
5. Unsichtbarer Hintergrund-Render pro Format → fertiges Reel (Vorschau +
   Download je Format; outputs_json in edit_jobs haelt den Fortschritt)

## Architektur (3 Teile)

```
web/      React-Dashboard (Vite, Port 5173, /api-Proxy → 8000)
          → CreateReelWizard.tsx = Haupt-Flow (Overlay, aus AppShell geoeffnet)
          → AuthScreen.tsx = Login/Registrierung, App.tsx = Auth-Weiche
          → react-router: main.tsx BrowserRouter, App.tsx rendert eingeloggt
            die Routen in components/AppShell.tsx (Sidebar + <Outlet/>,
            Kontext in components/app-context.ts: user/setUser/openWizard).
            Seiten in pages/: DashboardPage, HookPage, CanvasPage, ReelsPage, ProjektePage,
            EinstellungenPage (Konto + Admin), PacksPage + PackDetailPage
            (Wochen-Content), ComingSoonPage. Neue Seite ⇒ Route in App.tsx +
            NavLink in Sidebar.tsx. CreatePackWizard.tsx = Wochen-Content-Dialog.
backend/  Python FastAPI (Port 8000) + auth.py (Benutzer-System) + pipeline/-Module:
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

## Benutzer-System (Login/Registrierung, seit Juli 2026)

- **backend/auth.py**: bcrypt-Passwort-Hashing (72-Byte-Grenze wird VOR
  hashpw/checkpw validiert!), Server-Side-Sessions (Token nur als SHA-256-Hash
  in der DB, httpOnly-Cookie `hookcut_session`, sliding 30 Tage), Login-Lockout
  (5 Fehlversuche → 15 min, DB-Tabelle), FastAPI-Dependency `get_current_user`,
  Router `/auth/{register,login,logout,me}`. Registrierung NUR mit
  Einladungscode.
- **Ownership-Regel (WICHTIG):** jede Daten-Route hat
  `Depends(auth.get_current_user)`; Listen filtern `WHERE user_id = ?`,
  Einzel-/Download-Routen werfen über den `_own()`-Helper **404** bei fremden
  Ressourcen (kein 403 = kein Existenz-Orakel). Nur `/styles`, `/platforms`,
  `/presets` sind öffentlich. Neue Daten-Route ⇒ IMMER scopen, sonst Datenleck.
- **Erstes Konto = Admin** und übernimmt per `claim_orphan_rows` alle Altdaten
  (user_id NULL). Danach gibt es keine besitzerlosen Zeilen mehr.
- **DB:** neue Tabellen users/sessions/invite_codes/login_attempts + user_id
  auf projects/hook_jobs/analyze_jobs/edit_jobs (Mini-Migration). `create_*`
  nehmen user_id; `update_*`-Allow-Lists enthalten user_id NICHT (unveränderlich).
- **backend/admin.py** (+ hookcut-einladung.bat / hookcut-passwort-reset.bat):
  create-invite / list-invites / list-users / reset-password.
- **Konto/Admin im Browser** (Einstellungen-Seite): `PATCH /auth/me`
  (Anzeigename), `POST /auth/change-password` (prueft altes PW, rotiert ALLE
  Sessions, stellt fuer den aktuellen Browser eine frische aus), sowie der
  `admin_router` (Dependency `get_admin_user`, 403 fuer Nicht-Admins):
  `GET/POST /admin/invites`, `GET /admin/users` (nie mit password_hash).
  Damit ist die `.bat` fuer den Alltag optional (bleibt Notfallweg).
- **Tests:** HOOKCUT_DB-Env zeigt auf eine Wegwerf-DB (conftest.py setzt sie
  VOR dem ersten backend-Import) — API-Tests schreiben NIE in die echte
  state.db. Ohne das würde der erste Test-User per Backfill die Altdaten erben.
- **Fürs spätere Hosting:** `HOOKCUT_SECURE_COOKIES=1` setzen (Secure-Cookie
  nur über HTTPS). CORS-Origins in main.py erweitern. E-Mail-Verifikation +
  echter Passwort-Reset (Mail) sind dann die nächsten Bausteine.
- **Sicherheits-Review (Juli 2026):** Timing-Seitenkanal beim Login gefixt
  (bcrypt laeuft immer, auch bei unbekannter E-Mail → `_DUMMY_HASH`). SQL
  durchgehend parametrisiert (die f-string-Tabellennamen kommen aus festen
  Tupeln/Allow-Lists, nie aus Nutzereingaben). Bewusst akzeptiert fuers
  lokale Tool (fuers Hosting im Blick behalten): Account-Lockout ist pro
  E-Mail → jemand mit deiner E-Mail kann dich 15 min aussperren (DoS);
  Register-„E-Mail vergeben"-409 ist ein Enumerations-Hinweis, aber durch
  den Einladungscode-Zwang gedeckelt; TOCTOU-Rennen bei Register/Invite sind
  lokal vernachlaessigbar.
- **Bekannte Grenzen:** Download-Links (`<a href>`) zeigen bei abgelaufener
  Sitzung rohes 401-JSON statt Login-Maske. Das Gradio-Legacy (frontend/app.py)
  umgeht die HTTP-Auth (ruft die Pipeline direkt) — bleibt deprecated/lokal.

## Wochen-Content / Content-Packs (das erste „warum 10€/Monat"-Feature)

Recherche (2026): Das #1-Problem der Zielgruppe ist konsistent posten ohne
Burnout (3–5 Kurzvideos/Woche über mehrere Plattformen). Antwort: aus EINEM
Song/Video viele fertige Posts auf einen Schlag.

- **pipeline/content_pack.py** (rein + testbar): `select_hook_windows`
  (mehrere Hook-Fenster, die mit 1s-Clamp ins gefilmte Video passen, in
  Ranking-Reihenfolge) + `build_item_matrix` (kartesisch Hook × Style × Format,
  gedeckelt auf `MAX_PACK_ITEMS=24`).
- **DB:** `content_packs` + `pack_items` (user-gescoped). Analyse (Sync + Hook +
  optional Untertitel) läuft EINMAL in `_run_content_pack`; jedes pack_item ist
  ein einzelner Render-Auftrag. Ein kaputtes Item stoppt nicht das Paket.
- **Routen:** `POST /packs`, `GET /packs`, `GET /packs/{id}`,
  `GET /packs/{id}/items/{idx}/download` (Ownership-404). Frontend: PacksPage +
  PackDetailPage (pollt live), CreatePackWizard.
- Wiederverwendet `build_workspace` + `run_headless_render` + die
  Untertitel-Pipeline aus dem Edit-Flow, ohne diesen zu ändern.

## Spotify Canvas (3–8s stummer 9:16-Loop, +Streams)

- **pipeline/content_pack.py**: `canvas_window` (schneidet ein `duration_sec`-
  Fenster am Hook, das ins gefilmte Video passt; schiebt bei Überlauf nach
  vorn; None wenn Video < 3s) + `clamp_canvas_duration` (3–8s).
- **DB:** Tabelle `canvas_jobs` (user-gescoped). `_run_canvas_job` (main.py):
  Analyse → Fenster am Hook → `build_workspace` 1080×1920 gestylt → render →
  **Ton per ffmpeg `-an` strippen** (Canvas ist stumm; isoliert, ohne
  `build_workspace` anzufassen).
- **Routen:** `POST /canvas`, `GET /canvas`, `GET /canvas/{id}`,
  `GET /canvas/{id}/download` (Ownership-404, Dauer server-seitig geklemmt).
  Frontend: CanvasPage (loopende stumme Vorschau + Spotify-Upload-Hinweis) +
  CreateCanvasWizard.

## Hybrid-Hosting-Fundament (Richtung Online, ohne teure Cloud-GPU)

Entscheidung: Konten/Daten/Seiten kommen auf einen günstigen Server, das
schwere Video-Rendern bleibt beim Nutzer (lokale App als Render-Companion) —
Server-GPU-Render wäre fürs 10€-Preismodell zu teuer.

- **backend/config.py**: alles über Env — `HOOKCUT_CORS_ORIGINS` (Domains),
  `HOOKCUT_SECURE_COOKIES`, `HOOKCUT_LOCAL_RENDER` (Hybrid-Weiche).
- **main.py**: CORS aus config; `lifespan` statt `on_event`; `GET /health`.
  **db.py**: SQLite WAL-Modus (Nebenläufigkeit).
- **Render-Job-Vertrag** (für den späteren lokalen Render-Agenten):
  `GET /render/pending`, `POST /render/{item}/claim` (pending→rendering, 409
  wenn vergeben), `POST /render/{item}/result` (fertiges MP4 hochladen).
  Lokal (`HOOKCUT_LOCAL_RENDER=1`, Default) rendert der In-Process-Worker in
  `_run_content_pack`; beim Hosting (`=0`) bleiben die Items offen und der
  Agent zieht sie über diesen Vertrag ab.

## Roadmap fürs Bezahl-Release (bewusst DANACH, je ein eigener Block)

1. **Echtes Deployment** (Server + Domain) + **lokaler Render-Agent**
   (Companion, der pending-Items zieht, lokal rendert, das MP4 per
   `/render/{item}/result` hochlädt). Erst dann ist der Hybrid-Kreis geschlossen.
2. **Abrechnung** (Stripe, 10€/Monat) — ergibt erst mit Server Sinn.
3. **„Bleibt-online"-Features** Smart Link / Release-Landingpage + EPK
   (Pressekit) — die klassischen Abo-Gründe.
   (Spotify Canvas ist umgesetzt, siehe oben.)

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
   ACHTUNG (Nutzer-Test Juli 2026, "zuckt durchgehend"): `scanlineMix` im
   gpu-trigger-wave-Shader ist NICHT an strength gekoppelt - jeder Wert > 0
   flackert dauerhaft, fuer Puls-Effekte auf 0 lassen. Und: librosa erkennt
   bei Rap (Hi-Hats) gern das doppelte Tempo -> beat_pulse.py duennt Pulse
   automatisch auf >= 0.42s Abstand aus (MIN_PULSE_SPACING_SEC).
5. **Windows-Nutzer-Realität:** PowerShell blockt npm.ps1 (→ CMD oder
   npm.cmd), `Als Pfad kopieren` liefert Anführungszeichen mit, localhost ≠
   127.0.0.1 (Vite bindet localhost). Fehlermeldungen in api.ts sind bewusst
   deutsch/verständlich übersetzt.
6. **Sandbox-Grenzen (Claude Code Cloud):** kein WebGPU/Chrome-Render, kein
   HuggingFace/fbaipublicfiles-Download (Demucs/Whisper-Modelle laden nur
   beim Nutzer), editor/ npm install scheitert teils am Egress. Backend ist
   dort voll testbar, Editor/Render nur beim Nutzer.

## Zustand / Qualität

- 156 pytest-Tests grün (tests/). Web-Build + oxlint grün. Sync + Hook mit
  echten Dateien validiert (offset ~5039ms, conf 0.88 beim Testmaterial).
  Auth- und Navigations-Flows zusätzlich per Playwright im echten Browser
  (gegen den Vite-Proxy) verifiziert.
- Beat-Effekte (beat_pulse.py + audioPulse in freecut_workspace.py) sind
  implementiert und getestet, aber noch NICHT vom Nutzer im echten Render
  bestätigt (Sandbox kann kein Chrome-Rendern).
- Vom Nutzer end-to-end bestätigt: Sync, Hook-Flow, Styles-Render,
  9:16-Cover, Untertitel unten + exakte Lyrics.
- Legacy, funktioniert aber: Gradio-UI (frontend/app.py), alte ffmpeg-
  Effekte (effects_grading.py — durch FreeCut-Styles überholt, aber von
  Gradio + Tests noch genutzt). UploadModal im web/ wurde entfernt (durch
  Wizard ersetzt); die alten REST-Endpunkte (/projects POST, /takes, /sync,
  /presets) bleiben fürs Gradio-Legacy + dokumentierte API bestehen, das
  Dashboard nutzt weiterhin GET /projects + Take-Download.

## Offene / nächste Themen (Stand der Diskussion)

1. **Beat-Effekte beim Nutzer end-to-end bestätigen** (Backend + Tests grün,
   Chrome-Render geht nur beim Nutzer). Danach ggf. Intensität/Stride
   feinjustieren (beat_pulse.py hat stride=2/4 schon, UI bewusst nur Toggle).
2. Style-Intensitäten nach Nutzer-Feedback feinjustieren.
3. Hosting: Fundament steht (config/lifespan/WAL/health + Render-Vertrag,
   siehe oben). Nächster Block: echtes Deployment + lokaler Render-Agent +
   Stripe + Smart Link/EPK (Details im Roadmap-Abschnitt oben).
4. i18n der neuen Editor-Strings (TODO in editor/HOOKCUT-FORK.md).
5. Roadmap-Ideen: all-in-one-Strukturmodell als Pro-Backend (NATTEN/HF-Blocker
   beachten), Wort-Karaoke-Highlight. (Batch/Wochen-Content und Spotify Canvas
   sind umgesetzt.)
   (Multi-Plattform-Presets sind umgesetzt, warten auf Nutzer-Test.)

## Stil der Zusammenarbeit mit dem Besitzer

Deutsch, kurz, ehrlich (Grenzen offen benennen), keine Fachbegriffe ohne
Erklärung, alles per `.bat` doppelklickbar machen, jeden Schritt selbst
testen soweit möglich und den Rest als klaren Nutzer-Test formulieren
("git pull → neu starten → X prüfen"). Commits + Push nach jedem Schritt.
