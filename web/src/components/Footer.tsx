import { Link } from "react-router-dom";

/** Fusszeile mit den Pflichtlinks.
 *
 * Impressum und Datenschutzerklaerung muessen von JEDER Seite aus in
 * hoechstens zwei Klicks erreichbar sein - auch von der Anmeldemaske, denn
 * dort ist man noch kein Mitglied. Deshalb steht diese Zeile im AppShell
 * (angemeldet) UND im AuthScreen (abgemeldet).
 *
 * Die Links muessen als Text lesbar sein, nicht als Bild, und sie duerfen
 * nicht hinter einem Menue versteckt sein.
 */
export default function Footer() {
  return (
    <footer className="border-t border-ink-800 px-8 py-4 mt-8">
      <nav className="flex flex-wrap items-center justify-center gap-x-5 gap-y-2 text-xs text-ink-600">
        <Link to="/impressum" className="hover:text-muted transition-colors">
          Impressum
        </Link>
        <Link to="/datenschutz" className="hover:text-muted transition-colors">
          Datenschutz
        </Link>
        <Link to="/agb" className="hover:text-muted transition-colors">
          Nutzungsbedingungen
        </Link>
      </nav>
    </footer>
  );
}
