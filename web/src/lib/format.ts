// Kleine gemeinsame Anzeige-Helfer. Fruher lagen formatDate/formatTime und die
// Reel-Status-Ampel mehrfach (leicht abweichend) in einzelnen Seiten/Komponenten
// verstreut - hier zentral, damit sie nicht auseinanderdriften.

import type { EditJobSummary } from "../api";

/** ISO-Datum deutsch, z.B. "3. Aug" bzw. mit Jahr "3. Aug 2026". */
export function formatDate(iso: string, opts: { year?: boolean } = {}): string {
  return new Date(iso).toLocaleDateString("de-DE", {
    day: "numeric",
    month: "short",
    ...(opts.year ? { year: "numeric" as const } : {}),
  });
}

/** Sekunden als m:ss, z.B. 75 -> "1:15". */
export function formatTime(sec: number): string {
  const m = Math.floor(sec / 60);
  const s = Math.round(sec % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

/** Ampel (Label + Tailwind-Klassen) fuer den Status eines Wizard-Reels. */
export function editJobStatusMeta(
  status: EditJobSummary["status"],
): { label: string; className: string } {
  if (status === "done") return { label: "Fertig", className: "bg-brand-500/15 text-brand-400" };
  if (status === "error") return { label: "Fehler", className: "bg-red-500/15 text-red-400" };
  return { label: "Läuft…", className: "bg-amber-500/15 text-amber-400" };
}

/** Aus den Takes eines Projekts abgeleiteter Sammelstatus. */
export type ProjectStatus = "done" | "processing" | "draft" | "error";

/** Ampel fuer den Projektstatus - durchgehend deutsch (Dashboard + Projekte-Seite). */
export const projectStatusMeta: Record<ProjectStatus, { label: string; className: string }> = {
  done: { label: "Fertig", className: "bg-brand-500/15 text-brand-400" },
  processing: { label: "Läuft…", className: "bg-amber-500/15 text-amber-400" },
  draft: { label: "Entwurf", className: "bg-ink-700 text-muted" },
  error: { label: "Fehler", className: "bg-red-500/15 text-red-400" },
};
