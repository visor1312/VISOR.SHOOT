import { useEffect, useState } from "react";
import {
  X, Music2, Video, Loader2, AlertCircle, Check, Sparkles, Zap, Download,
} from "lucide-react";
import {
  editAnalyze, editHook, editRender, waitForEdit, editDownloadUrl, getStyles,
  getPlatforms, type Style, type Platform, type EditJob,
} from "../api";
import FilePick from "./FilePick";

type Phase =
  | "form" | "syncing" | "hookAsk" | "hooking" | "styleSelect" | "rendering" | "done" | "error";

export default function CreateReelWizard({ onClose }: { onClose: () => void }) {
  const [video, setVideo] = useState<File | null>(null);
  const [song, setSong] = useState<File | null>(null);
  const [subtitles, setSubtitles] = useState(false);
  const [lyrics, setLyrics] = useState("");
  const [phase, setPhase] = useState<Phase>("form");
  const [jobId, setJobId] = useState("");
  const [job, setJob] = useState<EditJob | null>(null);
  const [useHook, setUseHook] = useState(false);
  const [beatEffects, setBeatEffects] = useState(false);
  const [styles, setStyles] = useState<Style[]>([]);
  const [platforms, setPlatforms] = useState<Platform[]>([]);
  const [platformKeys, setPlatformKeys] = useState<string[]>(["reel"]);
  const [err, setErr] = useState("");

  useEffect(() => {
    getStyles().then(setStyles).catch(() => setStyles([]));
    getPlatforms().then(setPlatforms).catch(() => setPlatforms([]));
  }, []);

  function togglePlatform(key: string) {
    setPlatformKeys((prev) => {
      if (prev.includes(key)) {
        // Mindestens ein Format muss gewaehlt bleiben.
        return prev.length > 1 ? prev.filter((k) => k !== key) : prev;
      }
      return [...prev, key];
    });
  }

  function fail(e: unknown) {
    setErr(e instanceof Error ? e.message : String(e));
    setPhase("error");
  }

  async function start() {
    if (!video || !song) return;
    setPhase("syncing");
    try {
      const id = await editAnalyze(video, song, subtitles, subtitles ? lyrics : "");
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
      await editRender(jobId, styleKey, useHook, beatEffects, platformKeys);
      const j = await waitForEdit(jobId, ["done"], setJob,
        { timeoutMs: 60 * 60 * 1000 });
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
              {subtitles && (
                <div className="space-y-1.5">
                  <span className="text-sm text-muted">
                    Songtext einfügen (optional) – macht die Untertitel exakt
                  </span>
                  <textarea
                    value={lyrics}
                    onChange={(e) => setLyrics(e.target.value)}
                    rows={4}
                    placeholder="Songtext hier einfügen… (leer lassen = automatische Erkennung)"
                    className="w-full text-sm bg-ink-900 border border-ink-700 focus:border-brand-500 rounded-xl px-3 py-2 outline-none resize-none"
                  />
                </div>
              )}
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
                Soll selfsign den <span className="text-white font-medium">viralsten Teil</span> deines
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
              {platforms.length > 0 && (
                <div className="space-y-1.5">
                  <p className="text-sm text-muted">Formate – gerne mehrere, jedes wird einzeln gerendert:</p>
                  <div className="flex flex-wrap gap-2">
                    {platforms.map((p) => {
                      const active = platformKeys.includes(p.key);
                      return (
                        <button key={p.key} onClick={() => togglePlatform(p.key)} title={p.description}
                          className={`text-xs px-3 py-2 rounded-lg border transition-colors ${
                            active
                              ? "border-brand-500 bg-brand-500/15 text-white"
                              : "border-ink-700 bg-ink-800 text-muted hover:border-ink-500"
                          }`}>
                          {p.name} <span className="opacity-60">{p.width}×{p.height}</span>
                        </button>
                      );
                    })}
                  </div>
                </div>
              )}
              <label className="flex items-center gap-3 cursor-pointer select-none border border-ink-700 bg-ink-800 rounded-xl px-4 py-3">
                <input type="checkbox" checked={beatEffects} onChange={(e) => setBeatEffects(e.target.checked)}
                  className="w-4 h-4 accent-brand-500" />
                <Zap size={16} className="text-brand-400 shrink-0" />
                <span className="text-sm">
                  <span className="font-medium">Beat-Effekte</span>{" "}
                  <span className="text-muted">– Glitch-Puls im Takt der Musik</span>
                </span>
              </label>
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

          {phase === "rendering" && (() => {
            const total = job?.outputs?.length ?? platformKeys.length;
            const ready = job?.outputs?.filter((o) => o.ready).length ?? 0;
            return (
              <Busy text="Dein Reel wird erstellt…"
                hint={total > 1
                  ? `Format ${Math.min(ready + 1, total)} von ${total} – jedes Format wird einzeln gerendert.`
                  : "Video schneiden, Effekte, Export – das dauert ein paar Minuten."} />
            );
          })()}

          {phase === "done" && job?.has_output && (
            <div className="space-y-4">
              <div className="flex items-center gap-2 text-brand-400">
                <Check size={20} /> <span className="font-medium">Fertig!</span>
              </div>
              <video src={editDownloadUrl(jobId)} controls className="w-full rounded-xl bg-black max-h-[55vh]" />
              {job.outputs && job.outputs.length > 1 ? (
                <div className="space-y-2">
                  {job.outputs.filter((o) => o.ready).map((o) => (
                    <a key={o.platform} href={editDownloadUrl(jobId, o.platform)} download
                      className="flex items-center justify-center gap-2 w-full bg-brand-500 hover:bg-brand-600 text-ink-950 font-semibold py-2.5 rounded-xl">
                      <Download size={16} /> {o.name} ({o.width}×{o.height})
                    </a>
                  ))}
                </div>
              ) : (
                <a href={editDownloadUrl(jobId)} download
                  className="flex items-center justify-center gap-2 w-full bg-brand-500 hover:bg-brand-600 text-ink-950 font-semibold py-3 rounded-xl">
                  <Download size={18} /> Reel herunterladen
                </a>
              )}
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
