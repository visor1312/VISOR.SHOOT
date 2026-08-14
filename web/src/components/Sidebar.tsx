import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  Upload,
  Zap,
  Film,
  Music2,
  CalendarClock,
  FolderOpen,
  TrendingUp,
  Disc3,
  Layers,
  BarChart3,
  Users,
  DollarSign,
  Mic2,
  Users2,
  UserCircle,
  Settings,
  LogOut,
  Sparkles,
  type LucideIcon,
} from "lucide-react";
import type { User } from "../api";

interface NavItem {
  label: string;
  icon: LucideIcon;
  to: string;
  soon?: boolean;
  /** Braucht die Video-Werkzeuge (Chrome/WebGPU, ffmpeg, Modelle) und ist
   *  deshalb online nicht verfuegbar. */
  werkzeug?: boolean;
}

const mainNav: NavItem[] = [
  // Der Feed steht oben und ist die Startseite. Das Werkzeug-Dashboard hat
  // eine eigene Adresse (/dashboard) - wer HOOKCUT aufmacht, soll zuerst
  // sehen, was in der Szene los ist, und nicht seine eigene Werkbank.
  { label: "Offene Projekte", icon: Users2, to: "/projekte-feed" },
  { label: "Dashboard", icon: LayoutDashboard, to: "/dashboard", werkzeug: true },
  { label: "Mein Profil", icon: UserCircle, to: "/profil" },
  { label: "Hook Generator", icon: Zap, to: "/hook", werkzeug: true },
  { label: "Spotify Canvas", icon: Film, to: "/canvas", werkzeug: true },
  { label: "Wochen-Content", icon: CalendarClock, to: "/wochen-content", werkzeug: true },
  { label: "Meine fertigen Reels", icon: Music2, to: "/reels", werkzeug: true },
  // Frueher "Offene Projekte" - umbenannt, seit es den gleichnamigen
  // Netzwerk-Feed gibt. Hier liegen die EIGENEN Aufnahme-Projekte.
  { label: "Meine Aufnahmen", icon: FolderOpen, to: "/projekte", werkzeug: true },
];

// Steht nur in der Navigation, solange kein Abo laeuft - wer bezahlt hat,
// braucht keine Werbung mehr. Erreichbar bleibt /premium trotzdem (ueber die
// Einstellungen), damit man Laufzeit und Leistungen nachsehen kann.
const premiumNav: NavItem = { label: "HOOKCUT Premium", icon: Sparkles, to: "/premium" };

const analyticsNav: NavItem[] = [
  { label: "Spotify Streaming Dashboard", icon: TrendingUp, to: "/spotify", soon: true },
];

const dbNav: NavItem[] = [
  { label: "Type Beats Datenbank", icon: Disc3, to: "/type-beats", soon: true },
  { label: "Angefangene Tracks Datenbank", icon: Layers, to: "/tracks", soon: true },
];

const soonNav: NavItem[] = [
  { label: "Analytics", icon: BarChart3, to: "/analytics", soon: true },
  { label: "Collab Hub", icon: Users, to: "/collab", soon: true },
  { label: "Monetize", icon: DollarSign, to: "/monetize", soon: true },
];

function NavRow({ item }: { item: NavItem }) {
  const Icon = item.icon;
  return (
    <NavLink
      to={item.to}
      end={item.to === "/"}
      className={({ isActive }) =>
        `flex items-center justify-between px-3 py-2 rounded-lg text-sm transition-colors ${
          isActive
            ? "bg-brand-500/12 text-brand-400 font-medium"
            : "text-muted hover:text-white hover:bg-ink-800"
        }`
      }
    >
      <span className="flex items-center gap-3">
        <Icon size={18} />
        {item.label}
      </span>
      {item.soon && (
        <span className="text-[10px] uppercase tracking-wide px-1.5 py-0.5 rounded bg-ink-800 text-ink-600">
          Soon
        </span>
      )}
    </NavLink>
  );
}

function SectionLabel({ children }: { children: string }) {
  return (
    <p className="px-3 pt-6 pb-2 text-[11px] font-semibold uppercase tracking-wider text-ink-600">
      {children}
    </p>
  );
}

/** Die Zeile unter dem Namen. "Admin" schlaegt alles - wer das Ding
 *  betreibt, will das sehen und nicht seinen Tarif. */
