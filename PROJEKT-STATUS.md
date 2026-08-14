# selfsign — Projekt-Übergabe / Status

> **Für jeden neuen Coding-Agenten (oder neuen Chat): ZUERST `CLAUDE.md`
> lesen (kurz), dann dieses Dokument (tief), dann README.md (Bedienung).**
> Stand: **August 2026**, Branch `claude/rap-video-auto-editor-s9xfvt`
> (alles committed und gepusht).

## Was ist selfsign?

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
          Browser-Video-Editor, als selfsign gebrandet. Wird als UNSICHTBARE
          Render-Engine benutzt: headless/render.mjs rendert per headless
          Chrome ein von backend generiertes project.json (--quality ultra,
          1080x1920). Hat auch einen ⚡selfsign-Button im Editor (Etappe 3),
          aber Produktrichtung ist der Assistent, nicht der Editor.
```

Datenfluss Render: backend/freecut_workspace.py schreibt
`workspace/projects/<id>/project.json` + `media/<id>/{datei,metadata.json}`
→ `node editor/headless/render.mjs --workspace … --build` → final.mp4.

## Start (Windows, Doppelklick)

**Für den Besitzer gibt es `START-AM-PC.md`** — die Schritt-für-Schritt-Seite
zum Aktualisieren, Starten und Ausprobieren. Bei Änderungen an den `.bat`-Dateien
oder am Ablauf dort mitziehen, sonst zeigt sie auf etwas, das es nicht mehr gibt.

- `start-selfsign.bat` — Backend + Dashboard (der normale Weg)
- `start-editor.bat` — Backend + Editor (nur für Editor-Arbeit)
- `update-selfsign.bat` — git pull + pip install + `npm install` in `web/` + Start
- `selfsign-premium-test.bat` — einmaliger Start mit `HOOKCUT_PREMIUM_REQUIRED=1`,
  um die Bezahlschranke lokal zu sehen (über `_backend-premium.bat`)
- `selfsign-abo.bat` — Abos von Hand vergeben/beenden/anzeigen
- `cmd-hier.bat` — CMD im Ordner
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
- **backend/admin.py** (+ selfsign-einladung.bat / selfsign-passwort-reset.bat):
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
- **`/render/{item}/result` ist gedeckelt** (200 MB, `backend/uploads.py`).
  Diese drei Routen haben bewusst **kein** `require_tools()` — sie müssen auch
  antworten, wenn der Server nicht rendert. Damit sind sie die einzigen
  Werkzeug-Routen, die online offenstehen, also gilt für sie dieselbe Regel
  wie für Dateien von Fremden. Läuft die Grenze über, wird die halbe Datei
  weggeräumt **und** das Item auf `pending` zurückgesetzt (sonst hängt es für
  immer auf `rendering`).

### Bekannter Befund: der Render-Vertrag ist online noch unerreichbar

`render.yaml` setzt `HOOKCUT_TOOLS_ENABLED=0` → `POST /packs` antwortet mit
503 (`tests/test_tools_switch.py`) → es entstehen nie `pack_items` →
`/render/pending` ist immer leer. Dazu fehlen dem schlanken Server die
Analyse-Pakete (librosa, faster_whisper). **Wird in Phase 3, Schritt 3
umgebaut:** vom Item-Auftrag zum Pack-Auftrag, damit der Agent auch die
Analyse übernimmt. Siehe `PHASE-3-PLAN.md`.

## Phase 3: Premium-Abo (August 2026)

Zwei Entscheidungen des Besitzers, hergeleitet in `PHASE-3-PLAN.md`:

1. **Wer rendert: der PC des Betreibers, für alle** (Modell B). Der Kunde
   installiert nichts — das ist das Argument, das 10 €/Monat trägt. Nadelöhr
   ist die 5-GB-Platte, nicht die Rechenzeit: Upload-Grenze und automatisches
   Löschen des Rohmaterials sind deshalb Pflicht, nicht Kür.
2. **Wer kassiert: Merchant of Record (Paddle)**, nicht Stripe. Kostet ~0,55 €
   mehr pro Abonnent, erspart dem Betreiber aber die EU-Umsatzsteuer komplett
   (bei Stripe greift ab 10.000 € EU-Umsatz das One-Stop-Shop-Verfahren).

**Schritt 1 (fertig): Abo-Zustand + Handschalter.**

- **Tabelle `subscriptions`**: eine Zeile pro Konto, kein Verlauf. Status
  `active` / `canceled` / `expired` / `past_due`; `period_end` `NULL` heißt
  unbefristet (gibt es nur bei Abos von Hand). Die `provider_*`-Spalten sind
  für Paddle vorbereitet und bleiben im Handbetrieb leer (`provider = 'hand'`).
- **`backend/abo.py`**: die Regel, wann ein Abo trägt — bewusst ohne FastAPI
  und ohne Route. `canceled` trägt **bis** `period_end` weiter (wer kündigt,
  hat bezahlt). Unlesbares Datum → gilt als abgelaufen, nicht als unbefristet.
- **`auth.require_premium()`**: **402**, nicht 403. 403 heißt „du darfst
  nicht", 402 heißt „das kostet" — daran erkennt die Oberfläche, dass sie auf
  die Premium-Seite schicken soll. Ersetzt `require_tools()` **nicht**: die
  eine sagt „das kostet", die andere „das läuft hier nicht".
- **`HOOKCUT_PREMIUM_REQUIRED`** (Default `0`, online `1`): lokal soll sich
  niemand aus seinen eigenen Werkzeugen aussperren.
- **`selfsign-abo.bat`** + `abo-geben` / `abo-nehmen` / `abo-liste`: Verkauf
  von Hand, bevor ein Zahlungsanbieter existiert. Freischalten **verlängert**
  ab dem bisherigen Ende, statt Resttage zu verschlucken.
- Nebenbei gefunden und behoben: `delete_user_completely` räumte
  `email_tokens` nicht weg — wer sein Konto vor der E-Mail-Bestätigung löschte,
  bekam „FOREIGN KEY constraint failed", also einen 500er ausgerechnet beim
  Löschrecht (DSGVO Art. 17).

**Schritt 2 (fertig): Bezahlschranke.**

- **Die Regel, wo sie greift** (Kommentarblock über den Routen in `main.py`):
  **Arbeit kostet** — alle zehn POST-Routen, die etwas anlegen oder rechnen
  lassen, hängen an `require_premium`. **Lesen und Herunterladen bleibt offen** —
  wessen Abo ausläuft, kommt weiter an das, was er in der bezahlten Zeit
  erzeugt hat. **Der `/render`-Vertrag bleibt offen** — läuft ein Abo aus,
  während der Agent noch rendert, muss das Video trotzdem ankommen.
- **`/premium`** (`PremiumPage.tsx`): Preis, Leistungen, was frei bleibt.
  **Bewusst ohne Bestellknopf**, solange von Hand verkauft wird — ein Knopf,
  der zahlungspflichtig bestellt, zieht die Button-Lösung (§ 312j Abs. 3 BGB),
  die Widerrufsbelehrung und den Kündigungsbutton (§ 312k BGB) nach sich. Das
  kommt zusammen mit dem Zahlungsanbieter, nicht halb.
- **`PremiumSchranke`** als Layout-Route vor den Werkzeug-Seiten. Bewusst
  **keine Weiterleitung**: die Adresse bleibt stehen, der Nutzer sieht, worauf
  er geklickt hat.
- Werkzeug-Einträge bleiben **sichtbar** (anders als bei fehlenden Werkzeugen):
  wer nicht sieht, was er kaufen könnte, kauft es nicht. Der Knopf „Reel
  erstellen" verschwindet dagegen — er würde ins Leere fassen.
- Das hartkodierte „Free Plan" in der Sidebar ist jetzt echte Auskunft.

Zwei Fehler, die erst der Browser-Test gezeigt hat:

1. **`require_premium` hing an keiner einzigen Route.** Die Schranke in der
   Oberfläche war damit reine Deko — ein `fetch` wäre durchgegangen. Jetzt
   angehängt und mit einer Liste in `tests/test_abo.py` festgenagelt, die
   jede der zehn Routen einzeln prüft (402 **vor** der Eingabeprüfung, sonst
   verrät ein 422, dass die Route gearbeitet hätte).
2. **`/auth/login` und `/auth/register` lieferten das Nutzer-Objekt ohne
   Abo-Felder.** Direkt nach dem Anmelden stand deshalb „NaN €" auf der
   Premium-Seite. `public_user()` liefert den Abo-Zustand jetzt überall mit.

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
| 6 | E-Mail-Bestätigung + Rate-Limit auf die Registrierung | **fertig** (Bestätigung standardmäßig aus, siehe unten) |
| 7 | Sicherheits-Durchgang, `HOOKCUT_INVITE_ONLY=0`, echte Musiker einladen | Durchgang **fertig**; Öffnen wartet auf den Livegang |

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

## Sicherheits-Durchgang vor dem Öffnen (Phase 2, Schritt 7)

**Angriffe statt Codelektüre.** Vor dem Öffnen der Tür wurde die Anwendung
mit echten Konten angegriffen, nicht nur gelesen. Die Skripte dazu waren
Wegwerf-Werkzeuge; was sie geprüft haben, ist unten festgehalten, und die
wichtigsten Fälle sind als dauerhafte Tests eingebaut.

**Zwei echte Funde — beide gemessen, nicht vermutet:**

1. **Kommentar-Flut.** Kommentare waren die einzige Schreib-Route ohne
   Bremse — und sie landen unter *fremden* Beiträgen, sind also ein
   Belästigungswerkzeug. Gemessen: 300 Kommentare in 2,1 Sekunden,
   hochgerechnet über eine halbe Million pro Stunde. Jetzt 60/Stunde,
   gezählt über **alle** Beiträge hinweg (sonst verteilt ein Skript die Flut
   einfach auf viele Beiträge).
2. **Bestätigungsmails ohne Ende.** `/auth/resend-verification` nahm 50 von
   50 Anforderungen an — damit ließe sich das Gratis-Kontingent des
   Mail-Dienstes in einer Minute verbrennen. Jetzt zwei Minuten Wartezeit,
   gemessen am Alter des vorhandenen Links.

**Geprüft und gehalten:**

- **Kein Ausbruch aus dem Oberflächen-Ordner.** 13 Pfad-Tricks
  (`../`, URL-kodiert, doppelt kodiert, Backslashes, Null-Byte, absolute
  Pfade) landen alle auf der normalen Startseite. Gegenprobe: die Oberfläche
  wird wirklich ausgeliefert, der Test misst also etwas.
- **Kein SQL-Einschleusen.** Werte gehen ausnahmslos über Platzhalter. Die
  wenigen f-Strings bauen nur *Spaltennamen* ein, und die stammen aus fest
  verdrahtetem Code plus Positivliste (`_POST_FIELDS`), nie aus Eingaben.
- **23 Angriffe auf Rechte und Datentrennung** abgewehrt: fremde Beiträge
  ändern/löschen, fremde Kommentare löschen, sechs Admin-Wege als normales
  Mitglied, fremde Projekte lesen (404, nicht 403), Interessenten-Liste als
  Unbeteiligter, Passwort-Hash oder fremde E-Mail in einer Antwort,
  Dateipfade im Feed, `javascript:`-Link im Profil, überlange und unsinnige
  Eingaben.
- **Sitzungen:** In der DB liegt nur der Hash. Abmelden löscht die Zeile
  wirklich. Ein Passwortwechsel wirft alle Sitzungen weg, auch auf anderen
  Geräten. Erfundene Cookies (auch ein selbst gebauter Hash) ergeben 401.
- **Anmeldung:** Sperre nach fünf Fehlversuchen; unbekannte und echte
  Adresse liefern dieselbe Meldung.
- **Uploads:** 9-MB-Datei → 413, fremde Endung → 415, als `.wav` getarnter
  Text → 422.
- **Kein `dangerouslySetInnerHTML`** in der Oberfläche; Skript-Text wird
  gespeichert wie eingegeben und von React beim Anzeigen entschärft.
- **CORS** ohne Wildcard, fremde Herkunft wird nicht erlaubt. Cookie mit
  HttpOnly und SameSite; `Secure` nur online.
- **Werkzeuge online aus:** `POST /packs` → 503, Feed weiter nutzbar.

**Der 409-Hinweis beim Registrieren hat sich nebenbei entschärft.** Bisher
verriet „E-Mail schon registriert", welche Adressen ein Konto haben. Mit der
neuen Bremse ist das praktisch tot: im offenen Modus legt jeder Fehlversuch
selbst ein Konto an und zählt aufs Limit — nach fünf Adressen ist für eine
Stunde Schluss. Gemessen: 6 Versuche, dann gebremst.

**Bewusst nicht angefasst:** Folgen und Interesse haben keine Bremse, sind
aber idempotent (der Schlüssel verhindert Doppeleinträge); Profil-Änderungen
betreffen nur das eigene Profil.

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
  (selfsign-passwort-reset.bat), online aber ein Ärgernis-Hebel gegen fremde
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

**Schritt 6 ist erledigt.**

- **Rate-Limit:** höchstens 5 neue Konten pro Stunde und Adresse
  (`HOOKCUT_REGISTER_MAX_PER_HOUR`). Gezählt werden nur *erfolgreiche*
  Registrierungen — ein Tippfehler beim Einladungscode soll niemanden
  aussperren. Die Adresse kommt aus `auth.client_ip`: hinter dem Proxy der
  **letzte** Eintrag aus `X-Forwarded-For` (der erste ist fälschbar), und nur
  bei `HOOKCUT_TRUST_PROXY=1`. Die Adresse steht höchstens eine Stunde in der
  DB und wird danach weggeräumt.
- **E-Mail-Bestätigung:** gebaut, aber `HOOKCUT_EMAIL_VERIFICATION` ist
  **standardmäßig aus** — ohne Domain mit SPF/DKIM käme die Mail nicht an.
  `backend/mailer.py` hat drei Zustellarten; `log` schreibt die Mail ins
  Serverfenster, sodass sich der ganze Ablauf ohne Domain durchspielen lässt.
  Unbestätigte Konten dürfen lesen und ihr Profil pflegen, aber nicht posten
  oder kommentieren. Das erste Konto (der Betreiber) ist ausgenommen.
  Anleitung zum Einschalten: `HOSTING.md`, Abschnitt 6.

**Als Nächstes:** Phase 2, Schritt 7 — ein Sicherheits-Durchgang über alles
Neue, dann `HOOKCUT_INVITE_ONLY=0` und **fünf bis zehn echte Musiker
einladen und zuschauen, was sie tun**. Das ist der Moment der Wahrheit; bis
dahin ist alles Vermutung.

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
7. i18n der neuen Editor-Strings (TODO in editor/selfsign-FORK.md).
8. Ideen: all-in-one-Strukturmodell als Pro-Backend (NATTEN/HF-Blocker
   beachten), Wort-Karaoke-Highlight.

## Stil der Zusammenarbeit mit dem Besitzer

Deutsch, kurz, ehrlich (Grenzen offen benennen), keine Fachbegriffe ohne
Erklärung, alles per `.bat` doppelklickbar machen, jeden Schritt selbst
testen soweit möglich und den Rest als klaren Nutzer-Test formulieren
("git pull → neu starten → X prüfen"). Commits + Push nach jedem Schritt.
