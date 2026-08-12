# HOOKCUT — Hinweise für Claude

Kurzanleitung für jede neue Session. Tiefe Details stehen in
`PROJEKT-STATUS.md` (Architektur, Fahrplan, gelernte Lektionen, Sicherheit)
und `README.md` (Bedienung). **Diese Datei bewusst kurz halten und nicht
duplizieren** — was hier und dort steht, driftet sonst auseinander.

## Was das ist

Zwei Dinge in einem Projekt:

1. **Das Werkzeug** (fertig, in Benutzung): Performance-Video + Song rein,
   fertiges Reel raus — Sync, viralster Hook, Styles, Untertitel,
   Beat-Effekte, Multi-Plattform, Wochen-Content, Spotify Canvas.
2. **Das Netzwerk** (neu): ein soziales Netzwerk für Independent-Musiker mit
   „offenen Projekten" („mir fehlt noch ein Refrain"). Kostenlos; das
   Werkzeug aus 1. wird später das Premium-Angebot (~10 €/Monat).

**Der Besitzer ist Nicht-Techniker und arbeitet unter Windows.** Das prägt
alles: Oberfläche und Fehlermeldungen auf Deutsch, jeder Ablauf per
Doppelklick auf eine `.bat`, keine Fachbegriffe ohne Erklärung.

## Wo wir gerade stehen (Stand August 2026)

Arbeitsbranch: **`claude/rap-video-auto-editor-s9xfvt`**

| | Zustand |
|---|---|
| Werkzeug (Reels, Hook, Canvas, Wochen-Content) | fertig, läuft beim Besitzer |
| Benutzersystem (Login, Profile) | fertig |
| Netzwerk (posten, Feed, folgen, Interesse, Kommentare) | **fertig, aber noch nie von echten Musikern benutzt** |
| Live stellen (Phase 2) | **läuft** — 6 von 7 Schritten fertig; Livegang liegt beim Besitzer (`HOSTING.md`) |
| Premium-Abo, Apps für iOS/Android | später |

416 pytest-Tests grün, Web-Build und oxlint grün.
(Die Zahl wirkt hoch, weil drei Wächter je Datei bzw. je Route einen Fall
erzeugen: `test_routen_schutz.py` ~78, `test_keine_doppelten_namen.py` ~30,
`test_deployment_dateien.py` 16.)
Der genaue Fahrplan steht in `PROJEKT-STATUS.md`, Abschnitt „Fahrplan".

## Grundregeln

1. **Deutsch** — UI-Texte, Fehlermeldungen, Commit-Messages, Antworten.
   Im Code Umlaute in Kommentaren meiden (`ue`, `ae`, `oe`), in
   UI-Strings sind echte Umlaute richtig.
2. **Nach jedem Schritt committen und pushen.** Nicht sammeln.
3. **Ehrlich über Grenzen.** Was nicht getestet werden konnte, klar als
   solches benennen — nicht als „fertig" verkaufen.
