import { useEffect, useState } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import { Loader2, Mic2 } from "lucide-react";
import AppShell from "./components/AppShell";
import AuthScreen from "./components/AuthScreen";
import DashboardPage from "./pages/DashboardPage";
import HookPage from "./pages/HookPage";
import CanvasPage from "./pages/CanvasPage";
import ReelsPage from "./pages/ReelsPage";
import PacksPage from "./pages/PacksPage";
import PackDetailPage from "./pages/PackDetailPage";
import ProjektePage from "./pages/ProjektePage";
import EinstellungenPage from "./pages/EinstellungenPage";
import ComingSoonPage from "./pages/ComingSoonPage";
import { getMe, logout, setUnauthorizedHandler, type User } from "./api";

type AuthPhase = "loading" | "loggedOut" | "loggedIn";

function App() {
  const [authPhase, setAuthPhase] = useState<AuthPhase>("loading");
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    let cancelled = false;
    // Laeuft irgendwo eine Anfrage in einen 401 (Sitzung abgelaufen),
    // faellt die App automatisch auf die Login-Maske zurueck.
    setUnauthorizedHandler(() => {
      setUser(null);
      setAuthPhase("loggedOut");
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

  async function handleLogout() {
    try {
      await logout();
    } catch {
      /* Sitzung ist so oder so weg - lokal ausloggen reicht. */
    }
    setUser(null);
    setAuthPhase("loggedOut");
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
    return (
      <AuthScreen
        onAuthed={(u) => {
          setUser(u);
          setAuthPhase("loggedIn");
        }}
      />
    );
  }

  return (
    <Routes>
      <Route element={<AppShell user={user} setUser={setUser} onLogout={handleLogout} />}>
        <Route index element={<DashboardPage />} />
        <Route path="hook" element={<HookPage />} />
        <Route path="canvas" element={<CanvasPage />} />
        <Route path="reels" element={<ReelsPage />} />
        <Route path="wochen-content" element={<PacksPage />} />
        <Route path="wochen-content/:id" element={<PackDetailPage />} />
        <Route path="projekte" element={<ProjektePage />} />
        <Route path="einstellungen" element={<EinstellungenPage />} />
        <Route path="spotify" element={<ComingSoonPage title="Spotify Streaming Dashboard" />} />
        <Route path="type-beats" element={<ComingSoonPage title="Type Beats Datenbank" />} />
        <Route path="tracks" element={<ComingSoonPage title="Angefangene Tracks Datenbank" />} />
        <Route path="analytics" element={<ComingSoonPage title="Analytics" />} />
        <Route path="collab" element={<ComingSoonPage title="Collab Hub" />} />
        <Route path="monetize" element={<ComingSoonPage title="Monetize" />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}

export default App;
