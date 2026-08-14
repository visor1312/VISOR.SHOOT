# selfsign — Marke

**Name:** selfsign (klein geschrieben, immer)
**Claim:** *Sign yourself.*
**Bildmarke:** drei aufsteigende Signalbalken, die in eine Unterschrift
übergehen — Signal (Authentifizierung) + Signatur (eigene Handlung) =
selbst signierte Identität.

---

## Das Original-Logo einsetzen

> **Wichtig:** Das Logo im Projekt ist **nachgebaut**, nicht das Original.
> Ich kann Bilder aus dem Chat nur *ansehen*, nicht als Datei speichern —
> also habe ich die Kurven nach Augenmaß nachgezogen. Das wird ähnlich, nie
> identisch. Die Originaldatei muss von deinem Rechner kommen.

### Der einfache Weg: Datei draufziehen

**Zieh deine Logodatei mit der Maus auf `logo-einsetzen.bat`** und lass sie
los. Das Skript legt sie an die richtige Stelle, räumt die alte weg und
fragt, ob es sie gleich ins Projekt speichern und hochladen soll.

*Nicht doppelklicken* — dann weiß es nicht, welche Datei gemeint ist.

Danach im Browser einmal **Strg+F5**. Fertig.

### Welche Dateien sich lohnen

Von deinem Marken-Blatt kannst du bis zu drei einsetzen:

| Datei | Wofür | Nötig? |
|---|---|---|
| `selfsign-mark.svg` | nur die Bildmarke (Balken + Unterschrift) | **ja** |
| `selfsign-lockup-h.svg` | Marke **neben** dem Schriftzug (waagerecht) | empfohlen |
| `selfsign-lockup-v.svg` | Marke **über** dem Schriftzug (senkrecht) | empfohlen |

Die beiden Lockups lohnen sich, weil dann auch der **Schriftzug im
Original-Font** erscheint. Ohne sie setzt die Oberfläche „selfsign" in der
System-Schrift daneben — nah dran, aber nicht dasselbe.

Fehlt eine Lockup-Datei, fällt die Oberfläche still auf Marke + Text zurück.
Es geht also nichts kaputt, wenn du nur die Bildmarke hast.

### Der Weg über den Chat

Wenn deine Logodatei eine **SVG** ist, geht es auch ohne `.bat`: SVG ist
Text. Rechtsklick auf die Datei → *Öffnen mit* → *Editor*, alles markieren
(Strg+A), kopieren (Strg+C) und mir hier in den Chat einfügen. Dann schreibe
ich sie Zeichen für Zeichen ins Projekt — das ist dann wirklich das Original.

### Format

Am besten **SVG** — bleibt in jeder Größe scharf, auch als Tab-Symbol.
Eine **PNG mit durchsichtigem Hintergrund** geht auch; `logo-einsetzen.bat`
kommt mit beidem klar.

Brauchst du später eine schwarze oder weiße Fassung für helle Hintergründe,
sag Bescheid — dann baue ich die Umschaltung ein.

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
