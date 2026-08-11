# HOOKCUT — Hinweise für Claude

Kurzanleitung für jede neue Session. Tiefe Details stehen in
`PROJEKT-STATUS.md` (Architektur, gelernte Lektionen, Sicherheit, Roadmap)
und `README.md` (Bedienung). **Diese Datei bewusst kurz halten und nicht
duplizieren** — was hier und dort steht, driftet sonst auseinander.

## Was das ist

Lokales Tool für Indie-Musiker: Performance-Video + Song rein, fertiges
Reel raus (Sync, viralster Hook, Styles, Untertitel, Beat-Effekte,
Multi-Plattform, Wochen-Content, Spotify Canvas). Ziel ist eine
verkaufbare Plattform (~10 €/Monat).

**Der Besitzer ist Nicht-Techniker und arbeitet unter Windows.** Das prägt
alles: Oberfläche und Fehlermeldungen auf Deutsch, jeder Ablauf per
Doppelklick auf eine `.bat`, keine Fachbegriffe ohne Erklärung.

## Grundregeln

1. **Deutsch** — UI-Texte, Fehlermeldungen, Commit-Messages, Antworten.
   Im Code Umlaute in Kommentaren meiden (`ue`, `ae`, `oe`), in
   UI-Strings sind echte Umlaute richtig.
2. **Nach jedem Schritt committen und pushen.** Nicht sammeln.
   Die Sandbox rollt gelegentlich auf einen alten Stand zurück —
   ungepushte Arbeit ist dann weg.
3. **Das Remote ist die Wahrheit.** Sieht der lokale Stand alt aus
   (fehlende Dateien, unbekannte Commits), zuerst:
   `git fetch origin <branch> && git reset --hard origin/<branch> && git clean -fd`
   Danach `npm install` in `web/` und `pip install -r requirements.txt`.
   **Niemals** mit `--force` über das Remote pushen.
4. **Ehrlich über Grenzen.** Was nicht getestet werden konnte, klar als
   solches benennen — nicht als „fertig" verkaufen.
5. **Alles selbst testen, was hier testbar ist.** Der Rest wird als
   konkreter Nutzer-Test formuliert („git pull → neu starten → X prüfen").

## Befehle

```bash
# Tests (torch fehlt in der Sandbox -> test_upscale auslassen)
python -m pytest tests/ --ignore=tests/test_upscale.py -q

# Frontend
cd web && npm run build     # tsc -b && vite build
cd web && npm run lint      # oxlint
```

Alle drei müssen grün sein, bevor committet wird.

## Struktur

```
backend/          FastAPI + SQLite (kein ORM)
  main.py         Routen; auth.get_current_user schützt jede Datenroute
  auth.py         Passwörter, Sessions, Login, Admin-Routen
  db.py           Schema + Zugriff; jede Funktion nimmt db_path=
  config.py       Env-Konfiguration fürs Hosting
  pipeline/       Sync, Hook-Erkennung, Untertitel, Styles, Render
web/src/          React 19 + Vite + Tailwind v4 + react-router-dom
  pages/          Eine Datei pro Route
  components/     AppShell, Sidebar, Wizards, Dashboard
  lib/format.ts   Gemeinsame Anzeige-Helfer (Datum, Zeit, Status-Ampeln)
editor/           FreeCut-Fork, rendert per Chrome/WebGPU
tests/            pytest
*.bat             Doppelklick-Einstiege für den Besitzer
```

## Konventionen

- **Neue Anzeige-Helfer** (Datum, Status-Ampel …) gehören in
  `web/src/lib/format.ts`, nicht als Kopie in einzelne Seiten.
- **Datenrouten** brauchen immer `user: dict = Depends(auth.get_current_user)`.
  Fremde Ressourcen geben **404** (nicht 403) über `_own()` — so verrät die
  API nicht, ob eine fremde ID existiert. Offen sind nur die statischen
  Kataloge (`/styles`, `/platforms`, `/presets`, `/health`).
- **`db.py`-Funktionen** immer mit `db_path=`-Keyword (Tests nutzen
  eigene DBs über `HOOKCUT_DB`).
- **Einstellbares Verhalten** gehört in `backend/config.py` (Env-Variable mit
  sicherem Standard), nicht als `os.environ`-Abfrage quer im Code. Beispiel:
  `HOOKCUT_INVITE_ONLY` — Standard `1` (lokal nur mit Einladung), die offene
  Plattform setzt `0`.
- **Neue Python-Pakete** brauchen Windows-Wheels und gehören gepinnt in
  `requirements.txt` mit deutschem Kommentar, warum sie da sind.

## Was hier NICHT getestet werden kann

- **Der Video-Render.** Er braucht Chrome mit WebGPU — geht nur auf dem
  Rechner des Besitzers. Backend und Tests sagen nichts darüber, ob ein
  Video am Ende gut aussieht.
- **Modell-Downloads** (Demucs, Whisper) sind in der Sandbox blockiert;
  sie laden erst beim Besitzer.

Alles, was diese beiden Wege betrifft, ist erst nach seiner Rückmeldung
wirklich bestätigt.
