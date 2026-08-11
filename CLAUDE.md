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
| Live stellen (Hosting, Pflichtseiten, Meldeknopf) | **als Nächstes** |
| Premium-Abo, Apps für iOS/Android | später |

231 pytest-Tests grün, Web-Build und oxlint grün.
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
  main.py         Routen (Werkzeug UND Netzwerk); _own/_own_public s.u.
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
- **Einstellbares Verhalten** gehört in `backend/config.py` (Env-Variable mit
  sicherem Standard), nicht als `os.environ`-Abfrage quer im Code. Beispiel:
  `HOOKCUT_INVITE_ONLY` — Standard `1` (lokal nur mit Einladung), die offene
  Plattform setzt `0`.
- **Neue Python-Pakete** brauchen Windows-Wheels und gehören gepinnt in
  `requirements.txt` mit deutschem Kommentar, warum sie da sind.
