import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  Upload,
  Zap,
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
  Settings,
  LogOut,
  type LucideIcon,
} from "lucide-react";
import type { User } from "../api";

interface NavItem {
  label: string;
  icon: LucideIcon;
  to: string;
  soon?: boolean;
}

const mainNav: NavItem[] = [
  { label: "Dashboard", icon: LayoutDashboard, to: "/" },
  { label: "Hook Generator", icon: Zap, to: "/hook" },
  { label: "Wochen-Content", icon: CalendarClock, to: "/wochen-content" },
  { label: "Meine fertigen Reels", icon: Music2, to: "/reels" },
  { label: "Offene Projekte", icon: FolderOpen, to: "/projekte" },
];

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
}: {
  user: User;
  onLogout: () => void;
  onOpenWizard: () => void;
}) {
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
          {mainNav.map((i) => (
            <NavRow key={i.to} item={i} />
          ))}
          {/* "Reel erstellen" oeffnet den Assistenten als Overlay (keine Route). */}
          <button
            onClick={onOpenWizard}
            className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-muted hover:text-white hover:bg-ink-800 transition-colors"
          >
            <Upload size={18} />
            Reel erstellen
          </button>
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
            <p className="text-xs text-muted">{user.is_admin ? "Admin" : "Free Plan"}</p>
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
