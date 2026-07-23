import { useEffect, useState } from "react";
import { Video, Download, Sparkles, Loader2 } from "lucide-react";
import { listEditJobs, editDownloadUrl, type EditJobSummary } from "../api";
import { useApp } from "../components/app-context";
import { formatDate, editJobStatusMeta } from "../lib/format";

/** Vollwertige Galerie aller Wizard-Reels des angemeldeten Nutzers. */
export default function ReelsPage() {
  const { openWizard, refreshKey } = useApp();
  const [reels, setReels] = useState<EditJobSummary[] | null>(null);
  const [err, setErr] = useState("");

  // refreshKey zaehlt nach jedem Wizard-Schluss hoch -> Liste neu laden,
  // damit ein frisch erstelltes Reel sofort auftaucht.
  useEffect(() => {
    let cancelled = false;
    listEditJobs(100)
      .then((r) => !cancelled && setReels(r))
      .catch((e) => !cancelled && setErr(e instanceof Error ? e.message : String(e)));
    return () => { cancelled = true; };
  }, [refreshKey]);

  return (
    <main className="flex-1 min-w-0 px-8 py-7">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Meine fertigen Reels</h1>
          <p className="text-muted mt-1">Alle Reels, die du mit dem Assistenten erstellt hast.</p>
        </div>
        <button onClick={openWizard}
          className="flex items-center gap-2 bg-brand-500 hover:bg-brand-600 text-ink-950 font-semibold text-sm px-4 py-2.5 rounded-xl transition-colors">
          <Sparkles size={18} /> Neues Reel
        </button>
      </div>

      {err && (
        <div className="mt-5 bg-red-500/10 border border-red-500/40 text-red-400 text-sm rounded-xl px-4 py-3">
          {err}
        </div>
      )}

      {reels === null && !err && (
        <div className="mt-8 flex justify-center">
          <Loader2 size={28} className="text-brand-400 animate-spin" />
        </div>
      )}

      {reels && reels.length === 0 && (
        <div className="mt-6 bg-ink-850 border border-ink-700 rounded-2xl px-4 py-12 text-center text-sm text-muted">
          Noch keine Reels — erstelle dein erstes mit „Neues Reel".
        </div>
      )}

      {reels && reels.length > 0 && (
        <div className="mt-6 grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {reels.map((r) => {
            const meta = editJobStatusMeta(r.status);
            const ready = (r.outputs ?? []).filter((o) => o.ready);
            return (
              <div key={r.job_id} className="bg-ink-850 border border-ink-700 rounded-2xl overflow-hidden">
                {r.status === "done" && r.has_output ? (
                  <video src={editDownloadUrl(r.job_id)} controls preload="metadata"
                    className="w-full aspect-[9/16] max-h-80 bg-black object-contain" />
                ) : (
                  <div className="w-full aspect-[9/16] max-h-80 bg-ink-900 flex items-center justify-center">
                    {r.status === "error"
                      ? <span className="text-sm text-red-400">Fehlgeschlagen</span>
                      : <Loader2 size={24} className="text-brand-400 animate-spin" />}
                  </div>
                )}
                <div className="p-4">
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2 min-w-0">
                      <Video size={15} className="text-muted shrink-0" />
                      <span className="text-sm font-medium truncate">
                        {r.style ? `Style: ${r.style}` : "Reel"}
                      </span>
                    </div>
                    <span className={`text-xs font-medium px-2 py-0.5 rounded-md shrink-0 ${meta.className}`}>
                      {meta.label}
                    </span>
                  </div>
                  <p className="text-xs text-muted mt-1">{formatDate(r.created_at, { year: true })}</p>
                  {r.status === "done" && ready.length > 0 && (
                    <div className="flex flex-wrap gap-1.5 mt-3">
                      {ready.map((o) => (
                        <a key={o.platform} href={editDownloadUrl(r.job_id, o.platform)} download
                          title={`${o.name} herunterladen (${o.width}×${o.height})`}
                          className="text-xs px-2 py-1 rounded-lg bg-ink-800 hover:bg-ink-700 text-muted hover:text-white transition-colors flex items-center gap-1">
                          <Download size={13} /> {o.platform}
                        </a>
                      ))}
                    </div>
                  )}
                  {r.status === "error" && r.error && (
                    <p className="text-xs text-red-400/80 mt-2 line-clamp-2">{r.error}</p>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </main>
  );
}
