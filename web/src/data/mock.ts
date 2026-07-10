// Platzhalter-Daten fuer die Dashboard-Ansicht. Werden spaeter durch echte
// Aufrufe an das FastAPI-Backend (backend/main.py) ersetzt.

export type ProjectStatus = "done" | "processing" | "draft";

export interface RecentProject {
  id: number;
  title: string;
  date: string;
  status: ProjectStatus;
  duration: string;
}

export interface HookSuggestion {
  timestamp: string;
  score: number;
  line: string;
}

export const stats = [
  { label: "Produzierte Reels", value: "24", delta: "+3 diese Woche", icon: "music" as const },
  { label: "Virale Hooks gefunden", value: "17", delta: "+1 diese Woche", icon: "video" as const },
  { label: "Streams", value: "84K", delta: "+12% diesen Monat", icon: "headphones" as const },
  { label: "Hooks generiert", value: "61", delta: "+8 heute", icon: "zap" as const },
];

export const recentProjects: RecentProject[] = [
  { id: 1, title: "No Cap", date: "14. Jun", status: "done", duration: "2:34" },
  { id: 2, title: "Lowkey Grind", date: "11. Jun", status: "done", duration: "3:01" },
  { id: 3, title: "Ice Cold", date: "09. Jun", status: "processing", duration: "2:47" },
  { id: 4, title: "Real Talk", date: "05. Jun", status: "done", duration: "2:18" },
  { id: 5, title: "Midnight Run", date: "02. Jun", status: "draft", duration: "3:22" },
];

export const hookSuggestions: HookSuggestion[] = [
  { timestamp: "1:23", score: 96, line: "Real recognize real, fake see through" },
  { timestamp: "2:45", score: 89, line: "Started from the bottom, now we here" },
  { timestamp: "3:12", score: 84, line: "No cap, this is facts" },
];

export const statusMeta: Record<ProjectStatus, { label: string; className: string }> = {
  done: { label: "Fertig", className: "bg-brand-500/15 text-brand-400" },
  processing: { label: "Processing", className: "bg-amber-500/15 text-amber-400" },
  draft: { label: "Draft", className: "bg-ink-700 text-muted" },
};
