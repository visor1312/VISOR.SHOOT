// Typisierter Client fuer das HOOKCUT-FastAPI-Backend (backend/main.py).
// Alle Aufrufe gehen an /api/... und werden im Dev-Server (vite.config.ts)
// auf das Backend (127.0.0.1:8000) weitergeleitet.

const BASE = "/api";

export type TakeStatus = "pending" | "processing" | "done" | "error";

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

export async function createProject(name: string, song: File): Promise<string> {
  const form = new FormData();
  form.append("name", name);
  form.append("song", song);
  const res = await fetch(`${BASE}/projects`, { method: "POST", body: form });
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
  const res = await fetch(`${BASE}/projects/${projectId}/takes`, {
    method: "POST",
    body: form,
  });
  const data = await jsonOrThrow<{ take_id: string }>(res);
  return data.take_id;
}

export async function startSync(projectId: string, takeId: string): Promise<void> {
  const res = await fetch(
    `${BASE}/projects/${projectId}/takes/${takeId}/sync`,
    { method: "POST" },
  );
  await jsonOrThrow(res);
}

export async function getTake(projectId: string, takeId: string): Promise<Take> {
  const res = await fetch(`${BASE}/projects/${projectId}/takes/${takeId}`);
  return jsonOrThrow<Take>(res);
}

export function downloadUrl(projectId: string, takeId: string): string {
  return `${BASE}/projects/${projectId}/takes/${takeId}/download`;
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
