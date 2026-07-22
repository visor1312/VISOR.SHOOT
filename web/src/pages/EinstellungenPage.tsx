import { Mail, User as UserIcon } from "lucide-react";
import { useApp } from "../components/app-context";

/** Platzhalter-Version (Commit 1): zeigt das eigene Konto an. Das Bearbeiten
 * (Name/Passwort) und der Admin-Bereich (Einladungen/Nutzer) folgen in
 * Commit 3, sobald die Backend-Endpunkte stehen. */
export default function EinstellungenPage() {
  const { user } = useApp();
  return (
    <main className="flex-1 min-w-0 px-8 py-7">
      <h1 className="text-3xl font-bold tracking-tight">Einstellungen</h1>
      <p className="text-muted mt-1">Dein Konto.</p>

      <div className="mt-6 max-w-xl bg-ink-850 border border-ink-700 rounded-2xl p-6 space-y-4">
        <div className="flex items-center gap-3">
          <UserIcon size={18} className="text-muted" />
          <div>
            <p className="text-xs text-muted">Anzeigename</p>
            <p className="text-sm font-medium">{user.display_name}</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <Mail size={18} className="text-muted" />
          <div>
            <p className="text-xs text-muted">E-Mail</p>
            <p className="text-sm font-medium">{user.email}</p>
          </div>
        </div>
        <p className="text-sm text-muted pt-2 border-t border-ink-700">
          {user.is_admin ? "Rolle: Admin" : "Rolle: Nutzer"}
        </p>
      </div>
    </main>
  );
}
