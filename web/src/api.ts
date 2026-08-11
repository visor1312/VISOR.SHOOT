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

/** Sitzung abgelaufen/nicht angemeldet - App zeigt wieder die Login-Maske. */
export class UnauthorizedError extends Error {}

// Globaler 401-Handler: App.tsx registriert hier das Umschalten zur
// Login-Maske, damit jede beliebige API-Funktion bei abgelaufener
// Sitzung automatisch dorthin zurueckfuehrt.
let onUnauthorized: (() => void) | null = null;
export function setUnauthorizedHandler(fn: (() => void) | null) {
  onUnauthorized = fn;
}

async function requestOrExplain(
  input: string,
  init?: RequestInit,
  // authRequest: fuer die /auth-Endpunkte selbst ist ein 401 eine normale
  // Antwort (z.B. "Passwort falsch") und darf NICHT als abgelaufene
  // Sitzung behandelt werden.
  { authRequest = false } = {},
): Promise<Response> {
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
  // WICHTIG: vor der 404-Heuristik pruefen - ein 401 ist "nicht angemeldet",
  // kein "Backend zu alt".
  if (res.status === 401 && !authRequest) {
    onUnauthorized?.();
    throw new UnauthorizedError("Deine Sitzung ist abgelaufen. Bitte neu anmelden.");
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

// ---------------------------------------------------------------------------
// Benutzer-System (Login/Registrierung/Sitzung)

export interface User {
  id: string;
  email: string;
  display_name: string;
  is_admin: boolean;
}

function jsonPost(body: unknown): RequestInit {
  return {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  };
}

/** Eingeloggter User oder null (nicht angemeldet) - feuert NIE den 401-Handler. */
export async function getMe(): Promise<User | null> {
  const res = await requestOrExplain(`${BASE}/auth/me`, undefined, { authRequest: true });
  if (res.status === 401) return null;
  return jsonOrThrow<User>(res);
}

/** Verlangt dieser Server einen Einladungscode? (Lokales Werkzeug: ja,
 *  offene Plattform: nein.) Wird vor dem Anmelden abgefragt. */
export async function getAuthConfig(): Promise<{ invite_required: boolean }> {
  const res = await requestOrExplain(`${BASE}/auth/config`, undefined, { authRequest: true });
  return jsonOrThrow<{ invite_required: boolean }>(res);
}

export async function login(email: string, password: string): Promise<User> {
  const res = await requestOrExplain(
    `${BASE}/auth/login`, jsonPost({ email, password }), { authRequest: true });
  return jsonOrThrow<User>(res);
}

export async function register(
  inviteCode: string,
  email: string,
  displayName: string,
  password: string,
): Promise<User> {
  const res = await requestOrExplain(
    `${BASE}/auth/register`,
    jsonPost({ invite_code: inviteCode, email, display_name: displayName, password }),
    { authRequest: true },
  );
  return jsonOrThrow<User>(res);
}

export async function logout(): Promise<void> {
  const res = await requestOrExplain(`${BASE}/auth/logout`, { method: "POST" },
    { authRequest: true });
  await jsonOrThrow(res);
}

/** Anzeigenamen aendern -> aktualisierter User. */
export async function updateDisplayName(displayName: string): Promise<User> {
  const res = await requestOrExplain(`${BASE}/auth/me`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ display_name: displayName }),
  });
  return jsonOrThrow<User>(res);
}

/** Passwort aendern (bleibt in diesem Browser eingeloggt). */
export async function changePassword(currentPassword: string, newPassword: string): Promise<void> {
  const res = await requestOrExplain(
    `${BASE}/auth/change-password`,
    jsonPost({ current_password: currentPassword, new_password: newPassword }),
  );
  await jsonOrThrow(res);
}

// --- Admin (nur fuer Admin-Konten) ---------------------------------------

export interface InviteCode {
  code: string;
  created_at: string;
  used: boolean;
  used_by_email: string | null;
}

export interface AdminUser {
  id: string;
  email: string;
  display_name: string;
  is_admin: boolean;
  created_at: string;
}

export async function listInvites(): Promise<InviteCode[]> {
  const res = await requestOrExplain(`${BASE}/admin/invites`);
  return jsonOrThrow<InviteCode[]>(res);
}

export async function createInvite(): Promise<InviteCode> {
  const res = await requestOrExplain(`${BASE}/admin/invites`, { method: "POST" });
  return jsonOrThrow<InviteCode>(res);
}

