import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  CalendarClock, Download, FolderOpen, Film, Loader2, Music2, Upload, Zap,
} from "lucide-react";
import {
  listErstellt, erstelltDownloadUrl,
  type ErstelltEintrag, type ErstelltArt,
} from "../api";
import { useApp } from "../components/app-context";
import { formatDate } from "../lib/format";

/** Das Dashboard: EINE Liste von allem, was du erstellt hast.
 *
 *  Vorher standen hier vier Zahlen-Kacheln, drei Spalten, eine Reel-Sektion
 *  und noch ein Dreier-Raster - viel Struktur fuer wenig Auskunft, und mit
 *  wenig Daten wirkte die Seite tot. Die Zahlen ("3 Projekte") haben nie
 *  jemandem etwas gesagt.
 *
 *  Was zaehlt, ist: was habe ich gemacht, ist es fertig, wo lade ich es
 *  runter. Genau das steht jetzt hier - ueber alle Werkzeuge hinweg, nach
 *  Datum sortiert, aus GET /erstellt.
 */
export default function DashboardPage() {
  const { user, openWizard, refreshKey } = useApp();
  const [eintraege, setEintraege] = useState<ErstelltEintrag[] | null>(null);
  const [fehler, setFehler] = useState("");

  useEffect(() => {
    let abgebrochen = false;
    setFehler("");
    listErstellt()
      .then((e) => !abgebrochen && setEintraege(e))
      .catch((ex) => !abgebrochen && setFehler(ex instanceof Error ? ex.message : String(ex)));
    return () => { abgebrochen = true; };
  }, [refreshKey]);

  return (
    <main className="flex-1 min-w-0 px-8 py-7 max-w-4xl">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Deine Sachen</h1>
          <p className="text-muted mt-1">
            Alles, was du bisher erstellt hast – neueste zuerst.
          </p>
        </div>
        <button onClick={openWizard}
          className="shrink-0 flex items-center gap-2 bg-brand-500 hover:bg-brand-600 text-ink-950 font-semibold px-4 py-2.5 rounded-xl transition-colors">
          <Upload size={17} />
          Reel erstellen
        </button>
      </div>

      {fehler && (
        <div className="mt-6 bg-red-500/10 border border-red-500/40 text-red-400 text-sm rounded-xl px-4 py-3">
          {fehler}
        </div>
      )}

      {eintraege === null && !fehler && (
        <div className="mt-8 flex items-center gap-2 text-muted text-sm">
          <Loader2 size={16} className="animate-spin" />
          Wird geladen …
        </div>
      )}

      {eintraege?.length === 0 && <Leer name={user.display_name} onWizard={openWizard} />}

      {eintraege && eintraege.length > 0 && (
        <div className="mt-6 space-y-2">
          {eintraege.map((e) => <Zeile key={`${e.art}-${e.id}`} eintrag={e} />)}
        </div>
      )}
    </main>
  );
}

const ART_ICON: Record<ErstelltArt, typeof Music2> = {
  reel: Music2,
  pack: CalendarClock,
  canvas: Film,
  hook: Zap,
  aufnahme: FolderOpen,
};

const STATUS: Record<ErstelltEintrag["status"], { label: string; klasse: string }> = {
  fertig: { label: "Fertig", klasse: "bg-brand-500/15 text-brand-400" },
  laeuft: { label: "Läuft…", klasse: "bg-amber-500/15 text-amber-400" },
  fehler: { label: "Fehler", klasse: "bg-red-500/15 text-red-400" },
  leer: { label: "Leer", klasse: "bg-ink-800 text-muted" },
};

function Zeile({ eintrag }: { eintrag: ErstelltEintrag }) {
  const Icon = ART_ICON[eintrag.art];
  const status = STATUS[eintrag.status];
  return (
    <div className="bg-ink-850 border border-ink-700 rounded-xl px-4 py-3.5 flex items-start gap-3.5">
      <div className="w-9 h-9 rounded-lg bg-ink-800 shrink-0 flex items-center justify-center">
        <Icon size={17} className="text-brand-400" />
      </div>

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <Link to={eintrag.seite}
            className="font-medium hover:text-brand-400 transition-colors truncate">
            {eintrag.titel}
          </Link>
          <span className={`text-[11px] px-1.5 py-0.5 rounded ${status.klasse}`}>
            {status.label}
          </span>
        </div>
        <p className="text-sm text-muted mt-0.5">
          {formatDate(eintrag.created_at, { year: true })}
          {eintrag.detail && <> · {eintrag.detail}</>}
        </p>
        {/* Die Fehlermeldung gehoert hierher und nicht in ein Protokoll -
            sonst steht da nur "Fehler" und niemand weiss, woran es lag. */}
        {eintrag.fehler && (
          <p className="text-sm text-red-400 mt-1.5">{eintrag.fehler}</p>
        )}
      </div>

      {eintrag.downloads.length > 0 && (
        <div className="flex flex-wrap gap-1.5 justify-end shrink-0 max-w-[45%]">
          {eintrag.downloads.map((d) => (
            <a key={d.url} href={erstelltDownloadUrl(d.url)} download
              className="flex items-center gap-1.5 text-xs bg-ink-800 hover:bg-ink-700 border border-ink-700 px-2.5 py-1.5 rounded-lg transition-colors">
              <Download size={13} />
              {d.label}
            </a>
          ))}
        </div>
      )}
    </div>
  );
}

function Leer({ name, onWizard }: { name: string; onWizard: () => void }) {
  return (
    <div className="mt-8 bg-ink-850 border border-ink-700 rounded-2xl p-8 text-center">
      <p className="font-medium">Noch nichts da, {name}.</p>
      <p className="text-sm text-muted mt-1.5 max-w-md mx-auto">
        Lade ein Video und deinen Song hoch – selfsign schneidet daraus ein
        fertiges Reel. Alles, was du erstellst, landet danach hier.
      </p>
      <button onClick={onWizard}
        className="mt-5 inline-flex items-center gap-2 bg-brand-500 hover:bg-brand-600 text-ink-950 font-semibold px-4 py-2.5 rounded-xl transition-colors">
        <Upload size={17} />
        Erstes Reel erstellen
      </button>
    </div>
  );
}
