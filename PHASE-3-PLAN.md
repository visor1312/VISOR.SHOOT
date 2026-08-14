# Phase 3 — Vorbereitung: Premium-Abo und Render-Agent

Stand: 13. August 2026. Zweck: **Entscheidungsgrundlage, noch keine Umsetzung.**
Was hier steht, ist recherchiert und am Code geprüft — die zwei Entscheidungen
am Anfang gehören dir, danach kann ich durchbauen.

---

## 0. Was ich vorab schon repariert habe

Beim Nachsehen im Render-Vertrag ist mir eine offene Tür aufgefallen, die nichts
mit Phase 3 zu tun hat, aber sofort weg musste:

Die drei Routen `/render/pending`, `/render/{id}/claim` und `/render/{id}/result`
haben **absichtlich kein** `require_tools()` — sie müssen auch dann antworten,
wenn der Server selbst nicht rendert. Genau das macht sie aber zu den einzigen
Werkzeug-Routen, die online offenstehen. Und `/render/{id}/result` schrieb die
hochgeladene Datei **ungedeckelt** auf die Platte: jedes angemeldete Konto hätte
die gemietete Festplatte vollschreiben können, und dann steht nicht ein Upload,
sondern der ganze Dienst.

Behoben: der gedeckelte Schreiber aus `network.py` liegt jetzt in
`backend/uploads.py` und wird von beiden Seiten benutzt. Grenze 200 MB pro Item.
Läuft sie über, wird die halbe Datei weggeräumt **und** das Item auf `pending`
zurückgesetzt — sonst hinge es für immer auf `rendering` fest.
423 Tests grün, committet und gepusht.

---

## 1. Der Befund, der alles andere bestimmt

**Der Render-Vertrag ist online derzeit tot Code.** Nicht kaputt — unerreichbar.
Die Kette, Zeile für Zeile nachgeprüft:

| Schritt | Wo | Ergebnis |
|---|---|---|
| `render.yaml` setzt `HOOKCUT_TOOLS_ENABLED=0` | `render.yaml:36` | Werkzeuge aus |
| `POST /packs` ruft `require_tools()` | `backend/main.py:804` | → **503** |
| Ohne Pack keine `pack_items` | — | — |
| `/render/pending` listet nur `pack_items` | `backend/main.py:~897` | → immer **leer** |

Belegt durch den bestehenden Test `tests/test_tools_switch.py:40`, der genau
dieses 503 auf `/packs` festhält.

Dazu kommt ein zweiter Punkt: der **Analyse**-Teil (Sync-Versatz, Hook-Erkennung,
Untertitel) läuft vor dem Rendern und braucht `librosa`, `numpy`, `scipy` und
`faster_whisper` — rund 1,5 GB, die in `requirements-server.txt` bewusst **nicht**
drin sind. Der gehostete Server kann also nicht nur nicht rendern, er kann auch
nicht analysieren.

**Konsequenz:** Bevor irgendjemand für die Render-Werkzeuge bezahlen kann, muss
entschieden werden, *wer* rendert und *wo* die Analyse läuft. Das ist keine
Programmierfrage, das ist eine Produktfrage — und sie kostet unterschiedlich viel.

---

## 2. Entscheidung A — Wer rendert? (gehört dir)

Drei Wege. Ich habe bei jedem dazugeschrieben, was er dich wirklich kostet und
was er dem Kunden abverlangt.

### Modell A — Jeder Abonnent rendert auf dem eigenen PC

Der Abonnent installiert ein kleines selfsign-Programm auf seinem Windows-Rechner.
Es meldet sich mit seinem Konto an, holt sich Aufträge, rendert, lädt das Ergebnis
hoch.

* **Deine Kosten:** praktisch null. Rohmaterial verlässt den PC des Kunden nie.
* **Datenschutz:** bestmöglich — du siehst die Videos nie.
* **Skaliert:** unbegrenzt.
* **Aber:** Windows-Zwang, Installation nötig, PC muss an sein. Für einen Musiker,
  der im Zug schnell ein Reel bauen will, ist das Modell tot. Mac- und
  Nur-Handy-Nutzer fallen komplett raus.
* **Verkaufbarkeit von 10 €/Monat:** schwierig. Man verkauft ein Abo für Software,
  die auf dem eigenen Rechner läuft — das fühlt sich an wie Miete für nichts.

### Modell B — *Dein* PC rendert für alle (meine Empfehlung für den Start)

