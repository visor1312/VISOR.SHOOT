import {
  LayoutDashboard,
  Upload,
  Zap,
  Music2,
  FolderOpen,
  TrendingUp,
  Disc3,
  Layers,
  BarChart3,
  Users,
  DollarSign,
  Mic2,
  LogOut,
  type LucideIcon,
} from "lucide-react";
import type { User } from "../api";

interface NavItem {
  label: string;
  icon: LucideIcon;
  active?: boolean;
  soon?: boolean;
}

const mainNav: NavItem[] = [
  { label: "Dashboard", icon: LayoutDashboard, active: true },
  { label: "Upload", icon: Upload },
  { label: "Hook Generator", icon: Zap },
  { label: "Meine fertigen Reels", icon: Music2 },
  { label: "Offene Projekte", icon: FolderOpen },
];

const analyticsNav: NavItem[] = [
  { label: "Spotify Streaming Dashboard", icon: TrendingUp },
];

const dbNav: NavItem[] = [
  { label: "Type Beats Datenbank", icon: Disc3 },
  { label: "Angefangene Tracks Datenbank", icon: Layers },
];

const soonNav: NavItem[] = [
  { label: "Analytics", icon: BarChart3, soon: true },
  { label: "Collab Hub", icon: Users, soon: true },
  { label: "Monetize", icon: DollarSign, soon: true },
];

function NavRow({ item }: { item: NavItem }) {
  const Icon = item.icon;
  if (item.soon) {
    return (
      <div className="flex items-center justify-between px-3 py-2 rounded-lg text-ink-600 cursor-default">
        <span className="flex items-center gap-3 text-sm">
          <Icon size={18} />
          {item.label}
        </span>
        <span className="text-[10px] uppercase tracking-wide px-1.5 py-0.5 rounded bg-ink-800 text-ink-600">
          Soon
        </span>
      </div>
    );
  }
  return (
    <a
      href="#"
      className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
        item.active
          ? "bg-brand-500/12 text-brand-400 font-medium"
          : "text-muted hover:text-white hover:bg-ink-800"
      }`}
    >
      <Icon size={18} />
      {item.label}
    </a>
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

export default function Sidebar({ user, onLogout }: { user: User; onLogout: () => void }) {
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
            <NavRow key={i.label} item={i} />
          ))}
        </div>

        <SectionLabel>Analytics</SectionLabel>
        <div className="space-y-1">
          {analyticsNav.map((i) => (
            <NavRow key={i.label} item={i} />
          ))}
        </div>

        <SectionLabel>Datenbanken</SectionLabel>
        <div className="space-y-1">
          {dbNav.map((i) => (
            <NavRow key={i.label} item={i} />
          ))}
        </div>

        <SectionLabel>Demnächst</SectionLabel>
        <div className="space-y-1">
          {soonNav.map((i) => (
            <NavRow key={i.label} item={i} />
          ))}
        </div>
      </nav>

      {/* User */}
      <div className="flex items-center gap-3 px-4 py-4 border-t border-ink-700">
        <div className="w-9 h-9 rounded-full bg-gradient-to-br from-amber-500 to-orange-700 shrink-0 flex items-center justify-center text-xs font-bold text-white">
          {initials(user.display_name)}
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium truncate">{user.display_name}</p>
          <p className="text-xs text-muted">{user.is_admin ? "Admin" : "Free Plan"}</p>
        </div>
        <button onClick={onLogout} title="Abmelden"
          className="text-muted hover:text-white cursor-pointer p-1 -mr-1">
          <LogOut size={18} />
        </button>
      </div>
    </aside>
  );
}
