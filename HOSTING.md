# selfsign online stellen

Schritt-für-Schritt-Anleitung für den ersten Livegang. Alles, was der Server
braucht, steht schon im Projekt (`Dockerfile`, `render.yaml`,
`docker-start.sh`) — du musst nichts programmieren.

**Wichtig vorweg:** Beim ersten Livegang bleibt die Tür **zu**. Die
Registrierung geht weiterhin nur mit Einladungscode
(`HOOKCUT_INVITE_ONLY=1`). Das ist Absicht: erst alles am echten Server
prüfen, dann öffnen. Sonst stolpert der erste echte Musiker über einen Fehler,
den man selbst noch nicht kennt.

---

## 1. Konto bei Render anlegen

1. Auf <https://render.com> mit dem GitHub-Konto anmelden.
2. Render fragt, auf welche Repositories es zugreifen darf → dieses Projekt
   freigeben.

## 2. Dienst anlegen

1. Im Render-Dashboard: **New → Blueprint**.
2. Das Repository auswählen. Render liest `render.yaml` und schlägt einen
   Dienst namens `selfsign` vor.
3. **Plan prüfen:** Es muss der bezahlte **Starter**-Plan sein (~7 $/Monat).
   Grund: Nur bezahlte Pläne können eine **dauerhafte Festplatte** einbinden.
   Auf der Gratis-Stufe wären Konten, Beiträge und Hörproben nach jedem
   Neustart weg — und die Seite würde nach 15 Minuten Ruhe einschlafen, sodass
   der nächste Besucher etwa eine Minute auf eine weiße Seite starrt.
4. Auf **Apply** klicken. Der erste Bau dauert ein paar Minuten (Node baut die
   Oberfläche, Python installiert vier Pakete, ffmpeg kommt dazu).

