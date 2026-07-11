import { useEffect, useState } from "react";
import {
  X,
  UploadCloud,
  Music2,
  Video,
  Loader2,
  CheckCircle2,
  AlertCircle,
  Captions,
} from "lucide-react";
import {
  createProject,
  createTake,
  startSync,
  waitForSync,
  downloadUrl,
  listPresets,
  type Take,
  type EditPreset,
} from "../api";

type Phase = "form" | "running" | "done" | "error";

interface Props {
  onClose: () => void;
}

const RUNNING_LABEL: Record<string, string> = {
  upload: "Dateien werden hochgeladen…",
  pending: "In der Warteschlange…",
  processing: "Ton wird synchronisiert & Video gerendert…",
  effects: "Preset wird angewendet (Effekte & Grading)…",
  subtitles: "Untertitel werden erkannt & eingebrannt…",
};

const RUNNING_HINT: Record<string, string> = {
  processing: "Das kann bei einem 20–30-Sek.-Clip etwas dauern.",
  effects: "Beat-Effekte werden auf deinen Song getimt.",
  subtitles:
    "Die Spracherkennung läuft lokal — beim allerersten Mal lädt sie ihr Modell herunter (~460 MB).",
};

export default function UploadModal({ onClose }: Props) {
  const [song, setSong] = useState<File | null>(null);
  const [video, setVideo] = useState<File | null>(null);
  const [audioMode, setAudioMode] = useState<"mute" | "background">("mute");
  const [presets, setPresets] = useState<EditPreset[]>([]);
  const [preset, setPreset] = useState("clean");
  const [subtitles, setSubtitles] = useState(true);
  const [language, setLanguage] = useState<"de" | "en">("de");
  const [phase, setPhase] = useState<Phase>("form");
  const [statusLabel, setStatusLabel] = useState("upload");
  const [result, setResult] = useState<{ take: Take; projectId: string } | null>(null);
  const [errorMsg, setErrorMsg] = useState("");

  useEffect(() => {
    listPresets()
      .then(setPresets)
      .catch(() => {
        // Preset-Liste nicht ladbar (altes Backend?) - Upload funktioniert
        // trotzdem, dann eben ohne Auswahl mit Standard-Preset.
        setPresets([]);
      });
  }, []);

  const canSubmit = song && video && phase === "form";

  async function handleSubmit() {
    if (!song || !video) return;
    setPhase("running");
    setStatusLabel("upload");
    try {
      const name = song.name.replace(/\.[^.]+$/, "") || "Projekt";
      const projectId = await createProject(name, song);
      const takeId = await createTake(projectId, video, audioMode);
      await startSync(projectId, takeId, { preset, subtitles, language });
      const take = await waitForSync(projectId, takeId, (t) =>
        setStatusLabel(t.status),
      );
      if (take.status === "error") {
        setErrorMsg(take.error ?? "Unbekannter Fehler beim Synchronisieren.");
        setPhase("error");
      } else {
        setResult({ take, projectId });
        setPhase("done");
      }
    } catch (e) {
      setErrorMsg(e instanceof Error ? e.message : String(e));
      setPhase("error");
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
      <div className="w-full max-w-2xl bg-ink-850 border border-ink-700 rounded-2xl overflow-hidden max-h-[92vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-ink-700 shrink-0">
          <span className="flex items-center gap-2.5 font-semibold">
            <UploadCloud size={20} className="text-brand-400" />
            Video + Song Upload
          </span>
          <button onClick={onClose} className="text-muted hover:text-white">
            <X size={20} />
          </button>
        </div>

        <div className="p-6 overflow-y-auto">
          {phase === "form" && (
            <div className="space-y-5">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <FilePicker
                  label="Songdatei (mp3/wav)"
                  icon={<Music2 size={18} className="text-brand-400" />}
                  accept="audio/*"
                  file={song}
                  onPick={setSong}
                />
                <FilePicker
                  label="Video-Take (mp4/mov)"
                  icon={<Video size={18} className="text-brand-400" />}
                  accept="video/*"
                  file={video}
                  onPick={setVideo}
                />
              </div>

              {/* Preset-Auswahl */}
              {presets.length > 0 && (
                <div>
                  <p className="text-sm text-muted mb-2">Look & Schnitt-Preset</p>
                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                    {presets.map((p) => (
                      <button
                        key={p.id}
                        onClick={() => setPreset(p.id)}
                        title={p.description}
                        className={`text-left rounded-xl border px-3 py-2.5 transition-colors ${
                          preset === p.id
                            ? "border-brand-500 bg-brand-500/12"
                            : "border-ink-700 hover:border-ink-600"
                        }`}
                      >
                        <span
                          className={`block text-sm font-semibold ${
                            preset === p.id ? "text-brand-400" : "text-white"
                          }`}
                        >
                          {p.label}
                        </span>
                        <span className="block text-[11px] text-muted leading-snug mt-0.5 line-clamp-2">
                          {p.description}
                        </span>
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* Untertitel */}
              <div className="flex items-center gap-3 bg-ink-800/60 border border-ink-700 rounded-xl px-4 py-3">
                <Captions size={18} className="text-brand-400 shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium">Automatische Untertitel</p>
                  <p className="text-[11px] text-muted">
                    Karaoke-Stil: das aktuelle Wort wird farblich hervorgehoben.
                  </p>
                </div>
                {subtitles && (
                  <div className="flex gap-1">
                    {(["de", "en"] as const).map((l) => (
                      <button
                        key={l}
                        onClick={() => setLanguage(l)}
                        className={`text-xs px-2 py-1 rounded-md border transition-colors ${
                          language === l
                            ? "border-brand-500 bg-brand-500/12 text-brand-400"
                            : "border-ink-700 text-muted hover:text-white"
                        }`}
                      >
                        {l.toUpperCase()}
                      </button>
                    ))}
                  </div>
                )}
                <button
                  onClick={() => setSubtitles(!subtitles)}
                  aria-pressed={subtitles}
                  className={`w-11 h-6 rounded-full relative transition-colors shrink-0 ${
                    subtitles ? "bg-brand-500" : "bg-ink-700"
                  }`}
                >
                  <span
                    className={`absolute top-0.5 w-5 h-5 rounded-full bg-white transition-all ${
                      subtitles ? "left-[22px]" : "left-0.5"
                    }`}
                  />
                </button>
              </div>

              {/* Original-Ton */}
              <div>
                <p className="text-sm text-muted mb-2">Original-Videoton</p>
                <div className="flex gap-2">
                  {(["mute", "background"] as const).map((m) => (
                    <button
                      key={m}
                      onClick={() => setAudioMode(m)}
                      className={`flex-1 text-sm py-2 rounded-lg border transition-colors ${
                        audioMode === m
                          ? "border-brand-500 bg-brand-500/12 text-brand-400"
                          : "border-ink-700 text-muted hover:text-white"
                      }`}
                    >
                      {m === "mute" ? "Stumm" : "Leise im Hintergrund"}
                    </button>
                  ))}
                </div>
              </div>

              <button
                disabled={!canSubmit}
                onClick={handleSubmit}
                className="w-full bg-brand-500 hover:bg-brand-600 disabled:opacity-40 disabled:cursor-not-allowed text-ink-950 font-semibold py-3 rounded-xl transition-colors"
              >
                Video erstellen
              </button>
            </div>
          )}

          {phase === "running" && (
            <div className="flex flex-col items-center py-8 text-center">
              <Loader2 size={40} className="text-brand-400 animate-spin" />
              <p className="mt-4 font-medium">
                {RUNNING_LABEL[statusLabel] ?? "Wird verarbeitet…"}
              </p>
              <p className="text-sm text-muted mt-1 max-w-sm">
                {RUNNING_HINT[statusLabel] ??
                  "Das kann bei einem 20–30-Sek.-Clip etwas dauern."}
              </p>
            </div>
          )}

          {phase === "done" && result && (
            <div className="space-y-4">
              <div className="flex items-center gap-2 text-brand-400">
                <CheckCircle2 size={20} />
                <span className="font-medium">Fertig!</span>
              </div>
              <video
                src={downloadUrl(result.projectId, result.take.id)}
                controls
                className="w-full rounded-xl bg-black max-h-[50vh]"
              />
              <div className="flex gap-4 text-sm">
                <span className="text-muted">
                  Zeitversatz:{" "}
                  <span className="text-white font-medium">
                    {result.take.offset_ms?.toFixed(0)} ms
                  </span>
                </span>
                <span className="text-muted">
                  Konfidenz:{" "}
                  <span className="text-white font-medium">
                    {result.take.confidence?.toFixed(2)}
                  </span>
                </span>
              </div>
              <a
                href={downloadUrl(result.projectId, result.take.id)}
                download
                className="block text-center w-full bg-brand-500 hover:bg-brand-600 text-ink-950 font-semibold py-3 rounded-xl transition-colors"
              >
                Video herunterladen
              </a>
            </div>
          )}

          {phase === "error" && (
            <div className="space-y-4">
              <div className="flex items-center gap-2 text-red-400">
                <AlertCircle size={20} />
                <span className="font-medium">Fehlgeschlagen</span>
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

function FilePicker({
  label,
  icon,
  accept,
  file,
  onPick,
}: {
  label: string;
  icon: React.ReactNode;
  accept: string;
  file: File | null;
  onPick: (f: File) => void;
}) {
  return (
    <label className="block cursor-pointer">
      <span className="text-sm text-muted">{label}</span>
      <div className="mt-1.5 flex items-center gap-3 border border-dashed border-ink-700 hover:border-brand-500/60 rounded-xl px-4 py-3 transition-colors">
        {icon}
        <span className="text-sm flex-1 min-w-0 truncate">
          {file ? file.name : "Datei auswählen…"}
        </span>
      </div>
      <input
        type="file"
        accept={accept}
        className="hidden"
        onChange={(e) => e.target.files?.[0] && onPick(e.target.files[0])}
      />
    </label>
  );
}