export async function listUsers(): Promise<AdminUser[]> {
  const res = await requestOrExplain(`${BASE}/admin/users`);
  return jsonOrThrow<AdminUser[]>(res);
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

// ---------------------------------------------------------------------------
// All-in-One-Assistent (Reel erstellen): Sync -> Hook? -> Style-Render

export interface Style {
  key: string;
  name: string;
  description: string;
}

export interface Platform {
  key: string;
  name: string;
  description: string;
  width: number;
  height: number;
}

export interface EditOutput {
  platform: string;
  name: string;
  width: number;
  height: number;
  ready: boolean;
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
  outputs: EditOutput[] | null;
}

export async function getStyles(): Promise<Style[]> {
  const res = await requestOrExplain(`${BASE}/styles`);
  const data = await jsonOrThrow<{ styles: Style[] }>(res);
  return data.styles;
}

export async function getPlatforms(): Promise<Platform[]> {
  const res = await requestOrExplain(`${BASE}/platforms`);
  const data = await jsonOrThrow<{ platforms: Platform[] }>(res);
  return data.platforms;
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
  platforms: string[] = ["reel"],
): Promise<void> {
  const form = new FormData();
  form.append("style", style);
  form.append("use_hook", useHook ? "true" : "false");
  form.append("beat_effects", beatEffects ? "true" : "false");
  form.append("platforms", platforms.length ? platforms.join(",") : "reel");
  const res = await requestOrExplain(`${BASE}/edit/${jobId}/render`, { method: "POST", body: form });
  await jsonOrThrow(res);
}

export async function getEditJob(jobId: string): Promise<EditJob> {
  const res = await requestOrExplain(`${BASE}/edit/${jobId}`);
  return jsonOrThrow<EditJob>(res);
}

/** Kurzform eines Wizard-Reels, wie GET /edit sie liefert ("Meine Reels"). */
export interface EditJobSummary {
  job_id: string;
  status: EditStatus;
  error: string | null;
  style: string | null;
  created_at: string;
  has_output: boolean;
  outputs: EditOutput[] | null;
}

export async function listEditJobs(limit = 20): Promise<EditJobSummary[]> {
  const res = await requestOrExplain(`${BASE}/edit?limit=${limit}`);
  return jsonOrThrow<EditJobSummary[]>(res);
}

export function editDownloadUrl(jobId: string, platform?: string): string {
  return platform
    ? `${BASE}/edit/${jobId}/download?platform=${encodeURIComponent(platform)}`
    : `${BASE}/edit/${jobId}/download`;
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

// ---------------------------------------------------------------------------
// Wochen-Content / Content-Packs: ein Song -> viele fertige Posts

export type PackStatus =
  | "pending" | "analyzing" | "transcribing" | "rendering" | "done" | "error";

export interface PackItem {
  idx: number;
  hook_index: number;
  style: string;
  platform: string;
  status: PackStatus;
  error: string | null;
  ready: boolean;
}

export interface PackSummary {
  pack_id: string;
  status: PackStatus;
  error: string | null;
  with_subtitles: boolean;
  created_at: string;
  item_count: number;
  done_count: number;
}

export interface PackDetail extends PackSummary {
  items: PackItem[];
}

export async function createPack(
  video: File,
  song: File,
  opts: {
    styles: string[];
    hookCount: number;
    platforms: string[];
    beatEffects?: boolean;
    withSubtitles?: boolean;
    lyrics?: string;
  },
): Promise<{ pack_id: string; planned_items: number }> {
  const form = new FormData();
  form.append("video", video);
  form.append("song", song);
  form.append("styles", opts.styles.length ? opts.styles.join(",") : "clean");
  form.append("hook_count", String(opts.hookCount));
  form.append("platforms", opts.platforms.length ? opts.platforms.join(",") : "reel");
  form.append("beat_effects", opts.beatEffects ? "true" : "false");
  form.append("with_subtitles", opts.withSubtitles ? "true" : "false");
  form.append("lyrics", opts.lyrics ?? "");
  const res = await requestOrExplain(`${BASE}/packs`, { method: "POST", body: form });
  return jsonOrThrow<{ pack_id: string; planned_items: number }>(res);
}

export async function listPacks(limit = 50): Promise<PackSummary[]> {
  const res = await requestOrExplain(`${BASE}/packs?limit=${limit}`);
  return jsonOrThrow<PackSummary[]>(res);
}

export async function getPack(packId: string): Promise<PackDetail> {
  const res = await requestOrExplain(`${BASE}/packs/${packId}`);
  return jsonOrThrow<PackDetail>(res);
}

export function packItemDownloadUrl(packId: string, idx: number): string {
  return `${BASE}/packs/${packId}/items/${idx}/download`;
}

// ---------------------------------------------------------------------------
// Spotify Canvas: kurzer (3-8s) stummer 9:16-Loop

export type CanvasStatus = "pending" | "analyzing" | "rendering" | "done" | "error";

export interface CanvasJob {
  canvas_id: string;
  status: CanvasStatus;
  error: string | null;
  style: string | null;
  duration_sec: number;
  created_at: string;
  has_output: boolean;
}

export async function createCanvas(
  video: File,
  song: File,
  opts: { style: string; durationSec: number; useHook: boolean },
): Promise<{ canvas_id: string; duration_sec: number }> {
  const form = new FormData();
  form.append("video", video);
  form.append("song", song);
  form.append("style", opts.style);
  form.append("duration_sec", String(opts.durationSec));
  form.append("use_hook", opts.useHook ? "true" : "false");
  const res = await requestOrExplain(`${BASE}/canvas`, { method: "POST", body: form });
  return jsonOrThrow<{ canvas_id: string; duration_sec: number }>(res);
}

export async function listCanvas(limit = 50): Promise<CanvasJob[]> {
  const res = await requestOrExplain(`${BASE}/canvas?limit=${limit}`);
  return jsonOrThrow<CanvasJob[]>(res);
}

export async function getCanvas(canvasId: string): Promise<CanvasJob> {
  const res = await requestOrExplain(`${BASE}/canvas/${canvasId}`);
  return jsonOrThrow<CanvasJob>(res);
}

export function canvasDownloadUrl(canvasId: string): string {
  return `${BASE}/canvas/${canvasId}/download`;
}
