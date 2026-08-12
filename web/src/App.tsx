import { useEffect, useState } from "react";
import { Routes, Route, Navigate, Outlet, Link } from "react-router-dom";
import { ArrowLeft, Loader2, Mic2 } from "lucide-react";
import AppShell from "./components/AppShell";
import Footer from "./components/Footer";
import AuthScreen from "./components/AuthScreen";
import DashboardPage from "./pages/DashboardPage";
import HookPage from "./pages/HookPage";
import CanvasPage from "./pages/CanvasPage";
import ReelsPage from "./pages/ReelsPage";
import PacksPage from "./pages/PacksPage";
import PackDetailPage from "./pages/PackDetailPage";
import ProjektePage from "./pages/ProjektePage";
import EinstellungenPage from "./pages/EinstellungenPage";
import ProfilPage from "./pages/ProfilPage";
import FeedPage from "./pages/FeedPage";
import PostDetailPage from "./pages/PostDetailPage";
import ProfilAnsichtPage from "./pages/ProfilAnsichtPage";
import ComingSoonPage from "./pages/ComingSoonPage";
import ImpressumPage from "./pages/ImpressumPage";
import DatenschutzPage from "./pages/DatenschutzPage";
import AgbPage from "./pages/AgbPage";
import { getAuthConfig, getMe, logout, setUnauthorizedHandler, type User } from "./api";

type AuthPhase = "loading" | "loggedOut" | "loggedIn";

function App() {
  const [authPhase, setAuthPhase] = useState<AuthPhase>("loading");
  const [user, setUser] = useState<User | null>(null);
  // Laufen hier die Video-Werkzeuge? Bis die Antwort da ist, wird von "ja"
  // ausgegangen - lokal ist das der Normalfall, und so blitzt beim Start
  // nichts kurz auf und verschwindet wieder.
  const [toolsEnabled, setToolsEnabled] = useState(true);

  useEffect(() => {
    let cancelled = false;
    // Laeuft irgendwo eine Anfrage in einen 401 (Sitzung abgelaufen),
    // faellt die App automatisch auf die Login-Maske zurueck.
    setUnauthorizedHandler(() => {
      setUser(null);
      setAuthPhase("loggedOut");
    });
    getAuthConfig()
      .then((c) => !cancelled && setToolsEnabled(c.tools_enabled))
      .catch(() => { /* Standard beibehalten */ });
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
    // Die Rechtsseiten muessen OHNE Konto erreichbar sein - ein Impressum
    // hinter einer Anmeldung waere keins. Deshalb hier eigene Routen; alles
    // andere landet auf der Anmeldemaske.
    return (
      <Routes>
        <Route element={<OeffentlichesGeruest />}>
          <Route path="/impressum" element={<ImpressumPage />} />
          <Route path="/datenschutz" element={<DatenschutzPage />} />
          <Route path="/agb" element={<AgbPage />} />
        </Route>
        <Route path="*" element={
          <AuthScreen
            onAuthed={(u) => {
              setUser(u);
              setAuthPhase("loggedIn");
            }}
          />
        } />
      </Routes>
    );
  }

  return (
    <Routes>
      <Route element={
        <AppShell user={user} setUser={setUser} onLogout={handleLogout}
          toolsEnabled={toolsEnabled} />
      }>
        {/* Startseite: lokal das Werkzeug-Dashboard, online der Feed. Ohne
            Werkzeuge waere das Dashboard eine leere Seite mit toten Knoepfen -
            und genau das ist der erste Eindruck nach dem Anmelden.
            Bewusst eine Weiterleitung statt derselben Seite unter zwei
            Adressen: so gibt es eine kanonische URL und der Menuepunkt
            "Offene Projekte" ist auch wirklich hervorgehoben. */}
        <Route index element={
          toolsEnabled ? <DashboardPage /> : <Navigate to="/projekte-feed" replace />
        } />
        <Route path="hook" element={<HookPage />} />
        <Route path="canvas" element={<CanvasPage />} />
        <Route path="reels" element={<ReelsPage />} />
        <Route path="wochen-content" element={<PacksPage />} />
        <Route path="wochen-content/:id" element={<PackDetailPage />} />
        <Route path="projekte" element={<ProjektePage />} />
        <Route path="projekte-feed" element={<FeedPage />} />
        <Route path="projekt/:postId" element={<PostDetailPage />} />
        <Route path="musiker/:handle" element={<ProfilAnsichtPage />} />
        <Route path="profil" element={<ProfilPage />} />
        <Route path="einstellungen" element={<EinstellungenPage />} />
        <Route path="impressum" element={<ImpressumPage />} />
        <Route path="datenschutz" element={<DatenschutzPage />} />
        <Route path="agb" element={<AgbPage />} />
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

/** Rahmen fuer die Rechtsseiten, solange niemand angemeldet ist: kein
 *  Seitenmenue (das braucht ein Konto), dafuer ein Weg zurueck und dieselbe
 *  Fusszeile wie ueberall. */
function OeffentlichesGeruest() {
  return (
    <div className="min-h-screen bg-ink-950 text-white flex flex-col">
      <header className="px-8 py-5 flex items-center gap-3">
        <Link to="/" className="flex items-center gap-2.5">
          <div className="w-9 h-9 rounded-xl bg-brand-500 flex items-center justify-center">
            <Mic2 size={20} className="text-ink-950" />
          </div>
          <span className="text-lg font-bold tracking-tight">HOOKCUT</span>
        </Link>
      </header>
      <Outlet />
      <Link to="/"
        className="mx-8 mt-8 inline-flex items-center gap-2 text-sm text-muted hover:text-white transition-colors">
        <ArrowLeft size={16} />
        Zurück zur Anmeldung
      </Link>
      <Footer />
    </div>
  );
}

export default App;
