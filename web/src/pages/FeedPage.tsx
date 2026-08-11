import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Loader2, Plus, Music2, Users } from "lucide-react";
import {
  getDiscoverFeed, getFollowingFeed, getPostCategories,
  type Post, type PostCategory,
} from "../api";
import CreatePostWizard from "../components/CreatePostWizard";
import BeitragsKarte from "../components/BeitragsKarte";

type Reiter = "entdecken" | "folge-ich";

/** Der Feed: offene Projekte anderer Musiker.
 *
 * "Entdecken" ist bewusst die Startansicht - wer neu ist, folgt noch
 * niemandem und saehe unter "Folge ich" nur eine leere Seite.
 */
export default function FeedPage() {
  const [reiter, setReiter] = useState<Reiter>("entdecken");
  const [kategorien, setKategorien] = useState<PostCategory[]>([]);
  const [filter, setFilter] = useState<string[]>([]);
  const [beitraege, setBeitraege] = useState<Post[] | null>(null);
  const [fehler, setFehler] = useState("");
  const [dialogOffen, setDialogOffen] = useState(false);

  useEffect(() => {
    getPostCategories().then(setKategorien).catch(() => setKategorien([]));
  }, []);

  const laden = useCallback(() => {
    setBeitraege(null);
    setFehler("");
    const abfrage = { categories: filter };
    const holen = reiter === "entdecken" ? getDiscoverFeed : getFollowingFeed;
    return holen(abfrage)
      .then(setBeitraege)
      .catch((e) => setFehler(e instanceof Error ? e.message : String(e)));
  }, [reiter, filter]);

  useEffect(() => { laden(); }, [laden]);

  // Bezeichnungen kommen vom Server (/post-categories) - keine zweite Liste hier.
  const labels = Object.fromEntries(kategorien.map((k) => [k.key, k.name]));

  function filterUmschalten(key: string) {
    setFilter((v) => (v.includes(key) ? v.filter((k) => k !== key) : [...v, key]));
  }

  return (
    <main className="flex-1 min-w-0 px-8 py-7">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Offene Projekte</h1>
          <p className="text-muted mt-1">
            Finde Musiker, denen noch etwas fehlt – oder poste dein eigenes Projekt.
          </p>
        </div>
        <button onClick={() => setDialogOffen(true)}
          className="flex items-center gap-2 bg-brand-500 hover:bg-brand-600 text-ink-950 font-semibold text-sm px-4 py-2.5 rounded-xl transition-colors shrink-0">
          <Plus size={18} /> Projekt posten
        </button>
      </div>

      {/* Reiter */}
      <div className="flex gap-1 mt-6 border-b border-ink-700">
        <ReiterKnopf aktiv={reiter === "entdecken"} onClick={() => setReiter("entdecken")}
          icon={<Music2 size={16} />} label="Entdecken" />
        <ReiterKnopf aktiv={reiter === "folge-ich"} onClick={() => setReiter("folge-ich")}
          icon={<Users size={16} />} label="Folge ich" />
      </div>

      {/* Filter */}
      <div className="flex flex-wrap gap-2 mt-4">
        {kategorien.map((k) => {
          const aktiv = filter.includes(k.key);
          return (
            <button key={k.key} onClick={() => filterUmschalten(k.key)}
              className={`text-sm px-3 py-1.5 rounded-xl border transition-colors ${
                aktiv
                  ? "bg-brand-500 border-brand-500 text-ink-950 font-medium"
                  : "bg-ink-850 border-ink-700 text-muted hover:text-white"
              }`}>
              {k.name}
            </button>
          );
        })}
        {filter.length > 0 && (
          <button onClick={() => setFilter([])}
            className="text-sm px-3 py-1.5 text-muted hover:text-white">
            Filter zurücksetzen
          </button>
        )}
      </div>

      {fehler && (
        <div className="mt-5 bg-red-500/10 border border-red-500/40 text-red-400 text-sm rounded-xl px-4 py-3">
          {fehler}
        </div>
      )}

      {beitraege === null && !fehler && (
        <div className="mt-10 flex justify-center">
          <Loader2 size={28} className="text-brand-400 animate-spin" />
        </div>
      )}

      {beitraege && beitraege.length === 0 && (
        <div className="mt-6 bg-ink-850 border border-ink-700 rounded-2xl px-4 py-12 text-center">
          <p className="text-sm text-muted">
            {reiter === "folge-ich"
              ? "Hier erscheinen Projekte von Musikern, denen du folgst."
              : filter.length > 0
                ? "Zu diesen Filtern gibt es gerade nichts."
                : "Noch keine offenen Projekte."}
          </p>
          {reiter === "folge-ich" && (
            <button onClick={() => setReiter("entdecken")}
              className="mt-3 text-sm text-brand-400 hover:text-brand-500 font-medium">
              Erst mal umschauen
            </button>
          )}
        </div>
      )}

      {beitraege && beitraege.length > 0 && (
        <div className="mt-6 space-y-3">
          {beitraege.map((p) => (
            <Link key={p.id} to={`/projekt/${p.id}`}
              className="block hover:brightness-110 transition-all">
              <BeitragsKarte post={p} labels={labels} />
            </Link>
          ))}
        </div>
      )}

      {dialogOffen && (
        <CreatePostWizard
          onClose={() => setDialogOffen(false)}
          onCreated={() => { setDialogOffen(false); laden(); }}
        />
      )}
    </main>
  );
}

function ReiterKnopf({ aktiv, onClick, icon, label }: {
  aktiv: boolean; onClick: () => void; icon: React.ReactNode; label: string;
}) {
  return (
    <button onClick={onClick}
      className={`flex items-center gap-2 px-4 py-2.5 text-sm border-b-2 -mb-px transition-colors ${
        aktiv
          ? "border-brand-500 text-brand-400 font-medium"
          : "border-transparent text-muted hover:text-white"
      }`}>
      {icon}{label}
    </button>
  );
}
