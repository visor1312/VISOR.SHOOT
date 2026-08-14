# Am PC weitermachen — Schritt für Schritt

Diese Datei ist für den Moment, in dem du den Rechner anmachst und wissen
willst: *Was muss ich tun, damit alles aktuell ist und ich vor der Oberfläche
sitze?* Alles andere steht in `README.md` (Bedienung) und
`PROJEKT-STATUS.md` (Technik).

---

## 1. Aktualisieren und starten — ein Doppelklick

**`update-selfsign.bat` doppelklicken.** Das war's. Das Skript macht der Reihe
nach:

1. holt die neuen Änderungen (`git pull`),
2. installiert neue Python-Pakete nach,
3. installiert neue Oberflächen-Pakete nach (`npm install` im Ordner `web`),
4. startet Backend und Oberfläche in zwei Fenstern,
5. öffnet den Browser auf `http://localhost:5173`.

Es öffnen sich **drei Fenster**: zwei schwarze (Backend und Oberfläche — die
müssen offen bleiben) und der Browser. Zum Beenden später einfach die beiden
schwarzen Fenster schließen.

> **Wichtig:** Immer über `http://localhost:5173` einloggen, nicht über
> `127.0.0.1:5173`. Die Anmeldung ist an die Adresse gebunden.

**An der Datenbank musst du nichts machen.** Die neue Abo-Tabelle legt der
Server beim Start selbst an. Deine Projekte, Reels und dein Konto bleiben
unangetastet.

---

## 2. Was du nach dem Start siehst

Auf deinem eigenen Rechner kostet weiterhin nichts etwas: es sind deine
Werkzeuge und deine Rechenzeit. Die Bezahlschranke ist lokal **aus**
(`HOOKCUT_PREMIUM_REQUIRED=0`).

Sichtbar geändert hat sich:

* **Alles heißt jetzt selfsign** — Logo, Farben, Name, auch die
  `.bat`-Dateien (`start-selfsign.bat`, `update-selfsign.bat`, …).
* **Das Logo ist von mir nachgebaut, nicht das Original.** Ich kann Bilder
  aus dem Chat nur ansehen, nicht als Datei speichern. **Zieh deine
  Original-Logodatei auf `logo-einsetzen.bat`** — das setzt sie ein und
  fragt, ob sie gleich mit hochgeladen werden soll. Details: `MARKE.md`.
* **Die Startseite ist „Offene Projekte"** (der Feed), nicht mehr das
  Dashboard. Das Dashboard steht weiterhin in der Seitenleiste und hat eine
  eigene Adresse (`/dashboard`).
* **Das Dashboard heißt „Deine Sachen"** und ist jetzt eine einzige Liste:
  alles, was du erstellt hast — Reels, Wochen-Content, Canvas,
  Hook-Analysen, Aufnahmen — neueste zuerst, mit Status und Download.
  Die Zahlen-Kacheln sind weg; sie haben nie etwas gesagt.
* In der Seitenleiste stand unter deinem Namen früher hartkodiert „Free Plan".
  Jetzt steht dort, was der Server wirklich über das Konto sagt — bei dir
  „Admin".
* Es gibt eine neue Seite `http://localhost:5173/premium`. Die kannst du dir
  jederzeit ansehen; lokal steht sie nur nicht im Menü, weil sie hier keinen
  Sinn ergäbe.

---

## 3. Das Neue ausprobieren

### a) Abos von Hand vergeben

**`selfsign-abo.bat` doppelklicken.** Ein Menü mit fünf Punkten:

1. Alle Abos anzeigen
2. Premium freischalten (1 Monat)
3. Premium freischalten (12 Monate)
4. Premium unbefristet — für dein eigenes Konto und für Tests
5. Premium beenden

Bei 2–5 fragt es nach der E-Mail-Adresse des Kontos. Probier ruhig durch:
freischalten, Liste ansehen, beenden, Liste ansehen. Es ist deine Datenbank,
kaputtgehen kann nichts.

