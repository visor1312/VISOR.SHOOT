# selfsign — Marke

**Name:** selfsign (klein geschrieben, immer)
**Claim:** *Sign yourself.*
**Bildmarke:** drei aufsteigende Signalbalken, die in eine Unterschrift
übergehen — Signal (Authentifizierung) + Signatur (eigene Handlung) =
selbst signierte Identität.

---

## Das Logo austauschen — ein Handgriff

> **Wichtig:** Die Bildmarke im Projekt ist **nachgebaut**, nicht die
> Originaldatei. Ich habe sie anhand deines Marken-Blatts rekonstruiert; sie
> trifft die Idee und die Proportionen, ist aber nicht Kurve für Kurve
> identisch.

**So wird sie exakt:** die Originaldatei über diese Datei kopieren —

```
web/public/selfsign-mark.svg
```

Dateiname genau so beibehalten. Danach ziehen automatisch mit:

* die Seitenleiste (oben links)
* die Anmeldemaske und der Ladebildschirm
* das Symbol im Browser-Tab

Kein Code muss angefasst werden. Am besten eine **SVG** — die bleibt in jeder
Größe scharf. Zur Not tut es auch eine PNG mit durchsichtigem Hintergrund;
dann muss in `web/index.html` und `web/src/components/Logo.tsx` die Endung
angepasst werden.

Brauchst du zusätzlich eine schwarze oder weiße Fassung (für helle
Hintergründe), leg sie als `selfsign-mark-schwarz.svg` bzw.
`selfsign-mark-weiss.svg` daneben — dann baue ich die Umschaltung ein.

---

## Farben

| Rolle | Name | Wert | Wo im Code |
|---|---|---|---|
| Akzent | Acid Lime | `#B7FF00` | `--color-brand-500` |
| Akzent hell | — | `#C9FF4D` | `--color-brand-400` (Text auf Dunkel) |
| Akzent gedrückt | — | `#93CC00` | `--color-brand-600` (Knopf-Hover) |
| Grund | Ink Black | `#050505` | `--color-ink-950` |
| Fließtext | Off-White | `#F7F7F5` | `--color-off-white` |

Alle Tokens stehen in `web/src/index.css`. Die Grauwerte dazwischen
(`ink-900` bis `ink-600`) sind bewusst **neutral** — neben einem so lauten
Grün wirkt jeder Farbstich im Hintergrund schmutzig. Acid Lime soll die
einzige Farbe im Bild sein; deshalb ist auch der Avatar nicht mehr orange.

**Regel für Text auf Lime:** immer Ink Black (`text-ink-950`), nie Weiß.
Acid Lime ist so hell, dass weißer Text darauf unlesbar wird.

---

## Was noch HOOKCUT heißt — und warum

Umbenannt wurde alles, was ein Mensch zu sehen bekommt: Oberfläche,
Fehlermeldungen, Doku, `.bat`-Dateien, Rechtstexte, Mails.

**Bewusst nicht umbenannt** (Technik, kein Markenname):

| Was | Warum |
|---|---|
| Umgebungsvariablen `HOOKCUT_*` | Rein interne Schalter. Ein Umbenennen wäre ein eigener, mechanischer Schritt — sag Bescheid, dann mache ich ihn mit Rückfall auf die alten Namen, damit nichts bricht. |
| Cookie `hookcut_session` | Umbenennen meldet alle angemeldeten Nutzer ab. |
| Festplatten-Pfad `/var/hookcut` beim Hosting | Daran hängen die Daten. Ein neuer Pfad = neue, leere Platte. |

---

## Schriftzug

Der Schriftzug „selfsign" ist im Original eine eigene geometrische Schrift.
In der Oberfläche steht er zurzeit in der System-Schrift, klein geschrieben
und leicht enger gesetzt (`web/src/components/Logo.tsx`). Das ist nah dran,
aber nicht dasselbe. Wenn du die Schriftdatei hast, leg sie in
`web/public/schrift/` — dann binde ich sie ein.
