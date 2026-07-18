import { useEffect, useState } from "react";
import {
  X, Music2, Video, Loader2, AlertCircle, Check, Sparkles, Zap, Download,
} from "lucide-react";
import {
  editAnalyze, editHook, editRender, waitForEdit, editDownloadUrl, getStyles,
  type Style, type EditJob,
} from "../api";

type Phase =
  | "form" | "syncing" | "hookAsk" | "hooking" | "styleSelect" | "rendering" | "done" | "error";

export default function CreateReelWizard({ onClose }: { onClose: () => void }) {
  const [video, setVideo] = useState<File | null>(null);
  const [song, setSong] = useState<File | null>(null);
  const [subtitles, setSubtitles] = useState(false);
  const [phase, setPhase] = useState<Phase>("form");
  const [jobId, setJobId] = useState("");
  const [job, setJob] = useState<EditJob | null>(null);
  const [useHook, setUseHook] = useState(false);
  const [styles, setStyles] = useState<Style[]>([]);
  const [err, setErr] = useState("");

  useEffect(() => {
    getStyles().then(setStyles).catch(() => setStyles([]));
  }, []);

  function fail(e: unknown) {
    setErr(e instanceof Error ? e.message : String(e));
    setPhase("error");
  }

  async function start() {
    if (!video || !song) return;
    setPhase("syncing");
    try {
      const id = await editAnalyze(video, song, subtitles);
      setJobId(id);
      const j = await waitForEdit(id, ["synced"]);
      if (j.status === "error") return fail(j.error ?? "Sync fehlgeschlagen.");
      setJob(j);
      setPhase("hookAsk");
    } catch (e) { fail(e); }
  }

  async function chooseHook(want: boolean) {
    setUseHook(want);
    if (!want) { setPhase("styleSelect"); return; }
    setPhase("hooking");
    try {
      await editHook(jobId);
      const j = await waitForEdit(jobId, ["hooked"]);
      if (j.status === "error") return fail(j.error ?? "Hook-Suche fehlgeschlagen.");
      setJob(j);
      setPhase("styleSelect");
    } catch (e) { fail(e); }
  }

  async function render(styleKey: string) {
    setPhase("rendering");
    try {
      await editRender(jobId, styleKey, useHook);
      const j = await waitForEdit(jobId, ["done"], undefined, { timeoutMs: 30 * 60 * 1000 });
      if (j.status === "error") return fail(j.error ?? "Rendern fehlgeschlagen.");
      setJob(j);
      setPhase("done");
    } catch (e) { fail(e); }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
      <div className="w-full max-w-lg bg-ink-850 border border-ink-700 rounded-2xl overflow-hidden">
        <div className="flex items-center justify-between px-6 py-4 border-b border-ink-700">
          <span className="flex items-center gap-2.5 font-semibold">
            <Sparkles size={20} className="text-brand-400" /> Reel erstellen
          </span>
          <button onClick={onClose} className="text-muted hover:text-white"><X size={20} /></button>
        </div>

        <div className="p-6">
          {phase === "form" && (
            <div className="space-y-4">
              <FilePick label="Performance-Video" icon={<Video size={18} className="text-brand-400" />}
                accept="video/*" file={video} onPick={setVideo} />
              <FilePick label="Song (mp3/wav oder Screen-Recording)" icon={<Music2 size={18} className="text-brand-400" />}
                accept="audio/*,video/*" file={song} onPick={setSong} />
              <label className="flex items-center gap-3 cursor-pointer select-none">
                <input type="checkbox" checked={subtitles} onChange={(e) => setSubtitles(e.target.checked)}
                  className="w-4 h-4 accent-brand-500" />
                <span className="text-sm">Untertitel automatisch einblenden</span>
              </label>
              <button disabled={!video || !song} onClick={start}
                className="w-full bg-brand-500 hover:bg-brand-600 disabled:opacity-40 text-ink-950 font-semibold py-3 rounded-xl transition-colors">
                Los geht's
              </button>
            </div>
          )}

          {phase === "syncing" && <Busy text="Ton wird synchronisiert…" hint="Das ganze Video wird lippensynchron gelegt." />}

          {phase === "hookAsk" && (
            <div className="space-y-4">
              <div className="flex items-center gap-2 text-brand-400">
                <Check size={18} /> <span className="font-medium">Synchronisiert!</span>
                {job?.confidence != null && (
                  <span className="text-xs text-muted">Konfidenz {Math.round(job.confidence * 100)}%</span>
                )}
              </div>
              <p className="text-sm text-muted">
                Soll HOOKCUT den <span className="text-white font-medium">viralsten Teil</span> deines
                Songs suchen und das Reel darauf zuschneiden?
              </p>
              <div className="grid grid-cols-2 gap-3">
                <button onClick={() => chooseHook(true)}
                  className="flex items-center justify-center gap-2 bg-brand-500 hover:bg-brand-600 text-ink-950 font-semibold py-3 rounded-xl">
                  <Zap size={16} /> Viralsten Teil
                </button>
                <button onClick={() => chooseHook(false)}
                  className="bg-ink-800 hover:bg-ink-700 text-white font-medium py-3 rounded-xl">
                  Ganzes Video
                </button>
              </div>
            </div>
          )}

          {phase === "hooking" && <Busy text="Viralster Teil wird gesucht…" hint="KI analysiert die Song-Struktur." />}

          {phase === "styleSelect" && (
            <div className="space-y-4">
              {useHook && job?.hook && (
                <p className="text-xs text-brand-400">
                  Hook: {job.hook.start_sec.toFixed(1)}s – {job.hook.end_sec.toFixed(1)}s
                </p>
              )}
              {useHook && !job?.hook && (
                <p className="text-xs text-muted">
                  Kein passender Hook im gefilmten Bereich – ganzes Video wird verwendet.
                </p>
              )}
              <p className="text-sm text-muted">Wähle einen Look – wird per Knopfdruck erzeugt:</p>
              <div className="grid grid-cols-2 gap-3">
                {styles.map((s) => (
                  <button key={s.key} onClick={() => render(s.key)}
                    className="text-left border border-ink-700 hover:border-brand-500 bg-ink-800 rounded-xl p-3 transition-colors">
                    <p className="font-semibold text-sm">{s.name}</p>
                    <p className="text-xs text-muted mt-1 leading-snug">{s.description}</p>
                  </button>
                ))}
              </div>
            </div>
          )}

          {phase === "rendering" && (
            <Busy text="Dein Reel wird erstellt…" hint="Video schneiden, Effekte, Export – das dauert ein paar Minuten." />
          )}

          {phase === "done" && job?.has_output && (
            <div className="space-y-4">
              <div className="flex items-center gap-2 text-brand-400">
                <Check size={20} /> <span className="font-medium">Fertig!</span>
              </div>
              <video src={editDownloadUrl(jobId)} controls className="w-full rounded-xl bg-black max-h-[55vh]" />
              <a href={editDownloadUrl(jobId)} download
                className="flex items-center justify-center gap-2 w-full bg-brand-500 hover:bg-brand-600 text-ink-950 font-semibold py-3 rounded-xl">
                <Download size={18} /> Reel herunterladen
              </a>
            </div>
          )}

          {phase === "error" && (
            <div className="space-y-4">
              <div className="flex items-center gap-2 text-red-400"><AlertCircle size={20} /><span className="font-medium">Fehlgeschlagen</span></div>
              <pre className="text-xs text-muted bg-ink-900 rounded-lg p-3 whitespace-pre-wrap break-words max-h-40 overflow-auto">{err}</pre>
              <button onClick={() => setPhase("form")} className="w-full bg-ink-800 hover:bg-ink-700 text-white font-medium py-3 rounded-xl">
                Nochmal
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function Busy({ text, hint }: { text: string; hint: string }) {
  return (
    <div className="flex flex-col items-center py-8 text-center">
      <Loader2 size={40} className="text-brand-400 animate-spin" />
      <p className="mt-4 font-medium">{text}</p>
      <p className="text-sm text-muted mt-1">{hint}</p>
    </div>
  );
}

function FilePick({ label, icon, accept, file, onPick }: {
  label: string; icon: React.ReactNode; accept: string; file: File | null; onPick: (f: File) => void;
}) {
  return (
    <label className="block cursor-pointer">
      <span className="text-sm text-muted">{label}</span>
      <div className="mt-1.5 flex items-center gap-3 border border-dashed border-ink-700 hover:border-brand-500/60 rounded-xl px-4 py-3 transition-colors">
        {icon}
        <span className="text-sm flex-1 min-w-0 truncate">{file ? file.name : "Datei auswählen…"}</span>
      </div>
      <input type="file" accept={accept} className="hidden"
        onChange={(e) => e.target.files?.[0] && onPick(e.target.files[0])} />
    </label>
  );
}
