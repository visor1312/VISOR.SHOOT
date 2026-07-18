# HOOKCUT-Editor (Fork von FreeCut)

Dieser Ordner (`editor/`) ist der Video-Editor von HOOKCUT. Er ist ein **Fork
des Open-Source-Projekts [FreeCut](https://github.com/walterlow/freecut)**
(MIT-Lizenz, © 2025 FreeCut) — siehe `LICENSE`. Wir bauen HOOKCUT darauf auf:
FreeCut liefert den kompletten Browser-Editor (Timeline, GPU-Effekte,
Übergänge, Untertitel), HOOKCUT ergänzt darum herum die automatische Analyse
(Sync + Hook-Erkennung) und das Branding.

## Wichtige Hinweise
- **Nur Chrome oder Edge** (braucht WebGPU/WebCodecs). Kein Firefox/Safari.
- Deutsch ist als App-Sprache bereits vorhanden (Einstellungen → Allgemein).
- Die Lizenz-Datei `LICENSE` (FreeCut, MIT) **muss erhalten bleiben** — das
  verlangt die MIT-Lizenz.

## Starten (auf deinem Rechner)
In einem normalen CMD-Fenster (nicht PowerShell):
```
cd editor
npm install
npm run dev
```
Dann die angezeigte Adresse (z.B. `http://localhost:5173`) in **Chrome** öffnen.
Der Browser-Tab sollte jetzt **HOOKCUT** heißen.

> Läuft parallel das alte HOOKCUT-Dashboard (Port 5173)? Dann eins von beidem
> auf einen anderen Port legen, z.B. `npm run dev -- --port 5199`.

## Umbau-Etappen (Stand: großer Umbau läuft)
1. ✅ Fork übernommen, Browser-Tab/PWA auf HOOKCUT gebrandet (dieser Stand)
2. ⏳ Sichtbares In-App-Branding (Header, Startseite, Logo)
3. ⏳ HOOKCUT-Analyse-Panel im Editor (Auto-Sync + Hook-Erkennung)
4. ⏳ Alte schwache Editier-Bausteine (effects_grading, Untertitel-Einbrennen)
   ablösen — der Editor übernimmt das jetzt besser