function planLabel(user: User): string {
  if (user.is_admin) return "Admin";
  if (!user.premium) return "Kostenlos";
  return user.premium_status === "canceled" ? "Premium (gekündigt)" : "Premium";
}

/** Initialen aus dem Anzeigenamen (max. 2 Woerter), fuer den Avatar. */
function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean).slice(0, 2);
  const letters = parts.map((p) => p[0]).join("");
  return (letters || "?").toUpperCase();
}

export default function Sidebar({
  user,
  onLogout,
  onOpenWizard,
  toolsEnabled,
  premiumRequired,
  darfRendern,
}: {
  user: User;
  onLogout: () => void;
  onOpenWizard: () => void;
  toolsEnabled: boolean;
  premiumRequired: boolean;
  /** Werkzeuge vorhanden UND (falls noetig) bezahlt. */
  darfRendern: boolean;
}) {
  // Online (kein Chrome/WebGPU) fliegen die Werkzeug-Eintraege raus. Ein
  // sichtbarer Knopf, der nur einen Fehler erzeugt, waere schlimmer als gar
  // kein Knopf - besonders als erster Eindruck.
  const hauptNav = toolsEnabled ? mainNav : mainNav.filter((i) => !i.werkzeug);
  // Ohne Abo bleiben die Werkzeug-Eintraege SICHTBAR (anders als ohne
  // Werkzeuge): dahinter steht dann die Bezahlschranke, die erklaert, was es
  // ist und was es kostet. Wer nicht sehen kann, was er kaufen koennte,
  // kauft es auch nicht.
  const zeigePremium = premiumRequired && !user.premium;
  return (
    <aside className="w-64 shrink-0 h-screen sticky top-0 bg-ink-900 border-r border-ink-700 flex flex-col">
      {/* Logo */}
      <div className="flex items-center gap-2.5 px-5 h-16 shrink-0">
        <div className="w-9 h-9 rounded-xl bg-brand-500 flex items-center justify-center">
          <Mic2 size={20} className="text-ink-950" />
        </div>
        <span className="text-lg font-bold tracking-tight">HOOKCUT</span>
      </div>

      <nav className="flex-1 overflow-y-auto px-3 pb-4">
        <div className="space-y-1 pt-2">
          {hauptNav.map((i) => (
            <NavRow key={i.to} item={i} />
          ))}
          {/* "Reel erstellen" oeffnet den Assistenten als Overlay (keine Route). */}
          {darfRendern && (
          <button
            onClick={onOpenWizard}
            className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-muted hover:text-white hover:bg-ink-800 transition-colors"
          >
            <Upload size={18} />
            Reel erstellen
          </button>
          )}
          {zeigePremium && <NavRow item={premiumNav} />}
        </div>

        <SectionLabel>Analytics</SectionLabel>
        <div className="space-y-1">
          {analyticsNav.map((i) => (
            <NavRow key={i.to} item={i} />
          ))}
        </div>

        <SectionLabel>Datenbanken</SectionLabel>
        <div className="space-y-1">
          {dbNav.map((i) => (
            <NavRow key={i.to} item={i} />
          ))}
        </div>

        <SectionLabel>Demnächst</SectionLabel>
        <div className="space-y-1">
          {soonNav.map((i) => (
            <NavRow key={i.to} item={i} />
          ))}
        </div>
      </nav>

      {/* User */}
      <div className="flex items-center gap-3 px-4 py-4 border-t border-ink-700">
        <NavLink
          to="/einstellungen"
          title="Einstellungen"
          className="flex items-center gap-3 flex-1 min-w-0 group"
        >
          <div className="w-9 h-9 rounded-full bg-gradient-to-br from-amber-500 to-orange-700 shrink-0 flex items-center justify-center text-xs font-bold text-white">
            {initials(user.display_name)}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium truncate group-hover:text-brand-400 transition-colors">
              {user.display_name}
            </p>
            {/* Frueher stand hier hartkodiert "Free Plan". Jetzt ist es
                echte Auskunft: was der Server ueber dieses Konto sagt. */}
            <p className="text-xs text-muted">{planLabel(user)}</p>
          </div>
        </NavLink>
        <NavLink to="/einstellungen" title="Einstellungen"
          className="text-muted hover:text-white p-1">
          <Settings size={17} />
        </NavLink>
        <button onClick={onLogout} title="Abmelden"
          className="text-muted hover:text-white cursor-pointer p-1 -mr-1">
          <LogOut size={18} />
        </button>
      </div>
    </aside>
  );
}
