import { useEffect, useRef, useState } from "react";
import { Disc3, Loader2, Download, AlertCircle, Info } from "lucide-react";
import { listCanvas, canvasDownloadUrl, type CanvasJob } from "../api";
import CreateCanvasWizard from "../components/CreateCanvasWizard";

const RUNNING_LABEL: Record<string, string> = {
  pending: "In der Warteschlange…",
  analyzing: "Song wird analysiert…",
  rendering: "Canvas wird gerendert…",
};

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("de-DE", { day: "numeric", month: "short", year: "numeric" });
}

/** Uebersicht + Erstellung von Spotify-Canvases; pollt solange etwas rendert. */
export default function CanvasPage() {
  const [canvases, setCanvases] = useState<CanvasJob[] | null>(null);
  const [err, setErr] = useState("");
  const [wizardOpen, setWizardOpen] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout>>(undefined);

  async function load(poll: boolean) {
    try {
      const list = await listCanvas();
      setCanvases(list);
      const running = list.some((c) => ["pending", "analyzing", "rendering"].includes(c.status));
      if (poll && running) timer.current = setTimeout(() => load(true), 2500);
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    }
  }

  useEffect(() => {
    load(true);
    return () => clearTimeout(timer.current);
  }, []);

  return (
    <main className="flex-1 min-w-0 px-8 py-7">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Spotify Canvas</h1>
          <p className="text-muted mt-1">
            Kurze Loops, die auf Spotify dein Cover ersetzen – für spürbar mehr Streams.
          </p>
        </div>
        <button onClick={() => setWizardOpen(true)}
          className="flex items-center gap-2 bg-brand-500 hover:bg-brand-600 text-ink-950 font-semibold text-sm px-4 py-2.5 rounded-xl transition-colors">
          <Disc3 size={18} /> Neuer Canvas
        </button>
      </div>

      <div className="mt-4 flex items-start gap-2 bg-ink-850 border border-ink-700 rounded-xl px-4 py-3 text-sm text-muted">
        <Info size={16} className="text-brand-400 shrink-0 mt-0.5" />
        <span>
          So lädst du ihn hoch: In <span className="text-white">Spotify for Artists</span> deinen Track
          öffnen → <span className="text-white">„Canvas hinzufügen"</span> → die heruntergeladene
          Datei wählen. Der Clip läuft dann stumm in Dauerschleife, während dein Song spielt.
        </span>
      </div>

      {err && (
        <div className="mt-5 bg-red-500/10 border border-red-500/40 text-red-400 text-sm rounded-xl px-4 py-3">{err}</div>
      )}

      {canvases === null && !err && (
        <div className="mt-8 flex justify-center"><Loader2 size={28} className="text-brand-400 animate-spin" /></div>
      )}

      {canvases && canvases.length === 0 && (
        <div className="mt-6 bg-ink-850 border border-ink-700 rounded-2xl px-4 py-12 text-center text-sm text-muted">
          Noch keine Canvases — erstelle deinen ersten mit „Neuer Canvas".
        </div>
      )}

      {canvases && canvases.length > 0 && (
        <div className="mt-6 grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
          {canvases.map((c) => (
            <div key={c.canvas_id} className="bg-ink-850 border border-ink-700 rounded-2xl overflow-hidden">
              {c.status === "done" && c.has_output ? (
                <video src={canvasDownloadUrl(c.canvas_id)} autoPlay loop muted playsInline
                  className="w-full aspect-[9/16] bg-black object-contain" />
              ) : (
                <div className="w-full aspect-[9/16] bg-ink-900 flex flex-col items-center justify-center gap-2 px-2 text-center">
                  {c.status === "error"
                    ? <AlertCircle size={22} className="text-red-400" />
                    : <Loader2 size={22} className="text-brand-400 animate-spin" />}
                  <span className="text-[11px] text-muted">
                    {c.status === "error" ? "Fehlgeschlagen" : (RUNNING_LABEL[c.status] ?? "…")}
                  </span>
                </div>
              )}
              <div className="p-3">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-sm font-medium capitalize truncate">{c.style ?? "Canvas"}</span>
                  <span className="text-xs text-muted shrink-0">{c.duration_sec}s</span>
                </div>
                <p className="text-xs text-muted mt-0.5">{formatDate(c.created_at)}</p>
                {c.status === "done" && c.has_output && (
                  <a href={canvasDownloadUrl(c.canvas_id)} download
                    className="mt-2 flex items-center justify-center gap-1.5 w-full bg-ink-800 hover:bg-ink-700 text-muted hover:text-white text-xs py-1.5 rounded-lg transition-colors">
                    <Download size={13} /> Herunterladen
                  </a>
                )}
                {c.status === "error" && c.error && (
                  <p className="text-xs text-red-400/80 mt-1 line-clamp-2">{c.error}</p>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {wizardOpen && (
        <CreateCanvasWizard onClose={() => setWizardOpen(false)}
          onCreated={() => { setWizardOpen(false); clearTimeout(timer.current); load(true); }} />
      )}
    </main>
  );
}
