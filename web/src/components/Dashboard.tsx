import {
  Plus,
  Music2,
  Video,
  Headphones,
  Zap,
  UploadCloud,
  Sparkles,
  Play,
  Copy,
  ChevronRight,
  type LucideIcon,
} from "lucide-react";
import {
  stats,
  recentProjects,
  hookSuggestions,
  statusMeta,
} from "../data/mock";

const statIcons: Record<string, LucideIcon> = {
  music: Music2,
  video: Video,
  headphones: Headphones,
  zap: Zap,
};

function StatCard({ label, value, delta, icon }: (typeof stats)[number]) {
  const Icon = statIcons[icon];
  return (
    <div className="bg-ink-850 border border-ink-700 rounded-2xl p-5">
      <div className="flex items-start justify-between">
        <p className="text-sm text-muted">{label}</p>
        <div className="w-8 h-8 rounded-lg bg-ink-800 flex items-center justify-center">
          <Icon size={16} className="text-muted" />
        </div>
      </div>
      <p className="text-4xl font-bold mt-4 tracking-tight">{value}</p>
      <p className="text-xs text-brand-400 mt-3">{delta}</p>
    </div>
  );
}

export default function Dashboard({
  onOpenUpload,
  onOpenHook,
}: {
  onOpenUpload: () => void;
  onOpenHook: () => void;
}) {
  return (
    <main className="flex-1 min-w-0 px-8 py-7">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-4xl font-bold tracking-tight">Dashboard</h1>
          <p className="text-muted mt-1">Willkommen zurück, YngLyric</p>
        </div>
        <button
          onClick={onOpenUpload}
          className="flex items-center gap-2 bg-brand-500 hover:bg-brand-600 text-ink-950 font-semibold text-sm px-4 py-2.5 rounded-xl transition-colors"
        >
          <Plus size={18} />
          Neues Projekt
        </button>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4 mt-7">
        {stats.map((s) => (
          <StatCard key={s.label} {...s} />
        ))}
      </div>

      {/* Action cards */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mt-4">
        {/* Core: Upload */}
        <div className="bg-brand-500/8 border border-brand-500/60 rounded-2xl p-6 relative">
          <div className="flex items-start justify-between">
            <div className="w-12 h-12 rounded-xl bg-brand-500 flex items-center justify-center">
              <UploadCloud size={24} className="text-ink-950" />
            </div>
            <span className="text-[11px] font-semibold px-2 py-1 rounded bg-brand-500 text-ink-950">
              Core
            </span>
          </div>
          <h3 className="text-lg font-semibold text-brand-400 mt-5">
            Video + Song Upload
          </h3>
          <p className="text-sm text-muted mt-2 leading-relaxed">
            Lade dein Rap-Video und deinen produzierten Song hoch. Das System
            legt den Song automatisch perfekt synchron über dein Video.
          </p>
          <button
            onClick={onOpenUpload}
            className="mt-5 bg-brand-500 hover:bg-brand-600 text-ink-950 font-semibold text-sm px-4 py-2.5 rounded-xl transition-colors"
          >
            Jetzt hochladen
          </button>
        </div>

        {/* Viral Hook Detector */}
        <div className="bg-ink-850 border border-ink-700 rounded-2xl p-6">
          <div className="w-12 h-12 rounded-xl bg-ink-800 flex items-center justify-center">
            <Zap size={24} className="text-muted" />
          </div>
          <h3 className="text-lg font-semibold mt-5">Viral Hook Detector</h3>
          <p className="text-sm text-muted mt-2 leading-relaxed">
            Lade deinen Song hoch und das System findet automatisch die beste
            Hook-Stelle mit dem höchsten Viralitätsfaktor.
          </p>
          <button
            onClick={onOpenHook}
            className="mt-5 bg-ink-800 hover:bg-ink-700 text-white font-medium text-sm px-4 py-2.5 rounded-xl transition-colors"
          >
            Song analysieren
          </button>
        </div>

        {/* Coming soon */}
        <div className="bg-ink-850/50 border border-ink-700 rounded-2xl p-6 flex flex-col items-center justify-center text-center">
          <div className="w-12 h-12 rounded-xl bg-ink-800/60 flex items-center justify-center">
            <Sparkles size={24} className="text-ink-600" />
          </div>
          <h3 className="text-base font-medium text-muted mt-4">
            Feature coming soon
          </h3>
          <p className="text-xs text-ink-600 mt-1">Wir arbeiten an etwas Großem.</p>
          <span className="mt-4 text-xs px-3 py-1.5 rounded-lg bg-ink-800 text-ink-600">
            Demnächst
          </span>
        </div>
      </div>

      {/* Bottom: recent + hook detector */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4 mt-8">
        {/* Recent projects */}
        <div className="xl:col-span-2">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-xl font-semibold">Zuletzt bearbeitet</h2>
            <a
              href="#"
              className="flex items-center gap-1 text-sm text-brand-400 hover:text-brand-500"
            >
              Alle anzeigen <ChevronRight size={16} />
            </a>
          </div>
          <div className="space-y-2">
            {recentProjects.map((p) => {
              const meta = statusMeta[p.status];
              return (
                <div
                  key={p.id}
                  className="flex items-center gap-4 bg-ink-850 border border-ink-700 rounded-xl px-4 py-3.5 hover:bg-ink-800 transition-colors"
                >
                  <span className="text-sm text-ink-600 w-4 shrink-0">{p.id}</span>
                  <div className="w-9 h-9 rounded-lg bg-ink-800 flex items-center justify-center shrink-0">
                    <Music2 size={16} className="text-muted" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-medium truncate">{p.title}</p>
                    <p className="text-xs text-muted">{p.date}</p>
                  </div>
                  <span
                    className={`text-xs font-medium px-2.5 py-1 rounded-md ${meta.className}`}
                  >
                    {meta.label}
                  </span>
                  <span className="text-sm text-muted w-10 text-right shrink-0">
                    {p.duration}
                  </span>
                  <button className="w-8 h-8 rounded-lg hover:bg-ink-700 flex items-center justify-center text-muted hover:text-white transition-colors shrink-0">
                    <Play size={16} />
                  </button>
                </div>
              );
            })}
          </div>
        </div>

        {/* Hook detector panel */}
        <div className="bg-ink-850 border border-ink-700 rounded-2xl p-5 self-start">
          <div className="flex items-center justify-between">
            <span className="flex items-center gap-2 font-semibold">
              <Zap size={18} className="text-brand-400" />
              Viral Hook Detector
            </span>
            <a
              href="#"
              className="flex items-center gap-1 text-xs text-brand-400 hover:text-brand-500"
            >
              Details <ChevronRight size={14} />
            </a>
          </div>
          <p className="text-xs text-muted mt-3 leading-relaxed">
            KI analysiert deinen Song und findet automatisch die besten
            Hook-Stellen mit höchstem Viralitätsfaktor.
          </p>
          <div className="space-y-2 mt-4">
            {hookSuggestions.map((h) => (
              <div
                key={h.timestamp}
                className="flex items-center gap-3 bg-ink-800 rounded-xl px-3 py-2.5"
              >
                <span className="text-xs text-muted w-8 shrink-0">
                  {h.timestamp}
                </span>
                <span className="text-sm font-bold text-brand-400 w-7 shrink-0">
                  {h.score}
                </span>
                <p className="text-sm flex-1 min-w-0">{h.line}</p>
                <button className="text-muted hover:text-white shrink-0">
                  <Copy size={15} />
                </button>
              </div>
            ))}
          </div>
          <button
            onClick={onOpenHook}
            className="w-full mt-4 bg-brand-500/12 hover:bg-brand-500/20 text-brand-400 font-semibold text-sm py-3 rounded-xl transition-colors"
          >
            Hook extrahieren
          </button>
        </div>
      </div>
    </main>
  );
}
