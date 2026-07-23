import { useEffect, useState } from "react";
import {
  Plus,
  Music2,
  Video,
  Headphones,
  Zap,
  UploadCloud,
  Sparkles,
  Download,
  Copy,
  type LucideIcon,
} from "lucide-react";
import {
  listProjects,
  listRecentHooks,
  listEditJobs,
  downloadUrl,
  editDownloadUrl,
  type ProjectSummary,
  type HookJobSummary,
  type EditJobSummary,
  type Take,
  type User,
} from "../api";
import {
  formatDate,
  formatTime,
  editJobStatusMeta,
  projectStatusMeta,
  type ProjectStatus,
} from "../lib/format";

/** Projektstatus aus den Takes ableiten: läuft etwas? Ist etwas fertig? */
function projectStatus(takes: Take[]): ProjectStatus {
  if (takes.some((t) => t.status === "processing" || t.status === "pending")) return "processing";
  if (takes.some((t) => t.status === "done")) return "done";
  if (takes.length > 0 && takes.every((t) => t.status === "error")) return "error";
  return "draft";
}

function latestDoneTake(takes: Take[]): Take | undefined {
  return [...takes].reverse().find((t) => t.status === "done" && t.output_path);
}

/** Wie viele Einträge sind jünger als 7 Tage? Für die Delta-Zeile der Stat-Karten. */
function countThisWeek(items: { created_at: string }[]): number {
  const weekAgo = Date.now() - 7 * 24 * 60 * 60 * 1000;
  return items.filter((i) => new Date(i.created_at).getTime() > weekAgo).length;
}

interface Stat {
  label: string;
  value: string;
  delta: string;
  icon: string;
}

const statIcons: Record<string, LucideIcon> = {
  music: Music2,
  video: Video,
  headphones: Headphones,
  zap: Zap,
};

