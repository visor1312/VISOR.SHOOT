# FreeCut testen (Teil B) — Anleitung für deinen PC

Ziel: In ~15 Minuten selbst sehen, ob FreeCut als Editor für selfsign taugt.
Das läuft nur auf deinem Rechner (braucht **Chrome oder Edge** + Grafikkarte),
nicht in meiner Umgebung.

> Wichtig: Das ist ein **getrennter Test**, komplett neben selfsign. Deine
> selfsign-Installation wird dabei nicht angefasst.

## 1. FreeCut holen und starten
Öffne `cmd-hier.bat` (oder ein CMD irgendwo, wo Platz ist) und tippe:

```
git clone https://github.com/walterlow/freecut.git
cd freecut
npm install
npm run dev
```

`npm install` lädt einiges herunter (ein paar Minuten, einmalig). Wenn am Ende
sowas wie `Local: http://localhost:5173/` steht, im **Chrome** öffnen.

> Falls Port 5173 belegt ist, weil selfsign gleichzeitig läuft: vorher die
> selfsign-Fenster schließen — oder FreeCut mit `npm run dev -- --port 5199`
> starten und dann `http://localhost:5199` öffnen.

## 2. Die drei Kaufentscheider prüfen
1. **Editor-Gefühl:** Ein Video reinziehen, auf der Timeline schneiden,
   verschieben. Fühlt es sich flüssig und verständlich an?
2. **Zweite Tonspur:** Zusätzlich einen Song (mp3/wav) importieren und auf eine
   eigene Audiospur unter das Video legen. Das ist unser Kern-Ablauf
   („Song über stummes Video").
3. **9:16-Export:** In den Projekt-/Canvas-Einstellungen auf Hochformat
   (1080×1920) stellen, ein paar Sekunden exportieren (MP4). Kommt eine saubere
   9:16-Datei raus? Gerne mit eingebrannten Untertiteln testen.

## 3. Mir Bescheid geben
Schick mir einfach kurz:
- Lief `npm install`/`npm run dev` durch? (sonst: Fehlermeldung reinkopieren)
- Wie fühlt sich der Editor an (1 = mühsam … 5 = top)?
- Hat der 9:16-Export geklappt? (gern ein Screenshot oder die kurze MP4)

Danach entscheiden wir gemeinsam: **GO** (ich baue die selfsign-Analyse an
FreeCut an, siehe `eval/freecut_adapter.py`) oder anderer Weg.

---

### Optional für Technik-Neugierige: headless (ohne UI)
FreeCut kann Projekte auch per Kommandozeile rendern:
```
npm run headless -- --workspace "<ordner>" --project <id> --resolution 1080x1920 --out clip.mp4
```
Das ist der Weg, über den selfsign später vollautomatisch ein fertiges
9:16-Video erzeugen könnte, ohne dass du im Editor klicken musst.
