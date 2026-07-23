// Gemeinsamer Datei-Auswahlknopf (gestrichelter Rahmen mit Icon + Dateiname).
// Wird von allen Erstell-Assistenten (Reel/Pack/Canvas) geteilt.

export default function FilePick({ label, icon, accept, file, onPick }: {
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
        <span className="text-sm flex-1 min-w-0 truncate">{file ? file.name : "Datei auswählen…"}</span>
      </div>
      <input type="file" accept={accept} className="hidden"
        onChange={(e) => e.target.files?.[0] && onPick(e.target.files[0])} />
    </label>
  );
}
