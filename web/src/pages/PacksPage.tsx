import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { CalendarClock, Loader2, CheckCircle2, AlertCircle } from "lucide-react";
import { listPacks, type PackSummary, type PackStatus } from "../api";
import CreatePackWizard from "../components/CreatePackWizard";
import { formatDate } from "../lib/format";

function statusMeta(status: PackStatus): { label: string; className: string } {
  if (status === "done") return { label: "Fertig", className: "bg-brand-500/15 text-brand-400" };
  if (status === "error") return { label: "Fehler", className: "bg-red-500/15 text-red-400" };
  return { label: "Läuft…", className: "bg-amber-500/15 text-amber-400" };
}

/** Uebersicht aller Content-Pakete + Erstell-Dialog. */
export default function PacksPage() {
  const navigate = useNavigate();
  const [packs, setPacks] = useState<PackSummary[] | null>(null);
  const [err, setErr] = useState("");
  const [wizardOpen, setWizardOpen] = useState(false);

  useEffect(() => {
    let cancelled = false;
    listPacks()
      .then((p) => !cancelled && setPacks(p))
      .catch((e) => !cancelled && setErr(e instanceof Error ? e.message : String(e)));
    return () => { cancelled = true; };
  }, []);

  return (
    <main className="flex-1 min-w-0 px-8 py-7">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Wochen-Content</h1>
          <p className="text-muted mt-1">
            Ein Song → mehrere fertige Posts auf einen Schlag. Genug für eine ganze Woche.
          </p>
        </div>
        <button onClick={() => setWizardOpen(true)}
          className="flex items-center gap-2 bg-brand-500 hover:bg-brand-600 text-ink-950 font-semibold text-sm px-4 py-2.5 rounded-xl transition-colors">
          <CalendarClock size={18} /> Neues Paket
        </button>
      </div>

      {err && (
        <div className="mt-5 bg-red-500/10 border border-red-500/40 text-red-400 text-sm rounded-xl px-4 py-3">{err}</div>
      )}

      {packs === null && !err && (
        <div className="mt-8 flex justify-center"><Loader2 size={28} className="text-brand-400 animate-spin" /></div>
      )}

      {packs && packs.length === 0 && (
        <div className="mt-6 bg-ink-850 border border-ink-700 rounded-2xl px-4 py-12 text-center text-sm text-muted">
          Noch keine Pakete — erstelle dein erstes mit „Neues Paket".
        </div>
      )}

      {packs && packs.length > 0 && (
        <div className="mt-6 space-y-2">
          {packs.map((p) => {
            const meta = statusMeta(p.status);
            const Icon = p.status === "done" ? CheckCircle2 : p.status === "error" ? AlertCircle : Loader2;
            return (
              <button key={p.pack_id} onClick={() => navigate(`/wochen-content/${p.pack_id}`)}
                className="w-full flex items-center gap-4 bg-ink-850 border border-ink-700 hover:bg-ink-800 rounded-xl px-4 py-3.5 text-left transition-colors">
                <div className="w-9 h-9 rounded-lg bg-ink-800 flex items-center justify-center shrink-0">
                  <Icon size={16} className={p.status === "error" ? "text-red-400" : "text-brand-400"} />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="font-medium">Content-Paket · {p.item_count} Videos</p>
                  <p className="text-xs text-muted">{formatDate(p.created_at, { year: true })}</p>
                </div>
                <span className="text-sm text-muted">{p.done_count}/{p.item_count} fertig</span>
                <span className={`text-xs font-medium px-2.5 py-1 rounded-md ${meta.className}`}>{meta.label}</span>
              </button>
            );
          })}
        </div>
      )}

      {wizardOpen && (
        <CreatePackWizard onClose={() => setWizardOpen(false)}
          onCreated={(id) => { setWizardOpen(false); navigate(`/wochen-content/${id}`); }} />
      )}
    </main>
  );
}
