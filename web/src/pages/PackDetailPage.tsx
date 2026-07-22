import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { ArrowLeft, Download, Loader2, Video, AlertCircle } from "lucide-react";
import { getPack, packItemDownloadUrl, type PackDetail, type PackStatus } from "../api";

const RUNNING_LABEL: Record<string, string> = {
  pending: "In der Warteschlange…",
  analyzing: "Song wird analysiert (Sync + Hooks)…",
  transcribing: "Untertitel werden erkannt…",
  rendering: "Videos werden gerendert…",
};

function itemBadge(status: PackStatus): { label: string; className: string } {
  if (status === "done") return { label: "Fertig", className: "bg-brand-500/15 text-brand-400" };
  if (status === "error") return { label: "Fehler", className: "bg-red-500/15 text-red-400" };
  if (status === "rendering") return { label: "Rendert…", className: "bg-amber-500/15 text-amber-400" };
  return { label: "Wartet", className: "bg-ink-700 text-muted" };
}

/** Detail eines Content-Pakets: Grid aller Videos mit Status + Download.
 * Pollt, solange noch etwas laeuft. */
export default function PackDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [pack, setPack] = useState<PackDetail | null>(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    if (!id) return;
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout>;

    async function tick() {
      try {
        const p = await getPack(id!);
        if (cancelled) return;
        setPack(p);
        const running = ["pending", "analyzing", "transcribing", "rendering"].includes(p.status)
          || p.items.some((i) => ["pending", "rendering"].includes(i.status));
        if (running) timer = setTimeout(tick, 2500);
      } catch (e) {
        if (!cancelled) setErr(e instanceof Error ? e.message : String(e));
      }
    }
    tick();
    return () => { cancelled = true; clearTimeout(timer); };
  }, [id]);

  return (
    <main className="flex-1 min-w-0 px-8 py-7">
      <button onClick={() => navigate("/wochen-content")}
        className="flex items-center gap-1.5 text-sm text-muted hover:text-white transition-colors">
        <ArrowLeft size={16} /> Zurück zu Wochen-Content
      </button>

      <h1 className="text-3xl font-bold tracking-tight mt-3">Content-Paket</h1>

      {err && (
        <div className="mt-5 bg-red-500/10 border border-red-500/40 text-red-400 text-sm rounded-xl px-4 py-3">{err}</div>
      )}

      {!pack && !err && (
        <div className="mt-8 flex justify-center"><Loader2 size={28} className="text-brand-400 animate-spin" /></div>
      )}

      {pack && (
        <>
          {pack.status === "error" && (
            <div className="mt-4 flex items-center gap-2 bg-red-500/10 border border-red-500/40 text-red-400 text-sm rounded-xl px-4 py-3">
              <AlertCircle size={18} /> {pack.error ?? "Fehlgeschlagen."}
            </div>
          )}
          {["pending", "analyzing", "transcribing", "rendering"].includes(pack.status) && (
            <p className="mt-3 flex items-center gap-2 text-sm text-muted">
              <Loader2 size={16} className="animate-spin text-brand-400" />
              {RUNNING_LABEL[pack.status] ?? "Wird verarbeitet…"} ({pack.done_count}/{pack.item_count} fertig)
            </p>
          )}
          {pack.status === "done" && (
            <p className="mt-3 text-sm text-brand-400">{pack.item_count} Videos fertig — lade sie dir herunter.</p>
          )}

          <div className="mt-6 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {pack.items.map((it) => {
              const badge = itemBadge(it.status);
              return (
                <div key={it.idx} className="bg-ink-850 border border-ink-700 rounded-2xl overflow-hidden">
                  {it.ready ? (
                    <video src={packItemDownloadUrl(pack.pack_id, it.idx)} controls preload="metadata"
                      className="w-full aspect-[9/16] max-h-72 bg-black object-contain" />
                  ) : (
                    <div className="w-full aspect-[9/16] max-h-72 bg-ink-900 flex items-center justify-center">
                      {it.status === "error"
                        ? <AlertCircle size={22} className="text-red-400" />
                        : it.status === "rendering"
                          ? <Loader2 size={22} className="text-brand-400 animate-spin" />
                          : <Video size={22} className="text-ink-600" />}
                    </div>
                  )}
                  <div className="p-3">
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-sm font-medium capitalize truncate">{it.style}</span>
                      <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded shrink-0 ${badge.className}`}>{badge.label}</span>
                    </div>
                    <p className="text-xs text-muted mt-0.5">Hook {it.hook_index + 1} · {it.platform}</p>
                    {it.ready && (
                      <a href={packItemDownloadUrl(pack.pack_id, it.idx)} download
                        className="mt-2 flex items-center justify-center gap-1.5 w-full bg-ink-800 hover:bg-ink-700 text-muted hover:text-white text-xs py-1.5 rounded-lg transition-colors">
                        <Download size={13} /> Herunterladen
                      </a>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </>
      )}
    </main>
  );
}
