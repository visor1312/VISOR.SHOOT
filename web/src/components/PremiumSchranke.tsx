import { Link, Outlet } from "react-router-dom";
import { Lock } from "lucide-react";
import { useApp } from "./app-context";

/** Steht als Layout-Route vor den Werkzeug-Seiten.
 *
 *  Bewusst KEINE Weiterleitung auf /premium: die Adresse bleibt stehen, und
 *  der Nutzer sieht, worauf er geklickt hat und warum es nicht aufgeht.
 *  Eine Weiterleitung wuerde beides verschlucken.
 *
 *  Die Schranke hier ist reine Hoeflichkeit - verlassen kann man sich nur
 *  auf den Server (auth.require_premium, 402). Wer die Oberflaeche umgeht,
 *  kommt trotzdem nicht durch. */
export default function PremiumSchranke() {
  const ctx = useApp();

  if (!ctx.premiumRequired || ctx.user.premium) {
    // Kontext weiterreichen - sonst bekaemen die Seiten darunter nichts.
    return <Outlet context={ctx} />;
  }

  return (
    <main className="flex-1 px-8 py-8">
      <div className="max-w-lg bg-ink-850 border border-ink-700 rounded-2xl p-8">
        <div className="w-11 h-11 rounded-xl bg-brand-500/12 flex items-center justify-center">
          <Lock size={20} className="text-brand-400" />
        </div>
        <h1 className="text-xl font-semibold mt-4">Das gehört zu Premium</h1>
        <p className="text-sm text-muted mt-2">
          Die Video-Werkzeuge rechnen für dich – auf echter Hardware, und das
          kostet. Dein Profil, der Feed und die offenen Projekte bleiben
          kostenlos.
        </p>
        <Link to="/premium"
          className="inline-block mt-5 bg-brand-500 hover:bg-brand-600 text-ink-950 font-semibold px-4 py-2.5 rounded-xl transition-colors">
          Was Premium kostet
        </Link>
      </div>
    </main>
  );
}
