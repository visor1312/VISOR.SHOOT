import { useEffect, useState, type ReactNode } from "react";
import { Loader2 } from "lucide-react";
import { getBetreiber, type Betreiber } from "../api";

/** Gemeinsames Geruest fuer Impressum, Datenschutz und Nutzungsbedingungen.
 *
 * Die Betreiberangaben kommen vom Server (backend/betreiber.py), damit sie
 * an einer einzigen Stelle gepflegt werden. Deshalb bekommen die Seiten
 * ihren Inhalt als Funktion: er wird erst gebaut, wenn die Angaben da sind.
 */
export default function RechtsSeite({
  titel,
  stand,
  children,
}: {
  titel: string;
  /** Datum der letzten Aenderung - bei Rechtstexten ueblich und nuetzlich. */
  stand: string;
  children: (betreiber: Betreiber) => ReactNode;
}) {
  const [daten, setDaten] = useState<Betreiber | null>(null);
  const [fehler, setFehler] = useState("");

  useEffect(() => {
    let abgebrochen = false;
    getBetreiber()
      .then((b) => !abgebrochen && setDaten(b))
      .catch((e) => !abgebrochen && setFehler(e instanceof Error ? e.message : String(e)));
    return () => { abgebrochen = true; };
  }, []);

  return (
    <main className="flex-1 min-w-0 px-8 py-7 max-w-3xl">
      <h1 className="text-2xl font-bold tracking-tight">{titel}</h1>
      <p className="text-xs text-ink-600 mt-1">Stand: {stand}</p>

      {fehler && (
        <p className="mt-6 text-sm text-red-400">
          Die Angaben konnten nicht geladen werden: {fehler}
        </p>
      )}
      {!daten && !fehler && (
        <Loader2 size={20} className="text-brand-400 animate-spin mt-8" />
      )}
      {daten && <div className="mt-6 space-y-6 text-sm">{children(daten)}</div>}
    </main>
  );
}

/** Ueberschrift innerhalb eines Rechtstextes. */
export function Abschnitt({ titel, children }: { titel: string; children: ReactNode }) {
  return (
    <section className="space-y-2">
      <h2 className="text-base font-semibold text-white">{titel}</h2>
      <div className="space-y-2 text-muted leading-relaxed">{children}</div>
    </section>
  );
}