Zwei Dinge, die absichtlich so sind:

* **Freischalten verlängert, es überschreibt nicht.** Zweimal „1 Monat"
  hintereinander ergibt zwei Monate, keine Verkürzung.
* **Beenden löscht nicht**, es setzt auf „abgelaufen". So bleibt sichtbar,
  dass jemand mal Kunde war.

### b) Sehen, was ein Kunde ohne Abo sieht

**`selfsign-premium-test.bat` doppelklicken.** Startet selfsign genau einmal mit
den Einstellungen, die online gelten. Dein Konto hat kein Abo, also siehst du
das, was ein neuer Nutzer sieht:

* „Wochen-Content" und „Dashboard" zeigen die Bezahlschranke statt des
  Werkzeugs,
* in der Seitenleiste steht „Kostenlos",
* der Knopf „Reel erstellen" ist weg (er würde ins Leere fassen),
* die Werkzeug-Einträge bleiben aber **sichtbar** — wer nicht sieht, was er
  kaufen könnte, kauft es nicht.

Dann `selfsign-abo.bat` → Punkt **4** → deine E-Mail → im Browser **F5**. Jetzt
bist du durch, und alles funktioniert wie gewohnt.

**Zum Zurückschalten:** Fenster schließen und wieder ganz normal mit
`start-selfsign.bat` (oder `update-selfsign.bat`) starten. Der Testmodus gilt
nur für den einen Start, an deinen Daten ändert er nichts.

---

## 4. Wenn etwas schiefgeht

| Was du siehst | Was zu tun ist |
|---|---|
| `No module named 'bcrypt'` o.ä. im Backend-Fenster | `update-selfsign.bat` nochmal — der pip-Schritt war wohl nicht durch |
| `Cannot find module` im Frontend-Fenster | Ordner `web` → `npm install` (macht `update-selfsign.bat` jetzt mit) |
| Browser zeigt „Seite nicht erreichbar" | Die zwei schwarzen Fenster brauchen ein paar Sekunden. Neu laden. |
| Fehler beim `git pull` | Meldung im Fenster abfotografieren und mir schicken — nicht raten |
| Anmeldung geht nicht | `selfsign-passwort-reset.bat` |

Das Backend-Fenster ist die ehrlichste Auskunft: Was dort rot steht, ist der
eigentliche Fehler.

---

## 5. Mit Claude Code am PC weiterarbeiten

Claude Code im Projektordner starten. Der Einstiegssatz, der immer passt:

> „Lies CLAUDE.md, PROJEKT-STATUS.md und PHASE-3-PLAN.md und sag mir, wo wir
> stehen."

Der Zweig, auf dem alles liegt: **`claude/rap-video-auto-editor-s9xfvt`**.
`update-selfsign.bat` zeigt ihn beim Start an — steht dort etwas anderes,
sag Bescheid, bevor du weitermachst.

**Wo der Stand dokumentiert ist:**

* `PHASE-3-PLAN.md` — die beiden Entscheidungen (dein PC rendert, Paddle
  kassiert) und der Bauplan in sieben Schritten
* `PROJEKT-STATUS.md`, Abschnitt „Phase 3: Premium-Abo" — was Schritt 1 und 2
  genau gebaut haben, inklusive der Fehler, die dabei gefunden wurden
* `README.md`, Abschnitt „Premium-Abo (Handbetrieb)" — die Bedienung
* `MARKE.md` — Logo, Farben, Claim. **Und wie du das Original-Logo
  eintauschst: eine Datei ersetzen, sonst nichts.**

**Als Nächstes dran** (Schritt 3 und 4 aus dem Plan): der Auftrags-Vertrag
wird umgebaut, damit dein PC die Aufträge aus der Cloud abholen kann, und
dazu der Render-Agent für Windows. Das ist der Teil, der aus „online kann
niemand etwas bestellen" ein funktionierendes Produkt macht.
