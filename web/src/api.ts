// Typisierter Client fuer das HOOKCUT-FastAPI-Backend (backend/main.py).
// Alle Aufrufe gehen an /api/... und werden im Dev-Server (vite.config.ts)
// auf das Backend (127.0.0.1:8000) weitergeleitet.

const BASE = "/api";

export type TakeStatus =
  | "pending"
  | "processing"
  | "effects"
  | "subtitles"
  | "done"
  | "error";

export interface Take {
  id: string;
  project_id: string;
  video_path: string;
  status: TakeStatus;
  offset_ms: number | null;
  confidence: number | null;
  original_audio_mode: string;
  output_path: string | null;
  error: string | null;
  created_at: string;
}

// Uebersetzt technische Netzwerkfehler in Meldungen, mit denen auch
// Nicht-Techniker etwas anfangen koennen (Zielgruppe: Musiker, keine Devs).
const HINT_RESTART =
  "Bitte beide Server-Fenster schliessen und start-hookcut.bat neu starten, " +
  "dann die Seite neu laden.";

async function requestOrExplain(input: string, init?: RequestInit): Promise<Response> {
  let res: Response;
  try {
    res = await fetch(input, init);
  } catch {
    // "Failed to fetch": nicht mal der Frontend-Server (Port 5173) war
    // erreichbar - HOOKCUT laeuft nicht (mehr) oder wurde neu gestartet.
    throw new Error(
      "Keine Verbindung zu HOOKCUT. Laufen die beiden Server-Fenster noch? " +
        HINT_RESTART,
    );
  }
  if (res.status === 502 || res.status === 504) {
    // Vite-Proxy erreicht das Backend (Port 8000) nicht.
    throw new Error(
      "Das Backend (Fenster \"HOOKCUT Backend\") ist nicht erreichbar. " +
        HINT_RESTART,
    );
  }
  if (res.status === 404) {
    // Haeufigster Grund: Backend laeuft noch mit altem Code-Stand
    // (nach git pull ist ein Neustart noetig, es gibt kein Auto-Reload).
    throw new Error(
      "Das Backend kennt diese Funktion noch nicht - vermutlich laeuft es " +
        "mit einem alten Stand. " + HINT_RESTART,
    );
  }
  return res;
}

async function jsonOrThrow<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

/** Projekt inkl. aller Takes, wie GET /projects es liefert. */
export interface ProjectSummary {
  id: string;
  name: string;
  song_path: string;
  created_at: string;
  takes: Take[];
}

export async function listProjects(): Promise<ProjectSummary[]> {
  const res = await requestOrExplain(`${BASE}/projects`);
  return jsonOrThrow<ProjectSummary[]>(res);
}

export async function createProject(name: string, song: File): Promise<string> {
  const form = new FormData();
  form.append("name", name);
  form.append("song", song);
  const res = await requestOrExplain(`${BASE}/projects`, { method: "POST", body: form });
  const data = await jsonOrThrow<{ project_id: string }>(res);
  return data.project_id;
}

export async function createTake(
  projectId: string,
  video: File,
  originalAudioMode: "mute" | "background" = "mute",
): Promise<string> {
  const form = new FormData();
  form.append("video", video);
  form.append("original_audio_mode", originalAudioMode);
  const res = await requestOrExplain(`${BASE}/projects/${projectId}/takes`, {
    method: "POST",
    body: form,
  });
  const data = await jsonOrThrow<{ take_id: string }>(res);
  return data.take_id;
}

export interface EditPreset {
  id: string;
  label: string;
  description: string;
}

export async function listPresets(): Promise<EditPreset[]> {
  const res = await requestOrExplain(`${BASE}/presets`);
  return jsonOrThrow<EditPreset[]>(res);
}

export interface SyncOptions {
  preset?: string;
  subtitles?: boolean;
  language?: "de" | "en";
}

export async function startSync(
  projectId: string,
  takeId: string,
  { preset = "clean", subtitles = false, language = "de" }: SyncOptions = {},
): Promise<void> {
  const form = new FormData();
  form.append("preset", preset);
  form.append("subtitles", String(subtitles));
  form.append("language", language);
  const res = await requestOrExplain(
    `${BASE}/projects/${projectId}/takes/${takeId}/sync`,
    { method: "POST", body: form },
  );
  await jsonOrThrow(res);
}

export async function getTake(projectId: string, takeId: string): Promise<Take> {
  const res = await requestOrExplain(`${BASE}/projects/${projectId}/takes/${takeId}`);
  return jsonOrThrow<Take>(res);
}

export function downloadUrl(projectId: string, takeId: string): string {
  return `${BASE}/projects/${projectId}/takes/${takeId}/download`;
}

// ---------------------------------------------------------------------------
// Viral Hook Detector

export type HookStatus = "pending" | "separating" | "analyzing" | "done" | "error";

export interface HookCandidate {
  start_sec: number;
  end_sec: number;
  repetition_score: number;
  energy_score: number;
  vocal_score: number | null;
  viral_score: number;
}

export interface HookJob {
  job_id: string;
  status: HookStatus;
  error: string | null;
  result: {
    best: HookCandidate;
    alternatives: HookCandidate[];
    used_vocals: boolean;
  } | null;
}

/** Kurzform einer Hook-Analyse, wie GET /hooks sie liefert (nur bester Kandidat). */
export interface HookJobSummary {
  job_id: string;
  status: HookStatus;
  created_at: string;
  best: HookCandidate | null;
}

