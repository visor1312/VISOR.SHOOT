import { useEffect, useState } from "react";
import { X, Music2, Video, Loader2, CalendarClock, Zap } from "lucide-react";
import {
  createPack, getStyles, getPlatforms, type Style, type Platform,
} from "../api";

/** Dialog: aus 1 Song/Video ein ganzes Content-Paket erzeugen (mehrere
 * Hooks x Styles x Formate). Nach dem Anlegen -> onCreated(pack_id). */
export default function CreatePackWizard({
  onClose,
  onCreated,
}: {
  onClose: () => void;
  onCreated: (packId: string) => void;
}) {
  const [video, setVideo] = useState<File | null>(null);
  const [song, setSong] = useState<File | null>(null);
  const [styles, setStyles] = useState<Style[]>([]);
  const [platforms, setPlatforms] = useState<Platform[]>([]);
  const [styleKeys, setStyleKeys] = useState<string[]>(["clean"]);
  const [platformKeys, setPlatformKeys] = useState<string[]>(["reel"]);
  const [hookCount, setHookCount] = useState(2);
  const [beatEffects, setBeatEffects] = useState(false);
  const [subtitles, setSubtitles] = useState(false);
  const [lyrics, setLyrics] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  useEffect(() => {
    getStyles().then(setStyles).catch(() => setStyles([]));
    getPlatforms().then(setPlatforms).catch(() => setPlatforms([]));
  }, []);

  function toggle(list: string[], set: (v: string[]) => void, key: string, min1: boolean) {
    if (list.includes(key)) {
      if (min1 && list.length === 1) return; // mindestens einer muss bleiben
      set(list.filter((k) => k !== key));
    } else {
      set([...list, key]);
    }
  }

  const planned = Math.min(24, hookCount * Math.max(1, styleKeys.length) * Math.max(1, platformKeys.length));

  async function submit() {
    if (!video || !song) return;
    setBusy(true);
    setErr("");
    try {
      const { pack_id } = await createPack(video, song, {
        styles: styleKeys, hookCount, platforms: platformKeys,
        beatEffects, withSubtitles: subtitles, lyrics: subtitles ? lyrics : "",
      });
      onCreated(pack_id);
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
            <CalendarClock size={20} className="text-brand-400" /> Wochen-Content erstellen
          </span>
          <button onClick={onClose} className="text-muted hover:text-white"><X size={20} /></button>
        </div>

        <div className="p-6 space-y-4 overflow-y-auto">
          <p className="text-sm text-muted leading-relaxed">
            Ein Song + Video → mehrere fertige Posts auf einen Schlag. HOOKCUT
            kombiniert die besten Hook-Stellen mit deinen Looks und Formaten.
          </p>

          <FilePick label="Performance-Video" icon={<Video size={18} className="text-brand-400" />}
            accept="video/*" file={video} onPick={setVideo} />
          <FilePick label="Song (mp3/wav oder Screen-Recording)" icon={<Music2 size={18} className="text-brand-400" />}
            accept="audio/*,video/*" file={song} onPick={setSong} />

          <div className="space-y-1.5">
            <span className="text-sm text-muted">Wie viele Hook-Varianten? ({hookCount})</span>
            <input type="range" min={1} max={4} value={hookCount}
              onChange={(e) => setHookCount(Number(e.target.value))}
              className="w-full accent-brand-500" />
          </div>

          <div className="space-y-1.5">
            <span className="text-sm text-muted">Looks (mehrere möglich):</span>
            <div className="flex flex-wrap gap-2">
              {styles.map((s) => {
                const active = styleKeys.includes(s.key);
                return (
                  <button key={s.key} onClick={() => toggle(styleKeys, setStyleKeys, s.key, true)}
                    title={s.description}
                    className={`text-xs px-3 py-1.5 rounded-lg border transition-colors ${
                      active ? "border-brand-500 bg-brand-500/15 text-white"
                             : "border-ink-700 bg-ink-800 text-muted hover:border-ink-500"}`}>
                    {s.name}
                  </button>
                );
              })}
            </div>
          </div>

          <div className="space-y-1.5">
            <span className="text-sm text-muted">Formate (mehrere möglich):</span>
            <div className="flex flex-wrap gap-2">
              {platforms.map((p) => {
                const active = platformKeys.includes(p.key);
                return (
                  <button key={p.key} onClick={() => toggle(platformKeys, setPlatformKeys, p.key, true)}
                    title={p.description}
                    className={`text-xs px-3 py-1.5 rounded-lg border transition-colors ${
                      active ? "border-brand-500 bg-brand-500/15 text-white"
                             : "border-ink-700 bg-ink-800 text-muted hover:border-ink-500"}`}>
                    {p.name} <span className="opacity-60">{p.width}×{p.height}</span>
                  </button>
                );
              })}
            </div>
          </div>

          <label className="flex items-center gap-3 cursor-pointer select-none border border-ink-700 bg-ink-800 rounded-xl px-4 py-3">
            <input type="checkbox" checked={beatEffects} onChange={(e) => setBeatEffects(e.target.checked)}
              className="w-4 h-4 accent-brand-500" />
            <Zap size={16} className="text-brand-400 shrink-0" />
            <span className="text-sm"><span className="font-medium">Beat-Effekte</span>{" "}
              <span className="text-muted">– Glitch-Puls im Takt</span></span>
          </label>

          <label className="flex items-center gap-3 cursor-pointer select-none">
            <input type="checkbox" checked={subtitles} onChange={(e) => setSubtitles(e.target.checked)}
              className="w-4 h-4 accent-brand-500" />
            <span className="text-sm">Untertitel automatisch einblenden</span>
          </label>
          {subtitles && (
            <textarea value={lyrics} onChange={(e) => setLyrics(e.target.value)} rows={3}
              placeholder="Songtext einfügen (optional, macht die Untertitel exakt)…"
              className="w-full text-sm bg-ink-900 border border-ink-700 focus:border-brand-500 rounded-xl px-3 py-2 outline-none resize-none" />
          )}

          {err && (
            <div className="bg-red-500/10 border border-red-500/40 text-red-400 text-sm rounded-xl px-4 py-3">
              {err}
            </div>
          )}
        </div>

        <div className="px-6 py-4 border-t border-ink-700 shrink-0">
          <button disabled={!video || !song || busy} onClick={submit}
            className="w-full flex items-center justify-center gap-2 bg-brand-500 hover:bg-brand-600 disabled:opacity-40 text-ink-950 font-semibold py-3 rounded-xl transition-colors">
            {busy && <Loader2 size={18} className="animate-spin" />}
            {planned} Videos erzeugen
          </button>
        </div>
      </div>
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
