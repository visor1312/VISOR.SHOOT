import { Sparkles } from "lucide-react";

/** Ehrlicher Platzhalter fuer noch nicht gebaute Bereiche (statt toter Links). */
export default function ComingSoonPage({ title }: { title: string }) {
  return (
    <main className="flex-1 min-w-0 px-8 py-7">
      <h1 className="text-3xl font-bold tracking-tight">{title}</h1>
      <div className="mt-6 bg-ink-850/50 border border-ink-700 rounded-2xl p-12 flex flex-col items-center justify-center text-center">
        <div className="w-14 h-14 rounded-2xl bg-ink-800/60 flex items-center justify-center">
          <Sparkles size={28} className="text-ink-600" />
        </div>
        <h2 className="text-lg font-medium text-muted mt-5">Feature coming soon</h2>
        <p className="text-sm text-ink-600 mt-1 max-w-sm">
          Dieser Bereich ist in Arbeit. Wir bauen selfsign Schritt für Schritt zur
          kompletten Plattform aus.
        </p>
        <span className="mt-5 text-xs px-3 py-1.5 rounded-lg bg-ink-800 text-ink-600">
          Demnächst
        </span>
      </div>
    </main>
  );
}