4. **Selbst testen, was testbar ist.** Der Rest wird als konkreter
   Nutzer-Test formuliert („starten → X anklicken → was passiert?").
5. **Niemals mit `--force` über das Remote pushen.**

## Befehle

```bash
python -m pytest tests/ --ignore=tests/test_upscale.py -q   # Tests
cd web && npm run build                                     # tsc -b && vite build
cd web && npm run lint                                      # oxlint
```

Alle drei müssen grün sein, bevor committet wird.
`test_upscale` braucht torch (optional, siehe README) — deshalb ausgelassen.

**Auf dem Windows-Rechner des Besitzers:**
- Starten: `start-hookcut.bat` doppelklicken (Backend + Dashboard).
- PowerShell blockiert `npm.ps1` → CMD benutzen oder `npm.cmd`.
- Python liegt ggf. unter `%LOCALAPPDATA%\Microsoft\WindowsApps\python.exe`
  (so macht es `update-hookcut.bat`).
- Immer `localhost:5173` aufrufen, **nicht** `127.0.0.1` — das Session-Cookie
  hängt am Hostnamen.

## Zwei Umgebungen, zwei Realitäten

| | Cloud (Claude Code im Web) | Rechner des Besitzers |
|---|---|---|
| Video-Render (Chrome/WebGPU) | **geht nicht** | geht — hier wird es wirklich geprüft |
| Modelle (Demucs, Whisper) | Download blockiert | laden beim ersten Lauf |
| Backend, Tests, Web-Build | voll testbar | voll testbar |
| Abhängigkeiten | `.claude/hooks/session-start.sh` installiert sie automatisch | `update-hookcut.bat` erledigt das |

**In der Cloud kann der Container auf einen alten Stand zurückfallen**
(mehrfach passiert). Sehen Dateien alt aus oder fehlen: `git fetch origin
<branch> && git reset --hard origin/<branch> && git clean -fd`, dann
`pip install -r requirements.txt` und `npm install` in `web/`.
Das Remote ist die Wahrheit. **Lokal auf dem Rechner des Besitzers gilt das
nicht** — dort ist die Arbeitskopie die Wahrheit, also nichts blind
zurücksetzen.

## Struktur

```
backend/          FastAPI + SQLite (kein ORM)
  main.py         Das WERKZEUG: Sync, Hook, Styles, Packs, Canvas (+ _own)
  network.py      Das NETZWERK: Beiträge, Feed, Interesse, Kommentare
                  (+ _own_public, gedeckelter Upload) — eigener APIRouter
  auth.py         Passwörter, Sessions, Profile, Admin-Routen
  db.py           Schema + Zugriff; jede Funktion nimmt db_path=
  config.py       Env-Konfiguration (Hosting-Schalter)
  pipeline/       Sync, Hook-Erkennung, Untertitel, Styles, Render
web/src/          React 19 + Vite + Tailwind v4 + react-router-dom
  pages/          Eine Datei pro Route
  components/     AppShell, Sidebar, Wizards, Karten
  lib/format.ts   Gemeinsame Anzeige-Helfer (Datum, Zeit, Status-Ampeln)
editor/           FreeCut-Fork, rendert per Chrome/WebGPU
tests/            pytest
*.bat             Doppelklick-Einstiege für den Besitzer

requirements.txt          alles — für den Rechner des Besitzers
requirements-server.txt   nur das Netzwerk — für den gehosteten Server
Dockerfile                Node baut die Oberfläche, Python liefert sie aus
docker-start.sh           Start im Container (optional unter Litestream)
render.yaml               Bauplan für Render inkl. dauerhafter Festplatte
HOSTING.md                Schritt-für-Schritt-Anleitung zum Livegang
```

## Konventionen

- **Neue Anzeige-Helfer** (Datum, Status-Ampel …) gehören in
  `web/src/lib/format.ts`, nicht als Kopie in einzelne Seiten.
- **Datenrouten** brauchen immer `user: dict = Depends(auth.get_current_user)`.
  Offen sind nur die statischen Kataloge (`/styles`, `/platforms`, `/presets`,
  `/post-categories`, `/health`, `/auth/config`).
- **Zwei Sichtbarkeits-Regeln — nicht verwechseln:**

  | | Lesen | Ändern / Löschen |
  |---|---|---|
  | **Privates** (Projekte, Jobs, Packs, Canvas) | nur Besitzer → **404** via `_own()` | nur Besitzer → **404** |
  | **Soziales** (Beiträge, Kommentare) | jedes angemeldete Mitglied | nur Autor → **403** via `_own_public()` |

  Die 404-Regel schützt davor, dass jemand die *Existenz* fremder Daten
  herausfindet. Bei einem Beitrag im Feed ist die Existenz ohnehin öffentlich —
  dort wäre 404 gelogen, deshalb 403. **Neue private Route ⇒ `_own()`, neue
  soziale Route ⇒ `_own_public()`.** Falsch gewählt heißt Datenleck oder
  kaputter Feed.
- **Die Schnittstelle gibt nicht mehr preis als die Ansicht zeigt.** Beispiel:
  die Liste der Interessenten bekommt nur der Autor, alle anderen nur die
  Anzahl (`GET /posts/{id}/interest`).
- **Uploads von Fremden** (alles im Netzwerk) gehen über
  `_save_upload_capped()` mit Größengrenze, Endungs-Positivliste und
  Längenprüfung. Das alte `_save_upload()` ist ungedeckelt und nur noch für
  die lokalen Werkzeug-Flows gedacht.
- **Jedes Konto hat garantiert ein Profil** — `get_current_user` zieht es bei
  Bedarf nach. Feed, Kommentare und Interessenten verbinden hart mit
  `profiles`; ohne diese Garantie fielen Einträge lautlos heraus (genau das
  ist einmal passiert).
- **`db.py`-Funktionen** immer mit `db_path=`-Keyword (Tests nutzen
  eigene DBs über `HOOKCUT_DB`).
- **Der API-Pfad unterscheidet sich zwischen Entwicklung und Betrieb.**
  In `web/src/api.ts` gilt `BASE = import.meta.env.DEV ? "/api" : ""`: lokal
  schreibt Vite `/api/...` aufs Backend um, im gebauten Stand liefert das
  Backend die Oberfläche selbst aus (`FRONTEND_DIR`, ganz am Ende von
  `backend/main.py`) — dann entfällt das Präfix. **Nie fest auf `/api`
  verdrahten**, sonst funktioniert online gar nichts, und zwar mit
  irreführenden Fehlern. Wer daran etwas ändert, muss den **gebauten** Stand
  prüfen (`cd web && npm run build`, dann Backend starten und Port 8000
  im Browser öffnen) — der Dev-Server beweist hier nichts.
- **Die Video-Werkzeuge sind abschaltbar** (`HOOKCUT_TOOLS_ENABLED`, lokal `1`,
  gehostet `0`). Sie brauchen Chrome/WebGPU, ffmpeg und mehrere GB Modelle —
  online gibt es das nicht. Backend: `require_tools()` in `main.py` steht in
  **jeder Route, die einen Render- oder Analyse-Job startet** und antwortet
  abgeschaltet mit 503 statt still zu scheitern. Frontend: die Einträge sind in
  `Sidebar.tsx` mit `werkzeug: true` markiert und verschwinden, und die
  Startseite wird der Feed. **Neue Werkzeug-Route ⇒ `require_tools()` nicht
  vergessen**, sonst startet online ein Job, der nie fertig wird.
- **Neue Route ⇒ `tests/test_routen_schutz.py` entscheidet.** Der Test ruft
  jede Route ohne Anmeldung auf: 401/403 heißt geschützt. Ist eine Route
  absichtlich offen, gehört sie **mit Begründung** in `BEWUSST_OFFEN` —
  Offenheit muss eine Entscheidung sein, kein Versehen. Geprüft wird zur
  Laufzeit, weil `/auth/me` die Anmeldung im Funktionskörper holt und eine
  reine Code-Analyse das übersieht.
- **Nichts blind an `db.py` anhängen.** Die Datei ist über 1300 Zeilen lang;
  eine neue Funktion mit einem schon vergebenen Namen verdeckt stillschweigend
  die alte, und ein ganz anderer Programmteil fällt später um (genau so
  passiert mit `list_posts_by_user`). Erst `grep -n "def name"`, dann
  schreiben — `tests/test_keine_doppelten_namen.py` fängt den Rest ab.
- **Etwas löschen heißt: alles mit weg, was daran hängt.** Fremdschlüssel
  sind an (`PRAGMA foreign_keys = ON`), also blockiert jede vergessene
  Abhängigkeit den Löschvorgang mit einem 500er — und zwar erst dann, wenn
  jemand kommentiert oder Interesse gezeigt hat, also im Erfolgsfall.
  `db.delete_post` und `db.delete_user_completely` räumen deshalb Kommentare,
  Interesse, Kategorien und Meldungen mit. **Neue Tabelle mit Verweis auf
  `posts` oder `users` ⇒ in beide Funktionen eintragen.**
- **E-Mail-Versand geht über `backend/mailer.py`**, nie direkt. Die
  Zustellart ist ein Schalter (`HOOKCUT_MAIL_BACKEND`): `log` schreibt die
  Mail ins Serverfenster (Standard — so lässt sich der Ablauf ohne Domain
  durchspielen), `resend` verschickt wirklich, `aus` tut nichts. **Ein
  gescheiterter Versand darf den auslösenden Vorgang nie abbrechen** —
  sonst hat jemand ein Konto, von dem er nichts weiß.
- **Wer eine Adresse zählt (Rate-Limit), nimmt `auth.client_ip`.** Hinter
  dem Proxy ist `request.client.host` für alle gleich, und
  `X-Forwarded-For` ist eine Liste, deren **erster** Eintrag gefälscht sein
  kann — es gilt der **letzte**, und nur bei `HOOKCUT_TRUST_PROXY=1`.
- **Betreiberangaben stehen nur in `backend/betreiber.py`** (Name, Anschrift,
  E-Mail, Hoster). Impressum, Datenschutz und AGB holen sie über den
  öffentlichen Endpunkt `/betreiber` — **nie in die Oberfläche kopieren**,
  sonst stimmen nach einem Umzug zwei von drei Seiten nicht mehr. Zusätzlich
  per Env überschreibbar (`HOOKCUT_BETREIBER_*`), damit ein Adresswechsel
  ohne neuen Programmstand geht. **Ändert sich, welche Daten die Anwendung
  verarbeitet, muss `DatenschutzPage.tsx` mitwachsen** — eine Erklärung, die
  etwas verschweigt oder Nichtvorhandenes aufzählt, ist schlechter als keine.
- **Nutzerdaten gehören unter `config.PROJECTS_DIR`** (`HOOKCUT_PROJECTS_DIR`),
  nie fest ins Projektverzeichnis. `storage.py` und `db.DEFAULT_DB_PATH`
  hängen daran, ein Schalter verschiebt beides. Online zeigt er auf die
  dauerhafte Festplatte — alles andere im Container ist nach dem nächsten
  Ausrollen weg. **Neuer Ablageort ⇒ über `storage.py`**, nicht mit
  `Path(__file__)` neu gebaut.
- **Einstellbares Verhalten** gehört in `backend/config.py` (Env-Variable mit
  sicherem Standard), nicht als `os.environ`-Abfrage quer im Code. Beispiel:
  `HOOKCUT_INVITE_ONLY` — Standard `1` (lokal nur mit Einladung), die offene
  Plattform setzt `0`.
- **Der gehostete Server ist schlank — schwere Importe gehören in die
  Funktion.** `librosa`, `numpy`, `scipy`, `faster_whisper` und `demucs` sind
  zusammen ~1,5 GB und online **gar nicht installiert**
  (`requirements-server.txt`: fastapi, uvicorn, bcrypt, python-multipart).
  Deshalb stehen in `backend/main.py` die Importe von `beat_detect`,
  `hook_detect`, `sync_offset`, `transcribe` und `subtitles` **in den
  Funktionen**, nicht am Dateikopf. Wandert einer davon nach oben, startet der
  Server online nicht mehr — `tests/test_schlanker_server.py` fängt genau das
  ab (eigener Prozess mit Import-Sperre, plus Gegenprobe, dass die Sperre
  wirkt). Am Kopf bleiben dürfen `extract_audio`, `presets`, `render_sync` und
  `vocal_separation`: die brauchen nur ffmpeg bzw. die Standardbibliothek.
- **Neue Python-Pakete** brauchen Windows-Wheels und gehören gepinnt in
  `requirements.txt` mit deutschem Kommentar, warum sie da sind. Wird ein Paket
  auch **online** gebraucht, muss es zusätzlich in `requirements-server.txt` —
  mit derselben Version, sonst driften die beiden Listen auseinander.
