import { useState } from "react";
import { Outlet } from "react-router-dom";
import Sidebar from "./Sidebar";
import CreateReelWizard from "./CreateReelWizard";
import type { AppContext } from "./app-context";
import type { User } from "../api";

/** Persistentes Layout: Sidebar bleibt stehen, rechts wechselt der Inhalt
 * (<Outlet/>). Das "Reel erstellen"-Modal lebt hier, damit es von jeder
 * Seite und aus der Sidebar geoeffnet werden kann. */
export default function AppShell({
  user,
  setUser,
  onLogout,
}: {
  user: User;
  setUser: (user: User) => void;
  onLogout: () => void;
}) {
  const [wizardOpen, setWizardOpen] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);

  function closeWizard() {
    setWizardOpen(false);
    setRefreshKey((k) => k + 1);
  }

  const ctx: AppContext = {
    user,
    setUser,
    openWizard: () => setWizardOpen(true),
    refreshKey,
  };

  return (
    <div className="flex min-h-screen bg-ink-950 text-white">
      <Sidebar user={user} onLogout={onLogout} onOpenWizard={() => setWizardOpen(true)} />
      <Outlet context={ctx} />
      {wizardOpen && <CreateReelWizard onClose={closeWizard} />}
    </div>
  );
}
