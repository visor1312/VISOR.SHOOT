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
  /** Laufen auf diesem Server die Video-Werkzeuge? Online nicht (kein
   *  Chrome/WebGPU) - dann verschwinden sie aus der Navigation und der Feed
   *  ist die Startseite. Kommt aus GET /auth/config. */
  toolsEnabled: boolean;
  /** Kosten die Werkzeuge auf diesem Server ein Abo? Lokal nein, online ja.
   *  Kommt aus GET /auth/config. Ob der angemeldete Nutzer eins HAT, steht
   *  in user.premium. */
  premiumRequired: boolean;
}

export function useApp(): AppContext {
  return useOutletContext<AppContext>();
}
