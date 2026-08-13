import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { CalendarClock, Check, Film, Mail, Music2, Users2, Zap } from "lucide-react";
import { getBetreiber, type Betreiber } from "../api";
import { useApp } from "../components/app-context";

/** Was Premium kostet, was dazugehoert und was frei bleibt.
 *
 *  Bewusst OHNE Bestellknopf: solange die Abos von Hand vergeben werden
 *  (siehe README, "Premium-Abo (Handbetrieb)"), kommt hier kein Vertrag
 *  online zustande - es steht eine E-Mail-Adresse da. Ein Knopf, der
 *  zahlungspflichtig bestellt, braucht die Button-Loesung nach
 *  § 312j Abs. 3 BGB, eine Widerrufsbelehrung und einen Kuendigungsbutton
 *  nach § 312k BGB. Das kommt zusammen mit dem Zahlungsanbieter
 *  (PHASE-3-PLAN.md, Schritte 5 und 6) - nicht halb. */
export default function PremiumPage() {
  const { user } = useApp();
  const [betreiber, setBetreiber] = useState<Betreiber | null>(null);

  useEffect(() => {
    let abgebrochen = false;
    getBetreiber()
      .then((b) => !abgebrochen && setBetreiber(b))
      .catch(() => { /* ohne Adresse bleibt der Abschnitt einfach leer */ });
    return () => { abgebrochen = true; };
  }, []);

  const preis = (user.preis_cent / 100).toLocaleString("de-DE", {
    style: "currency", currency: user.waehrung || "EUR",
  });

  return (
    <main className="flex-1 px-8 py-8 max-w-4xl">
      <h1 className="text-2xl font-bold tracking-tight">HOOKCUT Premium</h1>
      <p className="text-muted mt-1.5 max-w-2xl">
        Das Netzwerk ist und bleibt kostenlos. Bezahlt werden die
        Video-Werkzeuge – sie rechnen für dich, und zwar auf echter Hardware.
      </p>

      {user.premium && <LaeuftHinweis bis={user.premium_bis} status={user.premium_status} />}

      <div className="mt-6 grid gap-4 md:grid-cols-2">
        <div className="bg-ink-850 border border-brand-500/40 rounded-2xl p-6">
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-bold tracking-tight">{preis}</span>
            <span className="text-muted text-sm">pro Monat</span>
          </div>
          <p className="text-sm text-muted mt-1">Monatlich kündbar.</p>
          <ul className="mt-5 space-y-3">
            <Leistung icon={CalendarClock} titel="Wochen-Content">
              Ein Video und ein Song werden zu mehreren fertigen, geschnittenen
              und untertitelten Reels – genug für eine ganze Woche.
            </Leistung>
            <Leistung icon={Film} titel="Spotify Canvas">
              Der kurze stumme 9:16-Loop, der auf Spotify das Cover ersetzt.
            </Leistung>
            <Leistung icon={Zap} titel="Hook Generator">
              Findet die Stelle im Song, die als Erstes sitzt.
            </Leistung>
            <Leistung icon={Music2} titel="Reel-Assistent">
              Video und Song hochladen, den Rest macht HOOKCUT.
            </Leistung>
          </ul>
        </div>

        <div className="bg-ink-850 border border-ink-700 rounded-2xl p-6">
          <h2 className="font-semibold flex items-center gap-2">
            <Users2 size={18} className="text-brand-400" />
            Kostenlos, dauerhaft
          </h2>
          <p className="text-sm text-muted mt-1.5">
            Ein Netzwerk hinter einer Bezahlschranke wächst nicht. Deshalb
            kostet nichts davon etwas:
          </p>
          <ul className="mt-4 space-y-2 text-sm text-muted">
            <li>· Dein Musiker-Profil</li>
            <li>· Offene Projekte einstellen und beantworten</li>
            <li>· Der Feed, Interesse und Kommentare</li>
            <li>· Anderen folgen</li>
          </ul>
          <p className="text-xs text-ink-600 mt-5">
            Ohne Premium bleibt dein Konto vollständig nutzbar – es fehlen nur
            die Video-Werkzeuge.
          </p>
        </div>
      </div>

      <div className="mt-6 bg-ink-850 border border-ink-700 rounded-2xl p-6">
        <h2 className="font-semibold flex items-center gap-2">
          <Mail size={18} className="text-brand-400" />
          So bekommst du es
        </h2>
        <p className="text-sm text-muted mt-1.5">
          Die Bezahlung über einen Zahlungsanbieter wird gerade eingerichtet.
          Bis dahin läuft es direkt: schreib eine kurze Mail mit der
          E-Mail-Adresse deines Kontos, dann bekommst du die Rechnung und
          danach die Freischaltung.
        </p>
        {betreiber?.email && (
          <a href={`mailto:${betreiber.email}?subject=HOOKCUT%20Premium&body=${
            encodeURIComponent(`Hallo,\n\nich möchte HOOKCUT Premium.\nMeine Konto-Adresse: ${user.email}\n\nViele Grüße`)
          }`}
            className="inline-flex items-center gap-2 mt-4 bg-brand-500 hover:bg-brand-600 text-ink-950 font-semibold px-4 py-2.5 rounded-xl transition-colors">
            <Mail size={16} />
            Mail an {betreiber.email}
          </a>
        )}
        <p className="text-xs text-ink-600 mt-4">
          Es gelten die <Link to="/agb" className="underline hover:text-white">AGB</Link>.
          Wie deine Daten verarbeitet werden, steht in der{" "}
          <Link to="/datenschutz" className="underline hover:text-white">Datenschutzerklärung</Link>.
        </p>
      </div>
    </main>
  );
}

function LaeuftHinweis({ bis, status }: { bis: string | null; status: string | null }) {
  const datum = bis ? new Date(bis).toLocaleDateString("de-DE") : null;
  // Gekuendigt heisst NICHT sofort weg - bezahlt ist bezahlt.
  const gekuendigt = status === "canceled";
  return (
    <div className={`mt-5 rounded-xl px-4 py-3 text-sm border ${
      gekuendigt
        ? "bg-amber-500/10 border-amber-500/40 text-amber-300"
        : "bg-brand-500/10 border-brand-500/40 text-brand-400"
    }`}>
      {gekuendigt
        ? `Dein Abo ist gekündigt und läuft ${datum ? `noch bis ${datum}` : "aus"}.`
        : datum
          ? `Dein Premium läuft bis ${datum}.`
          : "Dein Premium läuft – ohne Enddatum."}
    </div>
  );
}

function Leistung({ icon: Icon, titel, children }: {
  icon: typeof Check; titel: string; children: React.ReactNode;
}) {
  return (
    <li className="flex gap-3">
      <Icon size={18} className="text-brand-400 shrink-0 mt-0.5" />
      <div>
        <p className="text-sm font-medium">{titel}</p>
        <p className="text-sm text-muted">{children}</p>
      </div>
    </li>
  );
}
