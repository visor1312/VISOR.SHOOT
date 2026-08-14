import { useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { CheckCircle2, Loader2, XCircle } from "lucide-react";
import { verifyEmail } from "../api";

type Stand = "laeuft" | "geschafft" | "fehler";

/** Zielseite des Bestaetigungslinks aus der E-Mail (/bestaetigen?token=...).
 *
 * Bewusst OHNE Anmeldepflicht: der Link wird meistens auf dem Handy
 * geoeffnet, waehrend man am Rechner angemeldet ist. Das Token im Link ist
 * der Nachweis.
 */
export default function BestaetigenPage() {
  const [parameter] = useSearchParams();
  const token = parameter.get("token") ?? "";
  const [stand, setStand] = useState<Stand>("laeuft");
  const [fehler, setFehler] = useState("");
  // React startet Effekte im Entwicklungsmodus doppelt. Das Token gilt aber
  // nur EINMAL - ohne diese Sperre wuerde der zweite Aufruf scheitern und
  // eine erfolgreiche Bestaetigung als Fehler anzeigen.
  const schonVersucht = useRef(false);

  useEffect(() => {
    if (schonVersucht.current) return;
    schonVersucht.current = true;

    if (!token) {
      setStand("fehler");
      setFehler("In der Adresse fehlt der Bestätigungscode. Bitte den Link aus der E-Mail vollständig öffnen.");
      return;
    }
    verifyEmail(token)
      .then(() => setStand("geschafft"))
      .catch((e) => {
        setStand("fehler");
        setFehler(e instanceof Error ? e.message : String(e));
      });
  }, [token]);

  return (
    <div className="min-h-screen bg-ink-950 text-white flex items-center justify-center p-4">
      <div className="w-full max-w-md text-center">
        {stand === "laeuft" && (
          <>
            <Loader2 size={32} className="text-brand-400 animate-spin mx-auto" />
            <p className="text-muted mt-4">E-Mail-Adresse wird bestätigt …</p>
          </>
        )}

        {stand === "geschafft" && (
          <>
            <CheckCircle2 size={40} className="text-brand-400 mx-auto" />
            <h1 className="text-2xl font-bold tracking-tight mt-4">
              Adresse bestätigt
            </h1>
            <p className="text-muted mt-2 leading-relaxed">
              Danke! Du kannst jetzt loslegen – Projekte posten, kommentieren
              und dich mit anderen Musikern verbinden.
            </p>
            <Link to="/"
              className="inline-block mt-6 bg-brand-500 hover:bg-brand-600 text-ink-950 font-semibold text-sm px-5 py-2.5 rounded-xl transition-colors">
              Zu selfsign
            </Link>
          </>
        )}

        {stand === "fehler" && (
          <>
            <XCircle size={40} className="text-red-400 mx-auto" />
            <h1 className="text-2xl font-bold tracking-tight mt-4">
              Das hat nicht geklappt
            </h1>
            <p className="text-muted mt-2 leading-relaxed">{fehler}</p>
            <p className="text-sm text-ink-600 mt-4">
              Melde dich an und fordere unter „Einstellungen" einen neuen Link an.
            </p>
            <Link to="/"
              className="inline-block mt-6 text-sm px-5 py-2.5 rounded-xl bg-ink-800 hover:bg-ink-700 transition-colors">
              Zur Anmeldung
            </Link>
          </>
        )}
      </div>
    </div>
  );
}
