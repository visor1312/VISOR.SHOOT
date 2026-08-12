import RechtsSeite, { Abschnitt } from "../components/RechtsSeite";

/** Datenschutzerklaerung (DSGVO).
 *
 * Bewusst nah an dem, was der Code TATSAECHLICH tut - eine Erklaerung, die
 * Dinge auffuehrt, die es gar nicht gibt (Analyse-Werkzeuge, Newsletter,
 * Social-Plugins), ist schlechter als keine. Grundlage sind die Tabellen aus
 * backend/db.py: users, sessions, profiles, posts, comments, follows,
 * post_interests, login_attempts, reports.
 *
 * Wird der Funktionsumfang erweitert (E-Mail-Versand, Zahlungen, Analyse),
 * MUSS diese Seite mitwachsen.
 */
export default function DatenschutzPage() {
  return (
    <RechtsSeite titel="Datenschutzerklärung" stand="August 2026">
      {(b) => (
        <>
          <Abschnitt titel="Verantwortlich">
            <p>
              {b.name}
              <br />
              {b.strasse}, {b.plz} {b.ort}, {b.land}
              <br />
              E-Mail:{" "}
              <a className="text-brand-400 hover:underline"
                href={`mailto:${b.email}`}>{b.email}</a>
            </p>
          </Abschnitt>

          <Abschnitt titel="Welche Daten wir verarbeiten">
            <p>
              <strong className="text-white">Beim Anlegen eines Kontos:</strong>{" "}
              E-Mail-Adresse, Anzeigename und Passwort. Das Passwort wird
              niemals im Klartext gespeichert, sondern nur als kryptografischer
              Hash (bcrypt). Solange die Registrierung nur mit Einladung möglich
              ist, wird zusätzlich der verwendete Einladungscode gespeichert.
            </p>
            <p>
              <strong className="text-white">Im Profil:</strong> Künstlername,
              Kurzbeschreibung, Ort, Genres und Links – alles freiwillig und
              jederzeit änderbar.
            </p>
            <p>
              <strong className="text-white">Beiträge und Mitwirkung:</strong>{" "}
              Titel, Beschreibung, Kategorien, Genres, BPM und hochgeladene
              Hörproben; außerdem Kommentare, wem Sie folgen und bei welchen
              Beiträgen Sie Interesse gezeigt haben.
            </p>
            <p>
              <strong className="text-white">Bei Meldungen:</strong> Wenn Sie
              einen Inhalt melden, speichern wir, was Sie gemeldet haben, den
              gewählten Grund, Ihre Anmerkung und Ihr Konto – sonst ließe sich
              die Meldung nicht bearbeiten.
            </p>
            <p>
              <strong className="text-white">Zur Anmeldung:</strong> ein
              Sitzungsmerkmal (Cookie) sowie – bei Fehlversuchen – die Anzahl
              fehlgeschlagener Anmeldungen zu einer E-Mail-Adresse. Das schützt
              Konten vor dem systematischen Durchprobieren von Passwörtern.
            </p>
            <p>
              <strong className="text-white">Beim Aufruf der Seite:</strong>{" "}
              technische Zugriffsdaten wie IP-Adresse, Zeitpunkt und
              aufgerufene Adresse. Sie entstehen beim Betrieb des Servers und
              werden nicht mit Ihrem Konto zusammengeführt.
            </p>
            <p>
              <strong className="text-white">Beim Anlegen eines Kontos</strong>{" "}
              speichern wir zusätzlich für <strong className="text-white">eine
              Stunde</strong> die IP-Adresse, von der aus das Konto angelegt
              wurde. Damit begrenzen wir, wie viele Konten von einem Anschluss
              pro Stunde entstehen können – sonst ließe sich die Plattform
              automatisiert mit Konten fluten. Nach einer Stunde wird der
              Eintrag gelöscht; er wird zu nichts anderem verwendet.
            </p>
          </Abschnitt>

          <Abschnitt titel="Wozu und auf welcher Rechtsgrundlage">
            <p>
              Konto, Profil, Beiträge und Kommentare verarbeiten wir, um Ihnen
              die Plattform bereitzustellen – Art. 6 Abs. 1 lit. b DSGVO
              (Erfüllung des Nutzungsvertrags).
            </p>
            <p>
              Anmeldeschutz, die Bearbeitung von Meldungen, Missbrauchsabwehr
              und der technische Betrieb stützen sich auf unser berechtigtes
              Interesse an einem sicheren und funktionierenden Dienst –
              Art. 6 Abs. 1 lit. f DSGVO.
            </p>
          </Abschnitt>

          <Abschnitt titel="Cookies">
            <p>
              Wir setzen genau ein Cookie: das Sitzungsmerkmal, mit dem Sie
              angemeldet bleiben. Es ist für den Browser nicht auslesbar
              (HttpOnly), wird nur an unsere eigene Adresse gesendet
              (SameSite) und läuft nach 30 Tagen ab. Beim Abmelden wird es
              gelöscht.
            </p>
            <p>
              <strong className="text-white">
                Es gibt keine Werbe-Cookies, keine Analyse-Werkzeuge, kein
                Tracking und keine Social-Media-Plugins.
              </strong>{" "}
              Deshalb gibt es auch kein Cookie-Banner – für ein technisch
              notwendiges Cookie ist keine Einwilligung erforderlich.
            </p>
          </Abschnitt>

          <Abschnitt titel="Wer sonst noch Daten sieht">
            <p>
              Wir verkaufen keine Daten und geben sie nicht zu Werbezwecken
              weiter. Für den technischen Betrieb setzen wir ein:
            </p>
            <p>
              <strong className="text-white">Hosting:</strong> {b.hoster_name},{" "}
              {b.hoster_ort}. Die Server, auf denen Ihre Daten liegen, stehen in{" "}
              {b.hoster_region}. Da es sich um ein US-amerikanisches Unternehmen
              handelt, ist ein Zugriff aus den USA nicht vollständig
              auszuschließen; die Zusammenarbeit erfolgt auf Grundlage eines
              Auftragsverarbeitungsvertrags mit Standardvertragsklauseln.
            </p>
            <p>
              <strong className="text-white">Sicherung:</strong> Zur Sicherung
              gegen Datenverlust kann eine verschlüsselte Kopie der Datenbank
              bei Cloudflare (Cloudflare, Inc., USA) gespeichert werden.
            </p>
          </Abschnitt>

          <Abschnitt titel="Was öffentlich ist">
            <p>
              Ihr Profil, Ihre Beiträge, Ihre Hörproben und Ihre Kommentare sind
              für alle angemeldeten Mitglieder sichtbar – das ist der Zweck
              eines Netzwerks. Zeigen Sie Interesse an einem Beitrag, sieht die
              Person, die ihn verfasst hat, Ihren Namen und Ihr Profil; alle
              anderen sehen nur die Anzahl der Interessierten.
            </p>
            <p>
              Ihre E-Mail-Adresse ist <strong className="text-white">nicht</strong>{" "}
              öffentlich und wird anderen Mitgliedern nicht angezeigt.
            </p>
          </Abschnitt>

          <Abschnitt titel="Wie lange wir speichern">
            <p>
              Solange Ihr Konto besteht. Löschen Sie Ihr Konto, werden Konto,
              Profil, Beiträge, Hörproben und Kommentare gelöscht – dauerhaft
              und ohne Wiederherstellungsmöglichkeit. Sicherungskopien können
              die Daten noch bis zu 30 Tage enthalten, bevor sie überschrieben
              werden.
            </p>
          </Abschnitt>

          <Abschnitt titel="Ihre Rechte">
            <p>
              Sie haben das Recht auf Auskunft (Art. 15), Berichtigung
              (Art. 16), Löschung (Art. 17), Einschränkung der Verarbeitung
              (Art. 18), Datenübertragbarkeit (Art. 20) und Widerspruch
              (Art. 21 DSGVO).
            </p>
            <p>
              Ihr Konto können Sie jederzeit selbst löschen – unter
              „Einstellungen". Für alles Weitere genügt eine E-Mail an{" "}
              <a className="text-brand-400 hover:underline"
                href={`mailto:${b.email}`}>{b.email}</a>.
            </p>
            <p>
              Sie können sich außerdem bei einer Datenschutz-Aufsichtsbehörde
              beschweren. Zuständig ist die Landesbeauftragte für Datenschutz
              und Informationsfreiheit Nordrhein-Westfalen.
            </p>
          </Abschnitt>
        </>
      )}
    </RechtsSeite>
  );
}
