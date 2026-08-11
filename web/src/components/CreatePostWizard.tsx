import { useEffect, useState } from "react";
import { X, Music2, Loader2, Send } from "lucide-react";
import { createPost, getPostCategories, type PostCategory, type Post } from "../api";
import FilePick from "./FilePick";

/** Dialog: ein offenes Projekt posten ("mir fehlt noch ein Refrain"). */
export default function CreatePostWizard({
  onClose,
  onCreated,
}: {
  onClose: () => void;
  onCreated: (post: Post) => void;
}) {
  const [kategorien, setKategorien] = useState<PostCategory[]>([]);
  const [gewaehlt, setGewaehlt] = useState<string[]>([]);
  const [titel, setTitel] = useState("");
  const [text, setText] = useState("");
  const [genres, setGenres] = useState("");
  const [bpm, setBpm] = useState("");
  const [audio, setAudio] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  useEffect(() => {
    getPostCategories().then(setKategorien).catch(() => setKategorien([]));
  }, []);

  function umschalten(key: string) {
    setGewaehlt((v) => (v.includes(key) ? v.filter((k) => k !== key) : [...v, key]));
  }

  const kannSenden = titel.trim() !== "" && gewaehlt.length > 0 && !busy;

  async function senden() {
    if (!kannSenden) return;
    setBusy(true);
    setErr("");
    try {
      const post = await createPost({
        title: titel, categories: gewaehlt, body: text, genres,
        bpm: bpm ? Number(bpm) : 0, audio,
      });
      onCreated(post);
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
            <Music2 size={20} className="text-brand-400" /> Offenes Projekt posten
          </span>
          <button onClick={onClose} className="text-muted hover:text-white"><X size={20} /></button>
        </div>

        <div className="p-6 space-y-4 overflow-y-auto">
          <p className="text-sm text-muted leading-relaxed">
            Sag der Community, woran du arbeitest und was dir noch fehlt.
            Andere Musiker können sich bei dir melden.
          </p>

          <label className="block">
            <span className="text-sm text-muted">Worum geht's?</span>
            <input value={titel} onChange={(e) => setTitel(e.target.value)}
              maxLength={120} placeholder="z.B. Strophe steht, Hook fehlt"
              className="mt-1.5 w-full text-sm bg-ink-800 border border-ink-700 focus:border-brand-500 rounded-xl px-3 py-2.5 outline-none" />
          </label>

          <div>
            <span className="text-sm text-muted">Was suchst du? (mindestens eins)</span>
            <div className="mt-2 flex flex-wrap gap-2">
              {kategorien.map((k) => {
                const aktiv = gewaehlt.includes(k.key);
                return (
                  <button key={k.key} type="button" onClick={() => umschalten(k.key)}
                    className={`text-sm px-3 py-1.5 rounded-xl border transition-colors ${
                      aktiv
                        ? "bg-brand-500 border-brand-500 text-ink-950 font-medium"
                        : "bg-ink-800 border-ink-700 text-muted hover:text-white"
                    }`}>
                    {k.name}
                  </button>
                );
              })}
            </div>
          </div>

          <label className="block">
            <span className="text-sm text-muted">Mehr dazu (optional)</span>
            <textarea value={text} onChange={(e) => setText(e.target.value)}
              rows={4} maxLength={2000}
              placeholder="Worum geht's im Song? Was stellst du dir vor?"
              className="mt-1.5 w-full text-sm bg-ink-800 border border-ink-700 focus:border-brand-500 rounded-xl px-3 py-2.5 outline-none resize-none" />
          </label>

          <div className="grid grid-cols-2 gap-3">
            <label className="block">
              <span className="text-sm text-muted">Genres</span>
              <input value={genres} onChange={(e) => setGenres(e.target.value)}
                placeholder="Deutschrap, Trap"
                className="mt-1.5 w-full text-sm bg-ink-800 border border-ink-700 focus:border-brand-500 rounded-xl px-3 py-2.5 outline-none" />
            </label>
            <label className="block">
              <span className="text-sm text-muted">BPM (optional)</span>
              <input value={bpm} onChange={(e) => setBpm(e.target.value.replace(/\D/g, ""))}
                inputMode="numeric" placeholder="90"
                className="mt-1.5 w-full text-sm bg-ink-800 border border-ink-700 focus:border-brand-500 rounded-xl px-3 py-2.5 outline-none" />
            </label>
          </div>

          <FilePick label="Hörprobe (optional, max. 30 Sekunden)"
            icon={<Music2 size={18} className="text-brand-400" />}
            accept="audio/*" file={audio} onPick={setAudio} />
          <p className="text-xs text-ink-600 -mt-2">
            mp3, m4a, wav oder ogg – höchstens 8 MB. Ein kurzer Ausschnitt reicht,
            damit andere hören, worum es geht.
          </p>

          {err && (
            <div className="bg-red-500/10 border border-red-500/40 text-red-400 text-sm rounded-xl px-4 py-3">
              {err}
            </div>
          )}
        </div>

        <div className="px-6 py-4 border-t border-ink-700 shrink-0">
          <button onClick={senden} disabled={!kannSenden}
            className="w-full flex items-center justify-center gap-2 bg-brand-500 hover:bg-brand-600 disabled:opacity-40 text-ink-950 font-semibold py-3 rounded-xl transition-colors">
            {busy ? <Loader2 size={18} className="animate-spin" /> : <Send size={18} />}
            Projekt posten
          </button>
        </div>
      </div>
    </div>
  );
}
