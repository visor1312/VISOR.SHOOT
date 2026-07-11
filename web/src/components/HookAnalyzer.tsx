import { useState } from "react";
import { X, Zap, Music2, Loader2, AlertCircle, Mic2 } from "lucide-react";
import {
  analyzeHook,
  waitForHook,
  hookPreviewUrl,
  type HookCandidate,
  type HookJob,
} from "../api";

type Phase = "form" | "running" | "done" | "error";

interface Props {
  onClose: () => void;
}

const RUNNING_LABEL: Record<string, string> = {
  upload: "Song wird hochgeladen…",
  pending: "In der Warteschlange…",
  separating: "Vocals werden vom Beat getrennt (KI)…",
  analyzing: "Song-Struktur wird analysiert…",
};

function formatTime(sec: number): string {
  const m = Math.floor(sec / 60);
  const s = Math.round(sec % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

export default function HookAnalyzer({ onClose }: Props) {
  const [song, setSong] = useState<File | null>(null);
  const [phase, setPhase] = useState<Phase>("form");
  const [statusLabel, setStatusLabel] = useState("upload");
  const [job, setJob] = useState<HookJob | null>(null);
  const [errorMsg, setErrorMsg] = useState("");

  async function handleSubmit() {
    if (!song) return;
    setPhase("running");
    setStatusLabel("upload");
    try {
      const jobId = await analyzeHook(song);
      const finished = await waitForHook(jobId, (j) => setStatusLabel(j.status));
      if (finished.status === "error") {
        setErrorMsg(finished.error ?? "Unbekannter Fehler bei der Analyse.");
        setPhase("error");
      } else {
        setJob(finished);
        setPhase("done");
      }
    } catch (e) {
      setErrorMsg(e instanceof Error ? e.message : String(e));
      setPhase("error");
    }
  }

  const candidates: HookCandidate[] = job?.result
    ? [job.result.best, ...job.result.alternatives]
    : [];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
      <div className="w-full max-w-lg bg-ink-850 border border-ink-700 rounded-2xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-ink-700">
          <span className="flex items-center gap-2.5 font-semibold">
            <Zap size={20} className="text-brand-400" />
            Viral Hook Detector
          </span>
          <button onClick={onClose} className="text-muted hover:text-white">
            <X size={20} />
          </button>
        </div>

        <div className="p-6">
          {phase === "form" && (
            <div className="space-y-4">
              <p className="text-sm text-muted leading-relaxed">
                Lade deinen fertigen Song hoch. Die KI findet die Stelle mit dem
                höchsten Hook-Potenzial — perfekt, um zu wissen, welchen Teil du
                für dein Reel performst.
              </p>
              <label className="block cursor-pointer">
                <span className="text-sm text-muted">Songdatei (mp3/wav)</span>
                <div className="mt-1.5 flex items-center gap-3 border border-dashed border-ink-700 hover:border-brand-500/60 rounded-xl px-4 py-3 transition-colors">
                  <Music2 size={18} className="text-brand-400" />
                  <span className="text-sm flex-1 min-w-0 truncate">
                    {song ? song.name : "Datei auswählen…"}
                  </span>
                </div>
                <input
                  type="file"
                  accept="audio/*,video/*"
                  className="hidden"
                  onChange={(e) => e.target.files?.[0] && setSong(e.target.files[0])}
                />
              </label>
              <button
                disabled={!song}
                onClick={handleSubmit}
                className="w-full bg-brand-500 hover:bg-brand-600 disabled:opacity-40 disabled:cursor-not-allowed text-ink-950 font-semibold py-3 rounded-xl transition-colors"
              >
                Song analysieren
              </button>
            </div>
          )}

          {phase === "running" && (
            <div className="flex flex-col items-center py-8 text-center">
              <Loader2 size={40} className="text-brand-400 animate-spin" />
              <p className="mt-4 font-medium">
                {RUNNING_LABEL[statusLabel] ?? "Wird verarbeitet…"}
              </p>
              <p className="text-sm text-muted mt-1">
                Die Vocal-Trennung kann einige Minuten dauern (einmalig pro Song).
              </p>
            </div>
          )}

          {phase === "done" && job?.result && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="font-medium text-brand-400">
                  {candidates.length} Hook-Stelle{candidates.length !== 1 ? "n" : ""} gefunden
                </span>
                <span
                  className={`flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-md ${
                    job.result.used_vocals
                      ? "bg-brand-500/15 text-brand-400"
                      : "bg-ink-700 text-muted"
                  }`}
                  title={
                    job.result.used_vocals
                      ? "Vocals wurden separat analysiert (Demucs)"
                      : "Vocal-Analyse nicht verfügbar — bewertet über den Gesamtmix"
                  }
                >
                  <Mic2 size={13} />
                  {job.result.used_vocals ? "Mit Vocal-Analyse" : "Ohne Vocal-Analyse"}
                </span>
              </div>

              <div className="space-y-2">
                {candidates.map((c, i) => (
                  <div
                    key={i}
                    className={`rounded-xl border px-4 py-3 ${
                      i === 0
                        ? "border-brand-500/60 bg-brand-500/8"
                        : "border-ink-700 bg-ink-800"
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <span
                        className={`text-lg font-bold w-14 shrink-0 ${
                          i === 0 ? "text-brand-400" : "text-white"
                        }`}
                      >
                        {Math.round(c.viral_score)}
                        <span className="text-xs font-normal text-muted">/100</span>
                      </span>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium">
                          {i === 0 ? "Top-Hook" : `Alternative ${i}`}
                          <span className="text-muted font-normal">
                            {" "}· {formatTime(c.start_sec)} – {formatTime(c.end_sec)}
                          </span>
                        </p>
                        <p className="text-xs text-muted">
                          Wiederholung {(c.repetition_score * 100).toFixed(0)}% ·
                          Energie {c.energy_score.toFixed(2)}x
                          {c.vocal_score !== null && ` · Vocals ${c.vocal_score.toFixed(2)}x`}
                        </p>
                      </div>
                    </div>
                    <audio
                      controls
                      preload="none"
                      src={hookPreviewUrl(job.job_id, i)}
                      className="w-full mt-2 h-9"
                    />
                  </div>
                ))}
              </div>

              <p className="text-xs text-muted leading-relaxed">
                Tipp: Film deine Performance auf einer dieser Stellen — dann passt
                der Hook später exakt in dein Reel.
              </p>
            </div>
          )}

          {phase === "error" && (
            <div className="space-y-4">
              <div className="flex items-center gap-2 text-red-400">
                <AlertCircle size={20} />
                <span className="font-medium">Analyse fehlgeschlagen</span>
              </div>
              <pre className="text-xs text-muted bg-ink-900 rounded-lg p-3 whitespace-pre-wrap break-words max-h-40 overflow-auto">
                {errorMsg}
              </pre>
              <button
                onClick={() => setPhase("form")}
                className="w-full bg-ink-800 hover:bg-ink-700 text-white font-medium py-3 rounded-xl transition-colors"
              >
                Nochmal versuchen
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