Die Cloud nimmt Video und Song entgegen und stellt den Auftrag in eine Schlange.
Dein Windows-Rechner läuft mit einem Agenten, holt Aufträge, analysiert, rendert,
lädt hoch. Der Kunde macht alles im Browser — auch vom Handy.

* **Der Kunde installiert nichts.** Das ist das Argument, das 10 €/Monat trägt.
* **Deine Kosten:** Strom + dein PC muss laufen. Kein Cloud-Rechner.
* **Datenschutz:** ein echtes Verkaufsargument — „deine Videos werden in
  Deutschland verarbeitet und danach gelöscht". Muss in die Datenschutzerklärung.
* **Das Nadelöhr ist der Speicher, nicht die Rechenzeit.** Die gemietete Platte
  hat **5 GB** (`render.yaml:29`), Render verlangt 0,25 $ pro GB und Monat. Ein
  1080p-Handyvideo von 3 Minuten sind grob 300–500 MB. Das heißt: harte
  Obergrenze pro Upload **und** Rohmaterial nach dem Rendern automatisch löschen.
  Ohne beides ist die Platte nach einer Handvoll Aufträgen voll.
* **Aber:** Ist dein PC aus, warten die Aufträge. Das muss die Oberfläche ehrlich
  sagen („in der Warteschlange, meist innerhalb weniger Stunden fertig") — nicht
  so tun, als ginge es sofort.
* **Grenze:** irgendwo zwischen 20 und 50 zahlenden Nutzern wird ein PC eng. Das
  ist ein Luxusproblem, das man dann mit einem zweiten Agenten löst — das
  Protokoll kann von Haus aus mehrere.

### Modell C — Ein Server in der Cloud rendert

* **Der Kunde installiert nichts, nichts muss bei dir laufen.**
* **Aber:** Rendern braucht Chrome mit WebGPU. Das ist auf gemieteten Servern
  teuer und fummelig; realistisch reden wir über eine Größenordnung von 50–200 €
  im Monat, bevor der erste Kunde bezahlt hat. Bei 10 €/Monat brauchst du 5–20
  Abonnenten nur, um bei null zu sein.
* **Für später richtig. Für den Start das falsche Risiko.**

### Meine Empfehlung

**Modell B starten, Protokoll so bauen, dass A später ohne Umbau geht.** Der
Agent ist in beiden Fällen dasselbe Programm; der einzige Unterschied ist, *welche*
Aufträge er sehen darf — nur die eigenen (A) oder alle (B). Das ist eine Zeile im
Endpunkt, kein zweites Produkt.

---

## 3. Entscheidung B — Wer zieht das Geld ein? (gehört dir)

Zwei grundsätzlich verschiedene Wege. Der Unterschied ist **nicht** die Gebühr —
der Unterschied ist, wer gegenüber dem Finanzamt der Verkäufer ist.

### Weg 1 — Stripe (du bist der Verkäufer)

* Gebühr: grob 1,5 % + 0,25 € bei EU-Karten. Auf 10 € also ca. **0,40 €**.
* **Du** stellst die Rechnung, **du** schuldest die Umsatzsteuer.
* Deutsche Kunden: 19 % USt — oder gar keine, wenn du Kleinunternehmer nach
  § 19 UStG bist (seit 2025: 25.000 € Vorjahr / 100.000 € laufendes Jahr, und die
  100.000 sind eine **harte** Grenze — reißt du sie, ist der Status sofort weg,
  nicht erst nächstes Jahr).
* **Der Haken:** digitale Leistungen an Privatkunden im EU-Ausland werden im
  Land des *Kunden* besteuert. Ab 10.000 € EU-weitem Umsatz musst du ins
  **One-Stop-Shop-Verfahren** und die Umsatzsteuer jedes Kundenlandes abführen.
  Ein Österreicher, der 10 € zahlt, kann dir das einbrocken.
* Realistisch heißt das: Steuerberater, laufende Meldungen, Buchhaltung.

### Weg 2 — Merchant of Record, z. B. Paddle (der Anbieter ist der Verkäufer)

* Gebühr: grob 5 % + 0,50 $. Auf 10 € also ca. **0,95 €**.
* Paddle verkauft in eigenem Namen an deinen Kunden, zieht die jeweilige
  Landes-Umsatzsteuer ein und führt sie ab. **Du** bekommst eine Auszahlung —
  eine B2B-Leistung an eine ausländische Firma, Reverse Charge.
* Kein OSS, keine Umsatzsteuer-Meldungen pro EU-Land, keine
  Rückbuchungs-Streitereien. Chargebacks und Betrugsprüfung liegen bei Paddle.
* **Preis dafür:** ca. **0,55 € mehr pro Abonnent und Monat** als Stripe.
  Bei 20 Abonnenten sind das 11 € im Monat — deutlich weniger als eine Stunde
  Steuerberater.

### Zu Lemon Squeezy

Wird oft als die einfache Variante empfohlen — ist aber seit Juli 2024 von Stripe
gekauft und wird gerade in „Stripe Managed Payments" überführt. Die Anmeldung für
Neukunden dauert dort inzwischen Wochen statt Tage. **Ich würde es jetzt nicht mehr
neu anfangen.** Paddle ist der reifere Weg, Alternativen wären FastSpring oder Creem.

### Meine Empfehlung

**Merchant of Record (Paddle).** Die 0,55 € Aufpreis kaufen dir, dass du als
Einzelperson keine europäische Umsatzsteuer-Verwaltung betreiben musst. Das ist
bei einem 10-€-Produkt der Unterschied zwischen „läuft nebenbei" und „ist ein
Nebenjob".

**Wichtig und ehrlich:** Beide Wege verlangen ein angemeldetes Gewerbe und eine
Identitätsprüfung. Ob Kleinunternehmerregelung oder Regelbesteuerung für dich
besser ist, kann und darf ich nicht entscheiden — das ist eine Frage für einen
Steuerberater, und sie ist es wert, einmal 150 € dafür auszugeben, bevor der
erste Euro fließt.

---

## 4. Was verkaufst du eigentlich?

Der Satz „frei = Netzwerk, bezahlt = Werkzeuge" stimmt erst, wenn Entscheidung A
gefallen ist. Vorher gibt es online **keine** Werkzeuge zu verkaufen — sie laufen
nur auf deinem Rechner.

In Modell B wäre das Premium-Angebot konkret:

* **Wochen-Content:** ein Video + ein Song → mehrere fertige, geschnittene,
  untertitelte Reels in verschiedenen Stilen und Formaten. Das ist der Kern.
* **Spotify Canvas:** der 3–8-Sekunden-Loop.
* **Reels-Assistent** und **Hook-Finder** kämen danach, weil sie denselben Weg
  gehen.

Frei bleibt: Profil, Feed, offene Projekte, Kommentare, Interesse — alles, was das
Netzwerk lebendig macht. Ein Netzwerk hinter einer Bezahlschranke wächst nicht.

---

## 5. Der Bauplan in Schritten

Jeder Schritt endet grün (pytest + `npm run build` + `npm run lint`), wird
committet und gepusht. Reihenfolge ist bewusst so gewählt, dass **nach Schritt 1
schon verkauft werden kann** — von Hand, ohne Zahlungsanbieter.

### Schritt 1 — Abo-Zustand im Backend + Handschalter
*Unabhängig von beiden Entscheidungen. Kann ich sofort bauen.*

* Neue Tabelle `subscriptions` (Nutzer, Status, Plan, Laufzeit-Ende, Anbieter,
  Anbieter-IDs).
* `auth.require_premium()` als Sperre mit ehrlicher deutscher Meldung.
* `/auth/me` liefert `premium` und `premium_bis` mit.
* `selfsign-abo.bat`: Abo von Hand vergeben und entziehen.
* **Damit kannst du die ersten Kunden von Hand aufnehmen** — Rechnung per
  Überweisung oder PayPal, Abo per Doppelklick freischalten. Genau so findet man
  heraus, ob überhaupt jemand zahlen will, bevor man einen Zahlungsanbieter
  anbindet.
* Tests.

### Schritt 2 — Bezahlschranke in der Oberfläche
* Eine `/premium`-Seite: was kostet es, was bekommt man, was ist frei.
* Werkzeug-Seiten zeigen ohne Abo diese Seite statt toter Knöpfe.
* Premium-Kennzeichen im Profil.

### Schritt 3 — Auftrags-Vertrag umbauen (setzt Entscheidung A voraus)
* Vom Item-Auftrag zum **Pack-Auftrag**: der Agent übernimmt auch die Analyse,
  weil der Server sie nicht kann.
* **Agent-Token** statt Sitzungs-Cookie — auf dem Render-PC soll keine volle
  Admin-Anmeldung liegen. Eigene Tabelle, jederzeit widerrufbar.
* **`claimed_at` + Wiedervorlage.** Heute gibt es das nicht: stürzt der Agent
  mitten im Rendern ab, bleibt das Item für immer auf `rendering` und wird nie
  wieder abgeholt. (Nachgeprüft — die Spalte fehlt in `backend/db.py:281`.)
* Harte Obergrenze für hochgeladenes Rohmaterial + **automatisches Löschen nach
  dem Rendern**. Ohne das ist die 5-GB-Platte nach wenigen Aufträgen voll.
* Warteschlangen-Anzeige für den Kunden.

### Schritt 4 — Render-Agent für Windows
* `selfsign-agent.bat` zum Doppelklicken, ein Fenster, das sagt was es tut.
* Meldet sich mit dem Agent-Token an, holt Aufträge, rendert, lädt hoch.
* Übersteht Neustart und Verbindungsabbruch; ein kaputter Auftrag stoppt nicht
  die Schlange.

### Schritt 5 — Zahlungsanbieter anbinden (setzt Entscheidung B voraus)
* Checkout-Link, `POST /billing/webhook` mit **Signaturprüfung**.
* Regel ohne Ausnahme: **nur der Webhook schaltet Premium frei.** Nie das
  Frontend, nie ein Rücksprung-Link — der lässt sich fälschen.
* Kündigung, Zahlungsausfall und Rückbuchung müssen den Zustand ebenso zuverlässig
  wieder zumachen.

### Schritt 6 — Rechtliches, sobald Geld fließt
Das muss **vor dem ersten Euro** stehen, auch bei Handverkauf aus Schritt 1.

* **Kündigungsbutton (§ 312k BGB) — Pflicht.** Fehlt er, kann der Kunde jederzeit
  fristlos kündigen, und Wettbewerber können abmahnen. Der BGH hat am 16. Juli 2026
  entschieden, dass auf der Bestätigungsseite **nur** das Formular und der Knopf
  stehen dürfen — kein „willst du nicht lieber pausieren?". Das LG München I hat
  am 14. Juli 2026 zusätzlich verboten, einen Kündigungsgrund abzufragen oder das
  Formular über mehrere Schritte zu verteilen. Der Knopf muss **ohne Anmeldung**
  erreichbar sein.
* **Button-Lösung (§ 312j Abs. 3 BGB):** der Bestellknopf muss „Zahlungspflichtig
  bestellen" heißen.
* **Widerrufsbelehrung + Muster-Widerrufsformular.** Bei einem Abo, das sofort
  losgeht, erlischt das Widerrufsrecht nur, wenn der Kunde ausdrücklich zustimmt,
  **dass** es sofort losgeht, **und** bestätigt, dass er dadurch sein Widerrufsrecht
  verliert — und du ihm das anschließend per E-Mail bestätigst (§ 356 Abs. 5 BGB).
  Drei Teile, alle drei nötig.
* **AGB erweitern:** Leistungsbeschreibung, Preis inkl. USt., monatliche Laufzeit,
  Kündigungsfrist, keine Verfügbarkeitszusage (wichtig in Modell B!), was bei
  Zahlungsverzug passiert.
* **Datenschutzerklärung erweitern:** Zahlungsdienstleister als Empfänger,
  Zahlungsdaten, und in Modell B der Satz, wo das Video verarbeitet wird.
* **Impressum:** ggf. Umsatzsteuer-Identifikationsnummer.

Ich schreibe Entwürfe für all das. Ich bin kein Anwalt und darf keine
Rechtsberatung geben — bei einem Bezahlangebot mit Abmahnrisiko würde ich die
Texte einmal prüfen lassen.

### Schritt 7 — Dokumentation + dein Test
Anleitung für dich, Nutzer-Test zum Durchklicken.

---

## 6. Was bei dir bleibt

* Entscheidung A (wer rendert) und Entscheidung B (Zahlungsanbieter).
* Gewerbeanmeldung, Steuerberater, Kleinunternehmer-Frage.
* Konto beim Zahlungsanbieter samt Identitätsprüfung.
* Der Rechner, der rendert — und die Entscheidung, ob er laufen soll.
* Die Rechtstexte prüfen lassen.

## 7. Was ich ohne weitere Entscheidung sofort bauen kann

**Schritt 1** komplett — Abo-Zustand, Sperre, Handschalter. Der ist in *jedem*
Szenario gleich, egal wie A und B ausgehen, und macht das Produkt von Hand
verkaufbar.

Dazu die **Wiedervorlage aus Schritt 3** (`claimed_at`), weil der heutige Zustand
schon ohne Phase 3 ein Fehler ist: ein abgestürzter Agent blockiert ein Item für
immer.