function StatCard({ label, value, delta, icon }: Stat) {
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
  user,
  onOpenHook,
  onOpenWizard,
}: {
  user: User;
  onOpenHook: () => void;
  onOpenWizard: () => void;
}) {
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [hooks, setHooks] = useState<HookJobSummary[]>([]);
  const [reels, setReels] = useState<EditJobSummary[]>([]);
  const [loadError, setLoadError] = useState("");

  useEffect(() => {
    let cancelled = false;
    Promise.all([listProjects(), listRecentHooks(), listEditJobs()])
      .then(([p, h, r]) => {
        if (cancelled) return;
        setProjects(p);
        setHooks(h);
        setReels(r);
      })
      .catch((e) => {
        if (!cancelled) setLoadError(e instanceof Error ? e.message : String(e));
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const allTakes = projects.flatMap((p) => p.takes);
  const doneTakes = allTakes.filter((t) => t.status === "done");
  const doneReels = reels.filter((r) => r.status === "done");
  const doneHooks = hooks.filter((h) => h.status === "done" && h.best);
  const bestScore = doneHooks.reduce(
    (max, h) => Math.max(max, h.best?.viral_score ?? 0),
    0,
  );

  const stats: Stat[] = [
    {
      label: "Projekte",
      value: String(projects.length),
      delta: `+${countThisWeek(projects)} diese Woche`,
      icon: "music",
    },
    {
      label: "Fertige Reels",
      value: String(doneTakes.length + doneReels.length),
      delta: `+${countThisWeek(doneTakes) + countThisWeek(doneReels)} diese Woche`,
      icon: "video",
    },
    {
      label: "Hook-Analysen",
      value: String(hooks.length),
      delta: `+${countThisWeek(hooks)} diese Woche`,
      icon: "headphones",
    },
    {
      label: "Bester Viral-Score",
      value: bestScore > 0 ? String(Math.round(bestScore)) : "–",
      delta: bestScore > 0 ? "von 100 Punkten" : "noch keine Analyse",
      icon: "zap",
    },
  ];

  return (
    <main className="flex-1 min-w-0 px-8 py-7">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-4xl font-bold tracking-tight">Dashboard</h1>
          <p className="text-muted mt-1">Willkommen zurück, {user.display_name}</p>
        </div>
        <button
          onClick={onOpenWizard}
          className="flex items-center gap-2 bg-brand-500 hover:bg-brand-600 text-ink-950 font-semibold text-sm px-4 py-2.5 rounded-xl transition-colors"
        >
          <Plus size={18} />
          Reel erstellen
        </button>
      </div>

      {loadError && (
        <div className="mt-5 bg-red-500/10 border border-red-500/40 text-red-400 text-sm rounded-xl px-4 py-3">
          {loadError}
        </div>
      )}

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
            Reel erstellen (All-in-One)
          </h3>
          <p className="text-sm text-muted mt-2 leading-relaxed">
            Video + Song hochladen → synchronisieren → optional viralsten Teil
            finden → Style wählen. Fertiges 9:16-Reel per Knopfdruck.
          </p>
          <button
            onClick={onOpenWizard}
            className="mt-5 bg-brand-500 hover:bg-brand-600 text-ink-950 font-semibold text-sm px-4 py-2.5 rounded-xl transition-colors"
          >
            Los geht's
          </button>
        </div>

        {/* Viral Hook Detector */}
        <div className="bg-brand-500/8 border border-brand-500/60 rounded-2xl p-6 relative">
          <div className="flex items-start justify-between">
            <div className="w-12 h-12 rounded-xl bg-brand-500 flex items-center justify-center">
              <Zap size={24} className="text-ink-950" />
            </div>
            <span className="text-[11px] font-semibold px-2 py-1 rounded bg-brand-500 text-ink-950">
              Core
            </span>
          </div>
          <h3 className="text-lg font-semibold text-brand-400 mt-5">
            Viral Hook Detector
          </h3>
          <p className="text-sm text-muted mt-2 leading-relaxed">
            Lade deinen Song hoch und das System findet automatisch die beste
            Hook-Stelle mit dem höchsten Viralitätsfaktor.
          </p>
          <button
            onClick={onOpenHook}
            className="mt-5 bg-brand-500 hover:bg-brand-600 text-ink-950 font-semibold text-sm px-4 py-2.5 rounded-xl transition-colors"
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

      {/* Meine Reels (Wizard-Reels des angemeldeten Nutzers) */}
      <div className="mt-8">
        <h2 className="text-xl font-semibold mb-3">Meine Reels</h2>
        <div className="space-y-2">
          {reels.length === 0 && !loadError && (
            <div className="bg-ink-850 border border-ink-700 rounded-xl px-4 py-8 text-center text-sm text-muted">
              Noch keine Reels — erstelle dein erstes mit „Reel erstellen".
            </div>
          )}
          {reels.map((r) => {
            const meta = editJobStatusMeta(r.status);
            const readyOutputs = (r.outputs ?? []).filter((o) => o.ready);
            return (
              <div key={r.job_id}
                className="flex items-center gap-4 bg-ink-850 border border-ink-700 rounded-xl px-4 py-3.5">
                <div className="w-9 h-9 rounded-lg bg-ink-800 flex items-center justify-center shrink-0">
                  <Video size={16} className="text-muted" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="font-medium truncate">
                    {r.style ? `Style: ${r.style}` : "Reel"}
                  </p>
                  <p className="text-xs text-muted">{formatDate(r.created_at)}</p>
                </div>
                <span className={`text-xs font-medium px-2.5 py-1 rounded-md ${meta.className}`}>
                  {meta.label}
                </span>
                <div className="flex items-center gap-1.5 shrink-0">
                  {r.status === "done" && readyOutputs.length > 0 ? (
                    readyOutputs.map((o) => (
                      <a key={o.platform} href={editDownloadUrl(r.job_id, o.platform)} download
                        title={`${o.name} herunterladen (${o.width}×${o.height})`}
                        className="text-xs px-2 py-1 rounded-lg bg-ink-800 hover:bg-ink-700 text-muted hover:text-white transition-colors flex items-center gap-1">
                        <Download size={13} /> {o.platform}
                      </a>
                    ))
                  ) : (
                    <span className="w-8" />
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Bottom: recent + hook detector */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4 mt-8">
        {/* Recent projects */}
        <div className="xl:col-span-2">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-xl font-semibold">Zuletzt bearbeitet</h2>
          </div>
          <div className="space-y-2">
            {projects.length === 0 && !loadError && (
              <div className="bg-ink-850 border border-ink-700 rounded-xl px-4 py-8 text-center text-sm text-muted">
                Noch keine Projekte — starte mit „Neues Projekt".
              </div>
            )}
            {projects.map((p, i) => {
              const status = projectStatus(p.takes);
              const meta = projectStatusMeta[status];
              const done = latestDoneTake(p.takes);
              return (
                <div
                  key={p.id}
                  className="flex items-center gap-4 bg-ink-850 border border-ink-700 rounded-xl px-4 py-3.5 hover:bg-ink-800 transition-colors"
                >
                  <span className="text-sm text-ink-600 w-4 shrink-0">{i + 1}</span>
                  <div className="w-9 h-9 rounded-lg bg-ink-800 flex items-center justify-center shrink-0">
                    <Music2 size={16} className="text-muted" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-medium truncate">{p.name}</p>
                    <p className="text-xs text-muted">{formatDate(p.created_at)}</p>
                  </div>
                  <span
                    className={`text-xs font-medium px-2.5 py-1 rounded-md ${meta.className}`}
                  >
                    {meta.label}
                  </span>
                  <span className="text-sm text-muted w-16 text-right shrink-0">
                    {p.takes.length} Take{p.takes.length !== 1 ? "s" : ""}
                  </span>
                  {done ? (
                    <a
                      href={downloadUrl(p.id, done.id)}
                      title="Fertiges Video herunterladen"
                      className="w-8 h-8 rounded-lg hover:bg-ink-700 flex items-center justify-center text-muted hover:text-white transition-colors shrink-0"
                    >
                      <Download size={16} />
                    </a>
                  ) : (
                    <span className="w-8 shrink-0" />
                  )}
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
          </div>
          <p className="text-xs text-muted mt-3 leading-relaxed">
            Deine letzten Analysen. Die KI findet automatisch die Song-Stelle
            mit dem höchsten Hook-Potenzial.
          </p>
          <div className="space-y-2 mt-4">
            {doneHooks.length === 0 && (
              <div className="bg-ink-800 rounded-xl px-3 py-4 text-center text-xs text-muted">
                Noch keine Hook-Analysen.
              </div>
            )}
            {doneHooks.map((h) => {
              const range = `${formatTime(h.best!.start_sec)}–${formatTime(h.best!.end_sec)}`;
              return (
                <div
                  key={h.job_id}
                  className="flex items-center gap-3 bg-ink-800 rounded-xl px-3 py-2.5"
                >
                  <span className="text-xs text-muted w-8 shrink-0">
                    {formatTime(h.best!.start_sec)}
                  </span>
                  <span className="text-sm font-bold text-brand-400 w-7 shrink-0">
                    {Math.round(h.best!.viral_score)}
                  </span>
                  <p className="text-sm flex-1 min-w-0">
                    Hook bei {range}
                    <span className="block text-xs text-muted">
                      {formatDate(h.created_at)}
                    </span>
                  </p>
                  <button
                    title="Zeitbereich kopieren"
                    onClick={() => navigator.clipboard.writeText(range)}
                    className="text-muted hover:text-white shrink-0"
                  >
                    <Copy size={15} />
                  </button>
                </div>
              );
            })}
          </div>
          <button
            onClick={onOpenHook}
            className="w-full mt-4 bg-brand-500/12 hover:bg-brand-500/20 text-brand-400 font-semibold text-sm py-3 rounded-xl transition-colors"
          >
            Neuen Song analysieren
          </button>
        </div>
      </div>
    </main>
  );
}
