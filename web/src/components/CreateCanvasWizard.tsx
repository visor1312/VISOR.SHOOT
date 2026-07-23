import { useEffect, useState } from "react";
import { X, Music2, Video, Loader2, Disc3, Zap } from "lucide-react";
import { createCanvas, getStyles, type Style } from "../api";
import FilePick from "./FilePick";

/** Dialog: aus Video + Song einen 3-8s Spotify-Canvas erzeugen. */
export default function CreateCanvasWizard({
  onClose,
  onCreated,
}: {
  onClose: () => void;
  onCreated: (canvasId: string) => void;
}) {
  const [video, setVideo] = useState<File | null>(null);
  const [song, setSong] = useState<File | null>(null);
  const [styles, setStyles] = useState<Style[]>([]);
  const [styleKey, setStyleKey] = useState("clean");
  const [duration, setDuration] = useState(6);
  const [useHook, setUseHook] = useState(true);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  useEffect(() => {
    getStyles().then(setStyles).catch(() => setStyles([]));
  }, []);

  async function submit() {
    if (!video || !song) return;
    setBusy(true);
    setErr("");
    try {
      const { canvas_id } = await createCanvas(video, song, {
        style: styleKey, durationSec: duration, useHook,
      });
      onCreated(canvas_id);
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
      setBusy(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
      <div className="w-full max-w-lg bg-ink-850 border border-ink-700 rounded-2xl overflow-hidden max-h-[92vh] flex flex-col">
        <div className="flex items-center justify-between px-6 py-4 border-b border-ink-700 shrink-0">
          <span className="flex items-center gap-2.5 font-semibold">
            <Disc3 size={20} className="text-brand-400" /> Spotify Canvas erstellen
          </span>
          <button onClick={onClose} className="text-muted hover:text-white"><X size={20} /></button>
        </div>

        <div className="p-6 space-y-4 overflow-y-auto">
          <p className="text-sm text-muted leading-relaxed">
            Ein Canvas ist ein kurzer, sich wiederholender 9:16-Clip, der auf
            Spotify dein Cover ersetzt. Tracks mit Canvas bekommen deutlich mehr
            Streams. HOOKCUT schneidet den energiereichsten Moment zu.
          </p>

          <FilePick label="Performance-Video" icon={<Video size={18} className="text-brand-400" />}
            accept="video/*" file={video} onPick={setVideo} />
          <FilePick label="Song (mp3/wav oder Screen-Recording)" icon={<Music2 size={18} className="text-brand-400" />}
            accept="audio/*,video/*" file={song} onPick={setSong} />

          <div className="space-y-1.5">
            <span className="text-sm text-muted">Länge: {duration} Sekunden (Spotify: 3–8s)</span>
            <input type="range" min={3} max={8} value={duration}
              onChange={(e) => setDuration(Number(e.target.value))}
              className="w-full accent-brand-500" />
          </div>

          <div className="space-y-1.5">
            <span className="text-sm text-muted">Look:</span>
            <div className="flex flex-wrap gap-2">
              {styles.map((s) => (
                <button key={s.key} onClick={() => setStyleKey(s.key)} title={s.description}
                  className={`text-xs px-3 py-1.5 rounded-lg border transition-colors ${
                    styleKey === s.key ? "border-brand-500 bg-brand-500/15 text-white"
                                       : "border-ink-700 bg-ink-800 text-muted hover:border-ink-500"}`}>
                  {s.name}
                </button>
              ))}
            </div>
          </div>

          <label className="flex items-center gap-3 cursor-pointer select-none border border-ink-700 bg-ink-800 rounded-xl px-4 py-3">
            <input type="checkbox" checked={useHook} onChange={(e) => setUseHook(e.target.checked)}
              className="w-4 h-4 accent-brand-500" />
            <Zap size={16} className="text-brand-400 shrink-0" />
            <span className="text-sm"><span className="font-medium">Auf den Hook schneiden</span>{" "}
              <span className="text-muted">– energiereichsten Moment nehmen</span></span>
          </label>

          {err && (
            <div className="bg-red-500/10 border border-red-500/40 text-red-400 text-sm rounded-xl px-4 py-3">{err}</div>
          )}
        </div>

        <div className="px-6 py-4 border-t border-ink-700 shrink-0">
          <button disabled={!video || !song || busy} onClick={submit}
            className="w-full flex items-center justify-center gap-2 bg-brand-500 hover:bg-brand-600 disabled:opacity-40 text-ink-950 font-semibold py-3 rounded-xl transition-colors">
            {busy && <Loader2 size={18} className="animate-spin" />} Canvas erstellen
          </button>
        </div>
      </div>
    </div>
  );
}
