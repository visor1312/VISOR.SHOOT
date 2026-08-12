import { useEffect, useState } from "react";
import { Flag, Loader2, X } from "lucide-react";
import { getReportReasons, meldeInhalt, type Meldegrund } from "../api";

/** Melden-Dialog fuer einen Beitrag oder Kommentar.
 *
 * Bewusst schlicht: Grund auswaehlen, optional etwas dazuschreiben, fertig.
 * Wer gerade etwas melden will, ist meist veraergert - da hilft kein
 * Formular mit acht Feldern.
 *
 * Nach dem Absenden wird bestaetigt, dass die Meldung angekommen ist. Das
 * ist nicht nur hoeflich, sondern Teil der Pflicht: wer meldet, soll wissen,
 * dass etwas passiert.
 */
export default function MeldenDialog({
  art,
  zielId,
  onClose,
}: {
  art: "post" | "comment";
  zielId: string;
  onClose: () => void;
}) {
  const [gruende, setGruende] = useState<Meldegrund[]>([]);
  const [grund, setGrund] = useState("");
  const [notiz, setNotiz] = useState("");
  const [laeuft, setLaeuft] = useState(false);
  const [fertig, setFertig] = useState(false);
  const [fehler, setFehler] = useState("");

  useEffect(() => {
    getReportReasons()
      .then((g) => {
        setGruende(g);
        setGrund((aktuell) => aktuell || g[0]?.key || "");
      })
      .catch((e) => setFehler(e instanceof Error ? e.message : String(e)));
  }, []);

  async function absenden(e: React.FormEvent) {
    e.preventDefault();
    if (!grund) return;
    setLaeuft(true);
    setFehler("");
    try {
      await meldeInhalt(art, zielId, grund, notiz.trim());
      setFertig(true);
    } catch (e) {
      setFehler(e instanceof Error ? e.message : String(e));
    } finally {
      setLaeuft(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4"
      onClick={onClose}>
      <div className="w-full max-w-md bg-ink-900 border border-ink-700 rounded-2xl p-6"
        onClick={(e) => e.stopPropagation()}>
        <div className="flex items-start justify-between gap-4">
          <h2 className="flex items-center gap-2 text-lg font-semibold">
            <Flag size={18} className="text-red-400" />
            {art === "post" ? "Beitrag melden" : "Kommentar melden"}
          </h2>
          <button onClick={onClose} className="text-muted hover:text-white" title="Schließen">
            <X size={18} />
          </button>
        </div>

        {fertig ? (
          <div className="mt-5 space-y-4">
            <p className="text-sm text-muted leading-relaxed">
              Danke – die Meldung ist angekommen. Wir sehen sie uns an und
              entfernen den Inhalt, wenn er gegen die Nutzungsbedingungen
              verstößt.
            </p>
            <button onClick={onClose}
              className="w-full bg-brand-500 hover:bg-brand-600 text-ink-950 font-semibold text-sm py-2.5 rounded-xl transition-colors">
              Schließen
            </button>
          </div>
        ) : (
          <form onSubmit={absenden} className="mt-5 space-y-4">
            <div className="space-y-2">
              {gruende.map((g) => (
                <label key={g.key}
                  className="flex items-start gap-2.5 text-sm cursor-pointer">
                  <input type="radio" name="grund" value={g.key}
                    checked={grund === g.key}
                    onChange={() => setGrund(g.key)}
                    className="mt-0.5 accent-brand-500" />
                  <span className="text-muted">{g.label}</span>
                </label>
              ))}
            </div>

            <label className="block">
              <span className="text-sm text-muted">Was ist passiert? (freiwillig)</span>
              <textarea value={notiz} onChange={(e) => setNotiz(e.target.value)}
                rows={3} maxLength={1000}
                placeholder="Je genauer, desto schneller können wir es prüfen."
                className="mt-1.5 w-full text-sm bg-ink-800 border border-ink-700 focus:border-brand-500 rounded-xl px-3 py-2.5 outline-none resize-none" />
            </label>

            {fehler && <p className="text-sm text-red-400">{fehler}</p>}

            <div className="flex gap-2">
              <button type="button" onClick={onClose}
                className="flex-1 text-sm px-4 py-2.5 rounded-xl bg-ink-800 hover:bg-ink-700 transition-colors">
                Abbrechen
              </button>
              <button type="submit" disabled={!grund || laeuft}
                className="flex-1 flex items-center justify-center gap-2 bg-red-500 hover:bg-red-600 disabled:opacity-40 text-white font-semibold text-sm px-4 py-2.5 rounded-xl transition-colors">
                {laeuft ? <Loader2 size={16} className="animate-spin" /> : <Flag size={16} />}
                Melden
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
