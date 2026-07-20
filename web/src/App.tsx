import { useEffect, useState } from "react";
import { Loader2, Mic2 } from "lucide-react";
import Sidebar from "./components/Sidebar";
import Dashboard from "./components/Dashboard";
import HookAnalyzer from "./components/HookAnalyzer";
import CreateReelWizard from "./components/CreateReelWizard";
import AuthScreen from "./components/AuthScreen";
import { getMe, logout, setUnauthorizedHandler, type User } from "./api";

type AuthPhase = "loading" | "loggedOut" | "loggedIn";

function App() {
  const [authPhase, setAuthPhase] = useState<AuthPhase>("loading");
  const [user, setUser] = useState<User | null>(null);
  const [hookOpen, setHookOpen] = useState(false);
  const [wizardOpen, setWizardOpen] = useState(false);
  // Beim Schliessen eines Modals hochgezaehlt: der key-Wechsel laesst das
  // Dashboard neu mounten und damit seine Daten frisch vom Backend laden.
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    let cancelled = false;
    // Laeuft irgendwo eine Anfrage in einen 401 (Sitzung abgelaufen),
    // faellt die App automatisch auf die Login-Maske zurueck.
    setUnauthorizedHandler(() => {
      setUser(null);
      setAuthPhase("loggedOut");
      setHookOpen(false);
      setWizardOpen(false);
    });
    getMe()
      .then((u) => {
        if (cancelled) return;
        setUser(u);
        setAuthPhase(u ? "loggedIn" : "loggedOut");
      })
      .catch(() => {
        if (!cancelled) setAuthPhase("loggedOut");
      });
    return () => {
      cancelled = true;
      setUnauthorizedHandler(null);
    };
  }, []);

  function handleAuthed(u: User) {
    setUser(u);
    setAuthPhase("loggedIn");
    setRefreshKey((k) => k + 1);
  }

  async function handleLogout() {
    try {
      await logout();
    } catch {
      /* Sitzung ist so oder so weg - lokal ausloggen reicht. */
    }
    setUser(null);
    setAuthPhase("loggedOut");
  }

  function closeModals() {
    setHookOpen(false);
    setWizardOpen(false);
    setRefreshKey((k) => k + 1);
  }

  if (authPhase === "loading") {
    return (
      <div className="min-h-screen bg-ink-950 text-white flex flex-col items-center justify-center gap-4">
        <div className="flex items-center gap-2.5">
          <div className="w-11 h-11 rounded-xl bg-brand-500 flex items-center justify-center">
            <Mic2 size={24} className="text-ink-950" />
          </div>
          <span className="text-2xl font-bold tracking-tight">HOOKCUT</span>
        </div>
        <Loader2 size={24} className="text-brand-400 animate-spin" />
      </div>
    );
  }

  if (authPhase === "loggedOut" || !user) {
    return <AuthScreen onAuthed={handleAuthed} />;
  }

  return (
    <div className="flex min-h-screen bg-ink-950 text-white">
      <Sidebar user={user} onLogout={handleLogout} />
      <Dashboard
        key={refreshKey}
        user={user}
        onOpenHook={() => setHookOpen(true)}
        onOpenWizard={() => setWizardOpen(true)}
      />
      {hookOpen && <HookAnalyzer onClose={closeModals} />}
      {wizardOpen && <CreateReelWizard onClose={closeModals} />}
    </div>
  );
}

export default App;