export async function listRecentHooks(limit = 5): Promise<HookJobSummary[]> {
  const res = await requestOrExplain(`${BASE}/hooks?limit=${limit}`);
  return jsonOrThrow<HookJobSummary[]>(res);
}

export async function analyzeHook(song: File): Promise<string> {
  const form = new FormData();
  form.append("song", song);
  const res = await requestOrExplain(`${BASE}/hooks/analyze`, { method: "POST", body: form });
  const data = await jsonOrThrow<{ job_id: string }>(res);
  return data.job_id;
}

export async function getHookJob(jobId: string): Promise<HookJob> {
  const res = await requestOrExplain(`${BASE}/hooks/${jobId}`);
  return jsonOrThrow<HookJob>(res);
}

export function hookPreviewUrl(jobId: string, index: number): string {
  return `${BASE}/hooks/${jobId}/preview/${index}`;
}

/** Pollt den Analyse-Status bis 'done' oder 'error' (oder Timeout). */
export async function waitForHook(
  jobId: string,
  onUpdate?: (job: HookJob) => void,
  { intervalMs = 2000, timeoutMs = 30 * 60 * 1000 } = {},
): Promise<HookJob> {
  const start = Date.now();
  for (;;) {
    const job = await getHookJob(jobId);
    onUpdate?.(job);
    if (job.status === "done" || job.status === "error") return job;
    if (Date.now() - start > timeoutMs) {
      throw new Error("Zeitüberschreitung bei der Hook-Analyse.");
    }
    await new Promise((r) => setTimeout(r, intervalMs));
  }
}

/** Pollt den Take-Status bis 'done' oder 'error' (oder Timeout). */
export async function waitForSync(
  projectId: string,
  takeId: string,
  onUpdate?: (take: Take) => void,
  { intervalMs = 2000, timeoutMs = 15 * 60 * 1000 } = {},
): Promise<Take> {
  const start = Date.now();
  for (;;) {
    const take = await getTake(projectId, takeId);
    onUpdate?.(take);
    if (take.status === "done" || take.status === "error") return take;
    if (Date.now() - start > timeoutMs) {
      throw new Error("Zeitüberschreitung beim Synchronisieren.");
    }
    await new Promise((r) => setTimeout(r, intervalMs));
  }
}

// ---------------------------------------------------------------------------
// All-in-One-Assistent (Reel erstellen): Sync -> Hook? -> Style-Render

export interface Style {
  key: string;
  name: string;
  description: string;
}

export type EditStatus =
  | "pending" | "syncing" | "synced" | "hooking" | "hooked"
  | "transcribing" | "rendering" | "done" | "error";

export interface EditJob {
  job_id: string;
  status: EditStatus;
  error: string | null;
  with_subtitles: boolean;
  style: string | null;
  offset_ms: number | null;
  confidence: number | null;
  hook: { start_sec: number; end_sec: number } | null;
  has_output: boolean;
}

export async function getStyles(): Promise<Style[]> {
  const res = await requestOrExplain(`${BASE}/styles`);
  const data = await jsonOrThrow<{ styles: Style[] }>(res);
  return data.styles;
}

export async function editAnalyze(
  video: File,
  song: File,
  withSubtitles: boolean,
  lyrics = "",
): Promise<string> {
  const form = new FormData();
  form.append("video", video);
  form.append("song", song);
  form.append("with_subtitles", withSubtitles ? "true" : "false");
  form.append("lyrics", lyrics);
  const res = await requestOrExplain(`${BASE}/edit/analyze`, { method: "POST", body: form });
  const data = await jsonOrThrow<{ job_id: string }>(res);
  return data.job_id;
}

export async function editHook(jobId: string): Promise<void> {
  const res = await requestOrExplain(`${BASE}/edit/${jobId}/hook`, { method: "POST" });
  await jsonOrThrow(res);
}

export async function editRender(
  jobId: string,
  style: string,
  useHook: boolean,
  beatEffects = false,
): Promise<void> {
  const form = new FormData();
  form.append("style", style);
  form.append("use_hook", useHook ? "true" : "false");
  form.append("beat_effects", beatEffects ? "true" : "false");
  const res = await requestOrExplain(`${BASE}/edit/${jobId}/render`, { method: "POST", body: form });
  await jsonOrThrow(res);
}

export async function getEditJob(jobId: string): Promise<EditJob> {
  const res = await requestOrExplain(`${BASE}/edit/${jobId}`);
  return jsonOrThrow<EditJob>(res);
}

export function editDownloadUrl(jobId: string): string {
  return `${BASE}/edit/${jobId}/download`;
}

/** Pollt, bis der Job einen der Zielzustaende erreicht (oder Fehler/Timeout). */
export async function waitForEdit(
  jobId: string,
  until: EditStatus[],
  onUpdate?: (job: EditJob) => void,
  { intervalMs = 2000, timeoutMs = 30 * 60 * 1000 } = {},
): Promise<EditJob> {
  const start = Date.now();
  for (;;) {
    const job = await getEditJob(jobId);
    onUpdate?.(job);
    if (job.status === "error" || until.includes(job.status)) return job;
    if (Date.now() - start > timeoutMs) throw new Error("Zeitüberschreitung.");
    await new Promise((r) => setTimeout(r, intervalMs));
  }
}
