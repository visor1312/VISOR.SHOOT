import RechtsSeite, { Abschnitt } from "../components/RechtsSeite";

/** Nutzungsbedingungen.
 *
 * Der wichtigste Abschnitt ist "Rechte an deinen Inhalten": Musikerinnen und
 * Musiker laden hier Hoerproben hoch, oft mit fremden Beats oder Samples.
 * Deshalb steht klar drin, dass die Rechte beim Urheber bleiben, dass man
 * nur hochladen darf, woran man die Rechte hat, und welche Erlaubnis die
 * Plattform braucht, um den Beitrag ueberhaupt anzeigen zu koennen.
 */
export default function AgbPage() {
  return (
    <RechtsSeite titel="Nutzungsbedingungen" stand="August 2026">
      {(b) => (
        <>
          <Abschnitt titel="1. Worum es geht">
            <p>
              {b.plattform_name} ist ein Netzwerk für Musikerinnen und Musiker.
              Mitglieder veröffentlichen offene Projekte – etwa „mir fehlt noch
              ein Refrain" – und finden andere, die daran mitarbeiten. Die
              Nutzung ist kostenlos. Anbieter ist {b.name}, {b.strasse},{" "}
              {b.plz} {b.ort}.
            </p>
          </Abschnitt>

          <Abschnitt titel="2. Konto">
            <p>
              Für die Nutzung ist ein Konto nötig. Die Angaben dabei müssen
              zutreffend sein. Das Passwort ist geheim zu halten; das Konto darf
              nicht an Dritte weitergegeben werden. Ein Konto pro Person.
            </p>
            <p>
              Sie können Ihr Konto jederzeit ohne Angabe von Gründen unter
              „Einstellungen" löschen. Damit endet der Nutzungsvertrag.
            </p>
          </Abschnitt>

          <Abschnitt titel="3. Rechte an deinen Inhalten">
            <p>
              <strong className="text-white">
                Was Sie hochladen, bleibt Ihres.
              </strong>{" "}
              An Ihren Texten, Hörproben und sonstigen Inhalten erwerben wir
              keine Eigentumsrechte.
            </p>
            <p>
              Damit wir Ihren Beitrag überhaupt anzeigen können, räumen Sie uns
              ein einfaches, räumlich unbeschränktes und jederzeit widerrufliches
              Recht ein, den Inhalt auf der Plattform zu speichern und anderen
              Mitgliedern anzuzeigen. Dieses Recht endet, wenn Sie den Beitrag
              oder Ihr Konto löschen. Eine darüber hinausgehende Verwertung –
              Veröffentlichung außerhalb der Plattform, Weitergabe an Dritte,
              Werbung – findet nicht statt.
            </p>
            <p>
              <strong className="text-white">
                Sie dürfen nur hochladen, woran Sie die nötigen Rechte haben.
              </strong>{" "}
              Das betrifft besonders Beats, Samples und Instrumentals von
              anderen: Ein gekaufter oder kostenlos angebotener Beat erlaubt
              nicht automatisch jede Veröffentlichung. Prüfen Sie die Lizenz,
              bevor Sie etwas hochladen. Für Rechtsverletzungen haften Sie
              selbst.
            </p>
          </Abschnitt>

          <Abschnitt titel="4. Was nicht erlaubt ist">
            <p>Nicht erlaubt sind insbesondere:</p>
            <ul className="list-disc pl-5 space-y-1">
              <li>Inhalte, an denen Sie nicht die erforderlichen Rechte haben</li>
              <li>
                Beleidigungen, Bedrohungen, Hetze gegen Personen oder Gruppen
              </li>
              <li>
                Inhalte, die gegen Strafgesetze verstoßen oder Jugendliche
                gefährden
              </li>
              <li>Werbung, Spam und das massenhafte Anschreiben anderer</li>
              <li>
                automatisiertes Auslesen der Plattform sowie Versuche, ihre
                Sicherheit zu umgehen
              </li>
              <li>
                das Vortäuschen einer fremden Identität oder das Anlegen von
                Konten für andere
              </li>
            </ul>
          </Abschnitt>

          <Abschnitt titel="5. Melden und Entfernen">
            <p>
              Jeder Beitrag und jeder Kommentar lässt sich über den
              Melden-Knopf melden. Wir prüfen jede Meldung. Stellt sich ein
              Inhalt als rechtswidrig oder als Verstoß gegen diese Bedingungen
              heraus, entfernen wir ihn; bei schweren oder wiederholten
              Verstößen können wir das Konto sperren oder löschen.
            </p>
            <p>
              Wer mit einer Entscheidung nicht einverstanden ist, kann ihr per
              E-Mail an{" "}
              <a className="text-brand-400 hover:underline"
                href={`mailto:${b.email}`}>{b.email}</a>{" "}
              widersprechen.
            </p>
          </Abschnitt>

          <Abschnitt titel="6. Verfügbarkeit">
            <p>
              {b.plattform_name} ist ein junges Projekt und wird kostenlos
              angeboten. Eine bestimmte Verfügbarkeit können wir nicht zusichern;
              Wartungsarbeiten, Störungen und Weiterentwicklungen können den
              Dienst zeitweise unterbrechen.
            </p>
            <p>
              Bitte bewahren Sie eigene Kopien Ihrer Dateien auf. Hochgeladene
              Hörproben sind Arbeitsmaterial, kein Archiv.
            </p>
          </Abschnitt>

          <Abschnitt titel="7. Haftung">
            <p>
              Wir haften unbeschränkt für Vorsatz und grobe Fahrlässigkeit sowie
              bei Verletzung von Leben, Körper oder Gesundheit. Bei einfacher
              Fahrlässigkeit haften wir nur, wenn eine Pflicht verletzt wurde,
              auf deren Erfüllung Sie vertrauen durften, und begrenzt auf den
              typischerweise vorhersehbaren Schaden.
            </p>
            <p>
              Für Inhalte, die Mitglieder veröffentlichen, sind diese selbst
              verantwortlich.
            </p>
          </Abschnitt>

          <Abschnitt titel="8. Änderungen">
            <p>
              Wir können diese Bedingungen ändern, wenn es sachlich begründet
              ist – etwa weil neue Funktionen hinzukommen oder sich die
              Rechtslage ändert. Über Änderungen informieren wir vorab in der
              Anwendung. Wer nicht einverstanden ist, kann sein Konto löschen.
            </p>
          </Abschnitt>

          <Abschnitt titel="9. Schlussbestimmungen">
            <p>
              Es gilt deutsches Recht. Ist eine Bestimmung unwirksam, bleiben
              die übrigen wirksam.
            </p>
          </Abschnitt>
        </>
      )}
    </RechtsSeite>
  );
}
