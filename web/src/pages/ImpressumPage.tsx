import RechtsSeite, { Abschnitt } from "../components/RechtsSeite";

/** Impressum nach § 5 DDG (loeste 2024 das TMG ab).
 *
 * Pflichtangaben: Name, ladungsfaehige Anschrift (Postfach genuegt NICHT)
 * und Angaben fuer eine schnelle elektronische Kontaktaufnahme, wozu die
 * E-Mail-Adresse zwingend gehoert. Die Angaben selbst stehen in
 * backend/betreiber.py - hier steht nur, wie sie dargestellt werden.
 */
export default function ImpressumPage() {
  return (
    <RechtsSeite titel="Impressum" stand="August 2026">
      {(b) => (
        <>
          <Abschnitt titel="Angaben gemäß § 5 DDG">
            <p>
              {b.name}
              <br />
              {b.strasse}
              <br />
              {b.plz} {b.ort}
              <br />
              {b.land}
            </p>
          </Abschnitt>

          <Abschnitt titel="Kontakt">
            <p>
              E-Mail: <a className="text-brand-400 hover:underline"
                href={`mailto:${b.email}`}>{b.email}</a>
              {b.telefon && (
                <>
                  <br />
                  Telefon: {b.telefon}
                </>
              )}
            </p>
          </Abschnitt>

          <Abschnitt titel="Verantwortlich für den Inhalt nach § 18 Abs. 2 MStV">
            <p>
              {b.name}, {b.strasse}, {b.plz} {b.ort}
            </p>
          </Abschnitt>

          <Abschnitt titel="Verbraucherstreitbeilegung">
            <p>
              Wir sind nicht bereit und nicht verpflichtet, an
              Streitbeilegungsverfahren vor einer Verbraucherschlichtungsstelle
              teilzunehmen.
            </p>
          </Abschnitt>

          <Abschnitt titel="Haftung für Inhalte von Nutzerinnen und Nutzern">
            <p>
              {b.plattform_name} ist eine Plattform, auf der Musikerinnen und
              Musiker eigene Beiträge und Hörproben veröffentlichen. Für diese
              Inhalte sind ausschließlich die jeweiligen Urheberinnen und
              Urheber verantwortlich. Wir machen uns fremde Inhalte nicht zu
              eigen.
            </p>
            <p>
              Wer einen Beitrag für rechtswidrig hält, kann ihn über den
              Melden-Knopf am Beitrag melden oder sich per E-Mail an{" "}
              <a className="text-brand-400 hover:underline"
                href={`mailto:${b.email}`}>{b.email}</a>{" "}
              wenden. Wir prüfen jede Meldung und entfernen rechtswidrige
              Inhalte, sobald wir davon Kenntnis erlangen.
            </p>
          </Abschnitt>

          <Abschnitt titel="Haftung für Links">
            <p>
              Unser Angebot kann Links zu externen Webseiten Dritter enthalten,
              auf deren Inhalte wir keinen Einfluss haben. Für diese Inhalte ist
              stets der jeweilige Anbieter verantwortlich. Werden uns
              Rechtsverletzungen bekannt, entfernen wir solche Links umgehend.
            </p>
          </Abschnitt>
        </>
      )}
    </RechtsSeite>
  );
}
