# HOOKCUT — Projekt-Übergabe / Status

> **Für jeden neuen Coding-Agenten (oder neuen Chat): ZUERST `CLAUDE.md`
> lesen (kurz), dann dieses Dokument (tief), dann README.md (Bedienung).**
> Stand: **August 2026**, Branch `claude/rap-video-auto-editor-s9xfvt`
> (alles committed und gepusht).

## Was ist HOOKCUT?

**Zwei Dinge in einem Projekt:**

1. **Das Werkzeug** (fertig, in Benutzung): Handy-Performance-Video + fertiger
   Song rein → fertiges, gestyltes, untertiteltes 9:16-Reel raus.
2. **Das Netzwerk** (neu, seit August 2026): ein soziales Netzwerk für
   Independent-Musiker mit „offenen Projekten" („mir fehlt noch ein Refrain").
   Kostenlos — das Werkzeug aus 1. wird später das Premium-Angebot
   (~10 €/Monat). Endziel: Apps für iOS und Android.

Zielgruppe: nicht-technisch, Deutschrap. Besitzer: YngLyric (louis), arbeitet
auf Windows, non-technical — Erklärungen einfach halten, `.bat`-Dateien zum
Doppelklicken bereitstellen.

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
backend/  Python FastAPI (Port 8000). Bewusst nach Produkt getrennt:
          main.py    = das WERKZEUG (Sync, Hook, Styles, Packs, Canvas)
          network.py = das NETZWERK (Beitraege, Feed, Interesse, Kommentare)
          auth.py    = Benutzer-System + Profile
          Beide Router haengen in main.py per include_router.
          Dazu die pipeline/-Module:
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
  Router `/auth/{register,login,logout,me,config}`.
- **Registrierung: zwei Modi** über `config.INVITE_ONLY` (`HOOKCUT_INVITE_ONLY`).
  Standard `1` = nur mit Einladungscode (sichere Voreinstellung fürs lokale
  Werkzeug). Die offene Musiker-Plattform setzt `0`; dann wird ein
  mitgeschickter Code ignoriert und **nicht** verbraucht. `GET /auth/config`
  (öffentlich) sagt der Login-Maske, ob sie das Code-Feld zeigen muss.
- **Musiker-Profile** (`profiles`-Tabelle, `profiles_router`): die ÖFFENTLICHE
  Seite eines Kontos, bewusst getrennt von `users` (dort liegen E-Mail und
  Passwort-Hash). Felder: `handle` (eindeutiges @Kürzel für Profil-Adressen),
  artist_name, bio, city, genres, links_json, avatar_path.
  `GET/PATCH /profiles/me`, `GET /profiles/{handle}`.
  - Der **handle** wird bei der Registrierung aus dem Anzeigenamen erzeugt
    (`auth.make_handle`: Umlaute ausgeschrieben, nur a-z0-9, bei Kollision
    durchnummeriert) und ist über `update_profile` **nicht** änderbar — er
    steckt in Profil-Adressen, ein stiller Wechsel würde fremde Links brechen.
  - `auth.ensure_profile` zieht Profile für Altkonten beim ersten Zugriff nach
    (statt einer Migration).
  - **Links werden geprüft** (`auth.clean_link`): nur http(s), feste Liste
    erlaubter Arten. Ohne das könnte jemand einen `javascript:`-Link im Profil
    hinterlegen, den andere anklicken.

## Das Netzwerk (Phase 1, August 2026)

Aus dem Einzelplatz-Werkzeug wird eine Plattform für Musiker: „offene
Projekte" posten („mir fehlt noch ein Refrain"), im Feed finden, folgen,
Interesse zeigen, kommentieren.

