import { useEffect, useState } from "react";
import { FolderOpen, Music2, Download, Loader2 } from "lucide-react";
import { listProjects, downloadUrl, type ProjectSummary, type Take } from "../api";
import { formatDate, projectStatusMeta, type ProjectStatus } from "../lib/format";

function projectStatus(takes: Take[]): ProjectStatus {
  if (takes.some((t) => t.status === "processing" || t.status === "pending")) return "processing";
  if (takes.some((t) => t.status === "done")) return "done";
  if (takes.length > 0 && takes.every((t) => t.status === "error")) return "error";
  return "draft";
}

function latestDoneTake(takes: Take[]): Take | undefined {
  return [...takes].reverse().find((t) => t.status === "done" && t.output_path);
}

/** Alle Projekte des Nutzers (Take-basierter Workflow), mit Download. */
export default function ProjektePage() {
  const [projects, setProjects] = useState<ProjectSummary[] | null>(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    let cancelled = false;
    listProjects()
      .then((p) => !cancelled && setProjects(p))
      .catch((e) => !cancelled && setErr(e instanceof Error ? e.message : String(e)));
    return () => { cancelled = true; };
  }, []);

  return (
    <main className="flex-1 min-w-0 px-8 py-7">
      <h1 className="text-3xl font-bold tracking-tight">Meine Aufnahmen</h1>
      <p className="text-muted mt-1">Deine Projekte und ihre synchronisierten Takes.</p>

      {err && (
        <div className="mt-5 bg-red-500/10 border border-red-500/40 text-red-400 text-sm rounded-xl px-4 py-3">
          {err}
        </div>
      )}

      {projects === null && !err && (
        <div className="mt-8 flex justify-center">
          <Loader2 size={28} className="text-brand-400 animate-spin" />
        </div>
      )}

      {projects && projects.length === 0 && (
        <div className="mt-6 bg-ink-850 border border-ink-700 rounded-2xl px-4 py-12 text-center text-sm text-muted">
          Noch keine Projekte.
        </div>
      )}

      {projects && projects.length > 0 && (
        <div className="mt-6 space-y-2">
          {projects.map((p) => {
            const status = projectStatus(p.takes);
            const meta = projectStatusMeta[status];
            const done = latestDoneTake(p.takes);
            return (
              <div key={p.id}
                className="flex items-center gap-4 bg-ink-850 border border-ink-700 rounded-xl px-4 py-3.5">
                <div className="w-9 h-9 rounded-lg bg-ink-800 flex items-center justify-center shrink-0">
                  <FolderOpen size={16} className="text-muted" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="font-medium truncate flex items-center gap-2">
                    <Music2 size={14} className="text-muted shrink-0" /> {p.name}
                  </p>
                  <p className="text-xs text-muted">{formatDate(p.created_at, { year: true })}</p>
                </div>
                <span className={`text-xs font-medium px-2.5 py-1 rounded-md ${meta.className}`}>
                  {meta.label}
                </span>
                <span className="text-sm text-muted w-16 text-right shrink-0">
                  {p.takes.length} Take{p.takes.length !== 1 ? "s" : ""}
                </span>
                {done ? (
                  <a href={downloadUrl(p.id, done.id)} title="Fertiges Video herunterladen"
                    className="w-8 h-8 rounded-lg hover:bg-ink-700 flex items-center justify-center text-muted hover:text-white transition-colors shrink-0">
                    <Download size={16} />
                  </a>
                ) : (
                  <span className="w-8 shrink-0" />
                )}
              </div>
            );
          })}
        </div>
      )}
    </main>
  );
}