> **Falls Render die `render.yaml` nicht annimmt** (z. B. „invalid field"):
> Die Datei konnte hier nicht gegen Renders Vorgaben geprüft werden — die
> Entwicklungsumgebung kommt nicht ins Render-Dokumentationsnetz. Dann
> einfach von Hand anlegen, das dauert zwei Minuten länger:
> **New → Web Service → Repository wählen → Language: Docker**, Plan
> **Starter**, unter **Advanced** eine **Disk** mit Mount Path `/var/hookcut`
> und 5 GB anlegen, Health Check Path `/health`, und die fünf Variablen aus
> der Tabelle unten eintragen. Sag mir die Fehlermeldung, dann passe ich die
> Datei an.

## 3. Erster Blick

Render zeigt eine Adresse der Form `https://selfsign-xxxx.onrender.com`.
Die eigene Domain kommt später — der Name muss den Start nicht aufhalten.

Diese Punkte einmal durchgehen:

| Was | Erwartung |
|---|---|
| Seite öffnen | Login-Maske erscheint |
| Registrieren ohne Code | Fehlermeldung („Einladungscode …") — die Tür ist zu |
| Registrieren **mit** Code | funktioniert, du landest bei „Offene Projekte" |
| Menü links | **keine** Video-Werkzeuge (kein Hook Generator, kein Canvas) |
| Adresse `/musiker/deinname` direkt eingeben | Profil lädt, **kein** „Not Found" |
| Beitrag mit Hörprobe anlegen | Hörprobe lässt sich abspielen |

**Der wichtigste Test überhaupt:** Im Render-Dashboard **Manual Deploy →
Restart** klicken, warten, Seite neu laden. **Dein Konto und dein Beitrag
müssen noch da sein.** Sind sie weg, ist die Festplatte nicht richtig
eingebunden — dann nicht weitermachen, sondern das zuerst klären.

## 4. Einladungscodes erzeugen

`selfsign-einladung.bat` auf deinem Rechner erzeugt Codes für die **lokale**
Datenbank — die kennt der Server nicht.

Für den Server: im Render-Dashboard beim Dienst auf **Shell** gehen und
denselben Befehl eingeben, den auch die `.bat` benutzt:

```
python -m backend.admin create-invite
```

Der ausgegebene Text ist der Einladungscode (gilt einmal). Mehrere auf
einmal: `python -m backend.admin create-invite --anzahl 5`.
Wer schon ein Konto hat, sieht die Codes auch im Verzeichnis
`python -m backend.admin list-invites`.

## 5. Sicherung einschalten (kann warten)

Ohne diesen Schritt läuft alles — aber es gibt **keine Sicherung** der
Datenbank. Sobald du ein Cloudflare-Konto hast:

1. Bei Cloudflare **R2** einen Bucket anlegen (10 GB gratis), z. B. `selfsign-backup`.
2. Dort einen API-Token mit Schreibrechten erzeugen.
3. In Render unter **Environment** drei Werte eintragen:
   - `LITESTREAM_REPLICA_URL` = `s3://selfsign-backup/db?endpoint=<deine-R2-Adresse>`
   - `LITESTREAM_ACCESS_KEY_ID`
   - `LITESTREAM_SECRET_ACCESS_KEY`
4. Neu ausrollen. Im Log muss stehen: „Litestream aktiv: …".

**Ehrlich dazu:** Litestream sichert **nur die Datenbank**, nicht die
Hörproben. Bei einem Plattenschaden wären Konten, Beiträge und Kommentare
zurückholbar, die Audiodateien nicht. Für den Start vertretbar (sie lassen
sich neu hochladen), später nachrüstbar.

---

## 6. E-Mail-Bestätigung einschalten (erst mit eigener Domain)

Neue Konten können ihre E-Mail-Adresse bestätigen müssen. **Standardmäßig ist
das aus**, und das aus einem guten Grund: Mails von einer Adresse zu
verschicken, deren Domain dafür nicht eingerichtet ist, landen im Spam oder
kommen gar nicht an — dann könnte sich niemand mehr anmelden.

**Ausprobieren geht schon jetzt, ohne Domain.** Setz auf deinem Rechner
`HOOKCUT_EMAIL_VERIFICATION=1`. Die Mail wird dann nicht verschickt, sondern
**ins schwarze Backend-Fenster geschrieben** — inklusive Bestätigungslink. Den
kopierst du heraus und rufst ihn im Browser auf. So siehst du den ganzen
Ablauf, bevor irgendetwas online steht.

**Wenn die Domain steht:**

1. Bei <https://resend.com> anmelden (3.000 Mails/Monat gratis) und die Domain
   dort eintragen. Resend zeigt dir die DNS-Einträge (SPF und DKIM), die du
   beim Domain-Anbieter hinterlegen musst. **Ohne die kommt nichts an.**
2. In Render unter **Environment** eintragen:
   - `HOOKCUT_MAIL_BACKEND` = `resend`
   - `RESEND_API_KEY` = dein Schlüssel von Resend
   - `HOOKCUT_MAIL_FROM` = z. B. `selfsign <noreply@deine-domain.de>`
   - `HOOKCUT_PUBLIC_URL` = die echte Adresse der Seite (steht im Link!)
3. Erst **danach** `HOOKCUT_EMAIL_VERIFICATION` auf `1` — und sofort selbst ein
   Testkonto anlegen, um zu sehen, ob die Mail ankommt.

Was ein unbestätigtes Konto darf: sich anmelden, alles lesen, das eigene
Profil pflegen. Was nicht: posten und kommentieren. So trifft die Hürde genau
das, wogegen sie hilft — Inhalte von Wegwerf-Adressen — und nicht den ersten
Eindruck.

**Du selbst bist ausgenommen:** Das erste Konto (deins) gilt immer als
bestätigt. Sonst könntest du dich aus deiner eigenen Plattform aussperren.

## 7. Die Tür aufmachen

Wenn der Dienst läuft, du die Rechtstexte gelesen hast und ein paar Runden
selbst gedreht hast: In Render unter **Environment** `HOOKCUT_INVITE_ONLY`
auf `0` stellen. Ab dann kann sich jeder registrieren, und das Code-Feld
verschwindet von selbst aus der Anmeldemaske.

**Lad danach fünf bis zehn Musiker ein und schau ihnen zu, ohne zu
erklären.** Wo sie hängenbleiben, ist die Antwort auf die einzige Frage, die
noch offen ist: ob das Ding im echten Leben funktioniert. Alles andere ist
bis dahin Vermutung.

Was dich dabei schützt (im Sicherheits-Durchgang gemessen, nicht vermutet):
höchstens 5 neue Konten pro Stunde und Anschluss, 10 Beiträge und 60
Kommentare pro Stunde und Person, Hörproben auf 8 MB und 30 Sekunden
begrenzt, und ein Melden-Knopf an jedem fremden Beitrag samt deiner
Arbeitsliste unter **Einstellungen → Gemeldete Inhalte**.

**Wenn etwas aus dem Ruder läuft:** `HOOKCUT_INVITE_ONLY` wieder auf `1` —
dann kommt niemand Neues mehr rein, und die vorhandenen Konten laufen
weiter.

## Was wo eingestellt wird

Alle Schalter stehen in `render.yaml` und sind im Render-Dashboard unter
**Environment** änderbar:

| Variable | Wert online | Bedeutung |
|---|---|---|
| `HOOKCUT_TOOLS_ENABLED` | `0` | Video-Werkzeuge aus (brauchen Chrome/WebGPU) |
| `HOOKCUT_LOCAL_RENDER` | `0` | dieser Server rendert nichts selbst |
| `HOOKCUT_SECURE_COOKIES` | `1` | Session-Cookie nur über HTTPS |
| `HOOKCUT_INVITE_ONLY` | `1` → später `0` | Tür zu / offen für alle |
| `HOOKCUT_API_DOCS` | `0` | technische Schnittstellen-Doku aus (nur lokal sinnvoll) |
| `HOOKCUT_TRUST_PROXY` | `1` | echte Besucher-Adresse aus dem Proxy lesen |
| `HOOKCUT_PROJECTS_DIR` | `/var/hookcut` | **muss** auf die Festplatte zeigen |

Die Datenbank landet automatisch unter `HOOKCUT_PROJECTS_DIR/state.db` — ein
Schalter verschiebt beides, Datenbank und Dateien.

## Bekannte Einschränkungen

- **Mit angehängter Festplatte rollt Render nicht unterbrechungsfrei aus.**
  Bei jedem Update ist die Seite kurz weg. Das ist der Preis dafür, dass die
  Daten ein Update überleben.
- **Die Video-Werkzeuge gibt es online nicht** und sie sind auch nicht
  geplant: Sie brauchen Chrome mit WebGPU und mehrere GB an Modellen. Sie
  bleiben auf deinem Rechner (`start-selfsign.bat`).
- **Die Rechtstexte sind nicht anwaltlich geprüft.** Impressum,
  Datenschutzerklärung, Nutzungsbedingungen, Meldeknopf und „Konto löschen"
  stehen (Phase 2, Schritt 5) und sind nah am tatsächlichen Verhalten der
  Software geschrieben. Trotzdem: **vor dem Öffnen für Fremde einmal selbst
  durchlesen**, vor allem die Nutzungsbedingungen (Rechte an Beats und
  Samples). Deine Angaben stehen in `backend/betreiber.py` bzw. als
  `HOOKCUT_BETREIBER_*` in den Umgebungsvariablen — eine Adressänderung
  braucht kein Programmieren und kein neues Ausrollen.
- **Gemeldete Inhalte** landen bei dir unter **Einstellungen → Gemeldete
  Inhalte**. Dort entscheidest du je Meldung „Ausblenden" oder „Ist in
  Ordnung". Da schaust du nach dem Öffnen regelmäßig rein — eine liegen
  gebliebene Meldung ist genau das, was bei einer Beschwerde zählt.

## Was hier geprüft wurde und was nicht

Geprüft (in der Entwicklungsumgebung, mit exakt der Ordnerstruktur des
Images und nur den vier Server-Paketen): Oberfläche wird ausgeliefert,
Direktaufruf von Unterseiten landet nicht im 404, Werkzeuge sind aus,
Registrierung ohne Code wird abgewiesen, Beitrag samt Hörprobe funktioniert,
und Datenbank wie Hörproben landen im Datenordner statt im Programmordner.

**Nicht geprüft:** der Bau des Docker-Images selbst (die Entwicklungsumgebung
darf keine Docker-Basis-Images herunterladen) und alles am echten Server —
HTTPS, das `Secure`-Flag im echten Browser, die Festplatte über einen Neustart
hinweg. Genau dafür ist die Liste in Abschnitt 3 da.