- **Tabellen:** `posts` (+ `post_categories` als eigene indizierte Tabelle,
  weil danach GEFILTERT wird — in einer Textspalte träfe „beat" auch
  „boombeat" und kein Index griffe), `follows`, `post_interests`, `comments`.
- **`open_state`** (offen/erledigt) ist bewusst getrennt vom Moderations-
  `status`. Ohne den Erledigt-Schalter füllt sich der Feed mit Anfragen, auf
  die längst geantwortet wurde.
- **Feed:** `GET /feed/discover` (alle, mit Kategorie-/Genre-Filter) ist die
  Startansicht — wer neu ist, folgt niemandem und sähe sonst nichts.
  `GET /feed` zeigt eigene + gefolgte. Autorenprofil kommt per JOIN mit,
  Kategorien und Zähler werden für die ganze Liste in je einer Abfrage
  geholt (kein N+1).
- **Kontaktweg statt Direktnachrichten:** `GET /posts/{id}/interest` liefert
  die Interessenten MIT Profil; dort liegen die Links zu Instagram, Spotify
  & Co. Der Autor erreicht die Leute also über deren eigene Kanäle. Spart
  ein komplettes Nachrichtensystem.
- **Upload-Grenzen für Hörproben:** 8 MB (30 s WAV ≈ 5,3 MB), 30 s,
  Endungs-Positivliste, geprüft über `_probe_duration_sec`. Scheitert
  ffprobe → 422 (Nutzereingabe), nicht 500. Bei Fehlschlag werden Datei UND
  Beitragszeile zurückgebaut.
- **Spam-Bremse:** 10 Beiträge/Stunde. **Notaus:**
  `POST /admin/posts/{id}/hide` (nur Admin).
- **Melden (seit Phase 2, Schritt 5):** Tabelle `reports`, `POST /reports`
  (Beitrag oder Kommentar, fester Grund + freie Notiz, 20/Stunde),
  `GET /admin/reports` als Arbeitsliste und
  `POST /admin/reports/{id}/handle` (`ausblenden` / `behalten`). Eine
  Entscheidung schließt **alle** offenen Meldungen zu diesem Inhalt —
  melden drei Leute denselben Beitrag, ist das eine Entscheidung.
  `UNIQUE(target_type, target_id, reporter_id)` verhindert Melde-Spam; der
  zweite Klick sieht für den Nutzer trotzdem aus wie der erste.
  **Wichtig dabei:** Ist die frühere Meldung schon *entschieden*, wird sie
  bei einer neuen Meldung wieder geöffnet (`db.create_report`). Ohne das
  könnte dieselbe Person denselben Inhalt nie wieder melden — ein Beitrag
  lässt sich nach einer Entscheidung aber ändern, und die Meldung wäre
  stillschweigend verschwunden, obwohl die Oberfläche „angekommen" sagt.
- **Konto löschen ist für den letzten Admin gesperrt**, solange es noch
  andere Konten gibt (409): sonst bliebe eine Plattform ohne Verwaltung
  zurück, in der niemand mehr Meldungen bearbeiten kann.
- **Konto löschen:** `DELETE /auth/me` (Passwort nötig) räumt Konto, Profil,
  Beiträge samt Hörproben, Kommentare, Interesse und Folgen weg —
  `db.delete_user_completely`, gibt die Beitrags-IDs zurück, damit `auth.py`
  auch die Dateien löschen kann.
- **Frontend** (alles unter `web/src/`): `pages/FeedPage.tsx` (Reiter
  Entdecken/Folge ich + Filter), `pages/PostDetailPage.tsx`,
  `pages/ProfilAnsichtPage.tsx` (Route `/musiker/:handle`),
  `components/CreatePostWizard.tsx`, `components/BeitragsKarte.tsx`.
  Routen stehen in `web/src/App.tsx`, Navigation in
  `web/src/components/Sidebar.tsx`.
  Die alte Seite „Offene Projekte" (eigene Aufnahmen) heißt jetzt
  **„Meine Aufnahmen"** — sonst gäbe es den Namen zweimal.

- **Ownership-Regel (WICHTIG):** jede Daten-Route hat
  `Depends(auth.get_current_user)`; Listen filtern `WHERE user_id = ?`,
  Einzel-/Download-Routen werfen über den `_own()`-Helper **404** bei fremden
  Ressourcen (kein 403 = kein Existenz-Orakel). Nur `/styles`, `/platforms`,
  `/presets`, `/post-categories`, `/health`, `/auth/config` sind öffentlich.
  Neue Daten-Route ⇒ IMMER scopen, sonst Datenleck.
- **ACHTUNG, zweite Regel seit dem Netzwerk:** für SOZIALE Inhalte
  (Beiträge, Kommentare) gilt `_own_public()` statt `_own()` — lesen darf
  jedes angemeldete Mitglied (sonst gäbe es keinen Feed), ändern/löschen nur
  der Autor, und zwar mit **403**. Bei einem Beitrag im Feed ist die Existenz
  ohnehin öffentlich; ein 404 wäre dort schlicht gelogen. Neue private Route
  ⇒ `_own()`, neue soziale Route ⇒ `_own_public()`.
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
- **Bekannte Grenze:** Download-Links (`<a href>`) zeigen bei abgelaufener
  Sitzung rohes 401-JSON statt Login-Maske.
  *(Die alte Gradio-Oberfläche umging die HTTP-Auth komplett, indem sie die
  Pipeline direkt aufrief. Sie wurde im August 2026 entfernt — damit ist
  diese Lücke zu.)*

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

## Fahrplan (die große Linie, mit dem Besitzer abgestimmt)

Ziel: aus dem Werkzeug wird eine **Plattform für Independent-Musiker** —
kostenloses Netzwerk mit offenen Projekten, darauf ein Premium-Abo
(~10 €/Monat) für die Render-Werkzeuge. Web zuerst, Apps später.

**Rahmenbedingungen, die den ganzen Plan formen:**
- **Budget 0–20 €/Monat.** Investor erst, wenn es läuft und überzeugt.
  Alles muss auf Gratis-Stufen laufen (Domain ~1 €/Monat, Server/DB/Speicher
  gratis, E-Mail-Versand gratis bis einige tausend/Monat).
- **Rendern bleibt auf PCs.** Video-Render auf Servern braucht GPU-Maschinen
  und kostet echtes Geld pro Video — bei 10 €/Monat würde ein Vielnutzer
  Verlust machen, und ein Handy kann es gar nicht. Der Vertrag dafür steht
  schon (`/render/pending|claim|result` + `HOOKCUT_LOCAL_RENDER`).
- **Abo über die Webseite verkaufen, nicht in der App.** Apple nimmt in der
  EU rund 12–20 %, und man darf **nicht** beides gleichzeitig anbieten.
  Also: Abo im Web abschließen, die App schaltet nur frei.

| Phase | Inhalt | Zustand |
|---|---|---|
| 0 | Offene Registrierung (`HOOKCUT_INVITE_ONLY`), Musiker-Profile | **fertig** |
| 1 | Netzwerk: posten, Feed mit Filtern, folgen, Interesse, Kommentare | **fertig** |
| 2 | **Live stellen** | **als Nächstes** |
| 3 | Premium-Abo (Stripe) + Render-Agent für den PC | offen |
| 4 | Apps für iOS und Android (Expo/React Native, NativeWind) | offen |

**Phase 2 im Detail — sieben Schritte** (Stand: 3 von 7 erledigt)

Die Reihenfolge ist Absicht: **erst deployen, solange der Einladungscode noch
schützt.** So platzen Server-Überraschungen früh und ohne Publikum; das Öffnen
ist der letzte, bewusste Schritt.

| # | Schritt | Zustand |
|---|---|---|
| 1 | Ein Dienst: Backend liefert die Oberfläche mit aus | **fertig** (`f4c4a97`) |
| 2 | Video-Werkzeuge online abschaltbar (`HOOKCUT_TOOLS_ENABLED`) | **fertig** (`b91ce1e`) |
| 3 | Schlanker Server (schwere Importe faul, `requirements-server.txt`) | **fertig** |
| 4 | `Dockerfile` + `render.yaml`, erster Livegang — noch geschlossen | **Dateien fertig**, Livegang liegt beim Besitzer → `HOSTING.md` |
| 5 | Impressum / Datenschutz / AGB, Meldeknopf, Konto löschen | **fertig** |
| 6 | E-Mail-Bestätigung + Rate-Limit auf die Registrierung | offen |
| 7 | Sicherheits-Durchgang, `HOOKCUT_INVITE_ONLY=0`, echte Musiker einladen | offen |

**Zwei Entscheidungen, die diesen Plan von der alten Fassung unterscheiden:**

- **Kein PostgreSQL.** Der ältere Fahrplan sah SQLite → PostgreSQL vor. Das
  entfällt und spart Wochen: SQLite ist für ein leselastiges Netzwerk mit den
  ersten hundert Nutzern produktionstauglich, WAL läuft bereits.
  **Bedingung:** eine *dauerhafte Festplatte* — auf einer Gratis-Stufe mit
  flüchtigem Dateisystem wären Datenbank *und* Hörproben nach jedem Neustart
  weg. Deshalb bezahltes Hosting (~9 €/Monat, mit dem Besitzer entschieden).
  Sicherheitsnetz: Litestream spiegelt die Datenbank laufend nach
  Cloudflare R2. **Ehrlich dazu:** Litestream sichert nur die Datenbank, nicht
  die Hörproben — bei einem Plattenschaden wären Konten und Beiträge zurück,
  die Audiodateien nicht.
- **Kein Object Storage zum Start.** Hörproben liegen mit auf der Platte.
  Nachrüstbar, aber kein Startblocker.

**Schritt 5 ist erledigt** (Impressum nach § 5 DDG mit ladungsfähiger
Anschrift, Datenschutzerklärung getrennt davon, Nutzungsbedingungen,
Meldefunktion nach DSA, Konto löschen nach DSGVO Art. 17). Die Betreiberdaten
stehen an **einer einzigen Stelle** (`backend/betreiber.py`, zusätzlich per
`HOOKCUT_BETREIBER_*` überschreibbar), damit die Privatadresse später ohne
Programmieren gegen eine Geschäftsadresse tauschbar ist.
Die Texte gehören vor dem Livegang einmal vom Besitzer geprüft — besonders die
AGB, weil es dort um fremde Rechte an Beats und Samples geht.

**Danach (Phase 3+):** Render-Agent (Companion, der pending-Items zieht,
lokal rendert und per `/render/{item}/result` hochlädt) · Stripe ·
Benachrichtigungen · „Bleibt-online"-Features Smart Link / EPK.

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

- **231 pytest-Tests grün** (tests/). Web-Build + oxlint grün. Sync + Hook mit
  echten Dateien validiert (offset ~5039ms, conf 0.88 beim Testmaterial).
- **Im echten Browser durchgespielt** (Playwright gegen den Vite-Proxy):
  Anmeldung/Registrierung, Navigation, und der komplette Netzwerk-Ablauf mit
  ZWEI getrennten Konten — Rapper postet mit Hörprobe → Producer findet ihn
  über den Kategorie-Filter **ohne zu folgen** → öffnet, zeigt Interesse,
  kommentiert → sieht keinen Erledigt-/Löschen-Knopf → folgt → Beitrag
  erscheint unter „Folge ich" → Rapper sieht den Interessenten samt Profil →
  setzt auf erledigt → Beitrag verschwindet aus „Entdecken".
- **Vom Besitzer end-to-end bestätigt:** Sync, Hook-Flow, Styles-Render,
  9:16-Cover, Untertitel unten + exakte Lyrics. Außerdem: nach `git pull`
  startet die App und der Login-Ablauf funktioniert.
- **Noch NICHT vom Besitzer im echten Render bestätigt** (die Sandbox kann
  kein Chrome/WebGPU): Beat-Effekte, Multi-Plattform-Export, Wochen-Content,
  Spotify Canvas. Backend und Tests sagen nichts darüber, ob ein Video am
  Ende gut aussieht — das kann nur sein Rechner zeigen.
- **Das Netzwerk hat noch nie ein echter Musiker benutzt.** Alles bisher sind
  Testkonten. Das ist die größte offene Unbekannte im ganzen Projekt.
- **Ohne Bedienoberfläche, aber fertig und getestet:**
  `pipeline/multitake_cut.py` (taktgenauer Bildwechsel zwischen mehreren
  Takes) und `pipeline/upscale.py`. Beide hingen an der Gradio-Oberfläche,
  die im August 2026 entfernt wurde (kein Knopf führte mehr dorthin, und sie
  war der einzige Grund für die schwere `gradio`-Abhängigkeit). Die Module
  bleiben — sie warten auf eine Anbindung im Dashboard.
- `effects_grading.py` (alte ffmpeg-Effekte) ist durch die FreeCut-Styles
  überholt, wird aber weiter von `presets.py` genutzt — also **kein** toter
  Code. Die alten REST-Endpunkte (`POST /projects`, `/takes`, `/sync`,
  `/presets`) bleiben als dokumentierte API bestehen; das Dashboard nutzt
  `GET /projects` + Take-Download.

## Sicherheit (Review-Stand August 2026)

Durchgesehen wurde die komplette Auth-Fläche: auth.py, die Ownership-Regel in
main.py, das DB-Schema und die Datei-Ausgabe.

Geprüft und in Ordnung:
- Passwörter mit bcrypt (12 Runden), 72-Byte-Grenze vor jedem Hash/Check.
- In der DB liegt nur der SHA-256-Hash des Session-Tokens, nie das Token.
- Cookie httpOnly + SameSite=lax; Secure-Flag über HOOKCUT_SECURE_COOKIES.
- Login: einheitliche Fehlermeldung UND konstante Laufzeit (bcrypt läuft auch
  bei unbekannter E-Mail gegen einen Dummy-Hash) — verrät nicht, welche
  E-Mails registriert sind. Lockout (5 Fehlversuche → 15 min) liegt in der DB.
- Jede Datenroute hängt an get_current_user; fremde Ressourcen geben 404
  (nicht 403). Offen sind nur die statischen Kataloge (/styles, /platforms,
  /presets, /health, /post-categories, /report-reasons), /auth/config und
  /betreiber (Impressum). Admin-Routen zusätzlich hinter get_admin_user.
  **Seit August 2026 dauerhaft abgesichert:** `tests/test_routen_schutz.py`
  ruft jede der 76 Routen ohne Anmeldung auf; jede offene Route braucht
  einen Eintrag mit Begründung, sonst schlägt der Test fehl.
- **Die automatische API-Doku ist online aus** (`HOOKCUT_API_DOCS=0`).
  Gefunden beim Durchgang im August 2026: `/docs`, `/redoc` und
  `/openapi.json` waren öffentlich und hätten jedem Besucher sämtliche
  Routen samt Parametern gezeigt, Admin-Wege inklusive. Lokal bleibt es an.
- Passwortwechsel wirft alle Sitzungen (auch andere Geräte) weg.
- password_hash taucht in keiner Antwort auf. Alle Dateipfade kommen aus der
  DB, nie aus der URL — kein Path-Traversal.

Behoben in diesem Durchgang:
- Einladungscodes wurden mit einem bedingungslosen UPDATE eingelöst. Zwei
  gleichzeitige Registrierungen mit demselben Code hätten beide durchgehen
  können (zwei Konten aus einer Einladung). Jetzt `WHERE used_by IS NULL` +
  Auswertung von rowcount; verliert eine Registrierung das Rennen, wird das
  eben angelegte Konto wieder entfernt.

Bewusst offen (lokal unkritisch, vor dem Hosting zu klären):
- Kein Größenlimit für die **Werkzeug**-Uploads (`_save_upload` in `main.py`:
  Video/Song für Sync, Hook, Packs, Canvas) — lokal egal. Online entschärft,
  seit diese Routen mit `HOOKCUT_TOOLS_ENABLED=0` gar nicht mehr erreichbar
  sind (503, Phase 2 Schritt 2). Werden sie je online freigeschaltet, braucht
  es vorher eine Grenze. Die **Netzwerk**-Uploads (Hörproben) sind gedeckelt
  (`_save_upload_capped`, 8 MB + Endungs-Positivliste + Längenprüfung).
- Nach einer abgelaufenen Sperre bleibt fail_count stehen: der nächste
  Fehlversuch sperrt sofort wieder für 15 min. Für den Besitzer harmlos
  (hookcut-passwort-reset.bat), online aber ein Ärgernis-Hebel gegen fremde
  Konten.
- Die „erstes Konto wird Admin"-Prüfung ist selbst nicht renn-sicher; bei
  zwei exakt gleichzeitigen Erst-Registrierungen könnten zwei Admins
  entstehen. Praktisch nur relevant, wenn das Ding online geht.
- **Neu mit der offenen Registrierung** (`HOOKCUT_INVITE_ONLY=0`): Der 409
  „E-Mail schon registriert" verrät, ob eine Adresse ein Konto hat. Bisher war
  das durch den Einladungszwang gedeckelt — im offenen Modus ist es das nicht
  mehr. Bewusst so gelassen, weil die Alternative (immer 200 antworten und per
  Mail klären) ohne E-Mail-Versand nicht ehrlich umsetzbar ist. **Mit der
  E-Mail-Bestätigung in Phase 2 erledigt sich das**; bis dahin dokumentiert.
- Ebenfalls offen bis zum Livegang: Rate-Limit auf die Registrierung. Ohne
  Einladungszwang kann sonst ein Skript beliebig viele Konten anlegen.

## Offene / nächste Themen (Stand der Diskussion)

**Als Nächstes:** Phase 2, Schritt 6 — E-Mail-Bestätigung (abschaltbar) und
Rate-Limit auf die Registrierung. **Zwei Fallstricke, die dort zählen:**
hinter Renders Proxy ist `request.client.host` immer dieselbe Adresse (die
echte steht in `X-Forwarded-For`), sonst sperrt das Limit alle gemeinsam aus;
und der Versand von der eigenen Domain braucht SPF/DKIM, geht also erst mit
Domain — bis dahin bleibt die Bestätigung abschaltbar.

Parallel dazu kann der Besitzer jederzeit den Livegang aus Schritt 4
durchführen (`HOSTING.md`); die Tür bleibt dabei zu.

**Warten auf den Besitzer** (nur sein Rechner kann das prüfen):
1. Beat-Effekte, Multi-Plattform-Export, Wochen-Content und Spotify Canvas
   im echten Render bestätigen. Danach ggf. Beat-Intensität/Stride
   feinjustieren (beat_pulse.py hat stride=2/4, UI bewusst nur Toggle) und
   Style-Intensitäten nachziehen.
2. Das Netzwerk selbst ausprobieren und sagen, ob sich der Ablauf richtig
   anfühlt (posten → finden → Interesse → Kontakt).

**Bewusst zurückgestellt** (mit Begründung, nicht vergessen):
3. Benachrichtigungen (Glöckchen) — kommen direkt nach Phase 1, damit Leute
   zurückkommen.
4. Direktnachrichten — Kontakt läuft vorerst über die Profillinks
   (Instagram/Spotify) der Interessenten. Erst bauen, wenn sich zeigt, dass
   es wirklich fehlt.
5. Bilder an Beiträgen — erst wenn der Object Storage steht; die lokale
   Platte ist dafür der falsche Ort.
6. Blockieren/Stummschalten von Nutzern.
7. i18n der neuen Editor-Strings (TODO in editor/HOOKCUT-FORK.md).
8. Ideen: all-in-one-Strukturmodell als Pro-Backend (NATTEN/HF-Blocker
   beachten), Wort-Karaoke-Highlight.

## Stil der Zusammenarbeit mit dem Besitzer

Deutsch, kurz, ehrlich (Grenzen offen benennen), keine Fachbegriffe ohne
Erklärung, alles per `.bat` doppelklickbar machen, jeden Schritt selbst
testen soweit möglich und den Rest als klaren Nutzer-Test formulieren
("git pull → neu starten → X prüfen"). Commits + Push nach jedem Schritt.
