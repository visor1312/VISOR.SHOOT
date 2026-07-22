import { useOutletContext } from "react-router-dom";
import type { User } from "../api";

/** Kontext, den alle Seiten unter dem AppShell (via <Outlet/>) bekommen. */
export interface AppContext {
  user: User;
  /** Aktualisiert den App-weiten User (z.B. nach Namensaenderung). */
  setUser: (user: User) => void;
  /** Oeffnet den "Reel erstellen"-Assistenten (Overlay, von ueberall). */
  openWizard: () => void;
  /** Zaehlt nach jedem Modal-Schliessen hoch -> Seiten koennen neu laden. */
  refreshKey: number;
}

export function useApp(): AppContext {
  return useOutletContext<AppContext>();
}
