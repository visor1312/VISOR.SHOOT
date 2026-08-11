import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Loader2, MapPin, UserPlus, UserCheck, ArrowLeft, ExternalLink } from "lucide-react";
import {
  getProfile, getProfilePosts, followProfile, unfollowProfile, getPostCategories,
  type Profile, type Post, type PostCategory,
} from "../api";
import BeitragsKarte from "../components/BeitragsKarte";

/** Das Profil eines anderen Musikers: wer ist das, was macht er, und
 *  woran arbeitet er gerade. */
export default function ProfilAnsichtPage() {
  const { handle = "" } = useParams();
  const [profil, setProfil] = useState<Profile | null>(null);
  const [beitraege, setBeitraege] = useState<Post[]>([]);
  const [labels, setLabels] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [fehler, setFehler] = useState("");

  const laden = useCallback(async () => {
    setFehler("");
    try {
      const [p, b] = await Promise.all([getProfile(handle), getProfilePosts(handle)]);
      setProfil(p);
      setBeitraege(b);
    } catch (e) {
      setFehler(e instanceof Error ? e.message : String(e));
    }
  }, [handle]);

  useEffect(() => { laden(); }, [laden]);
  useEffect(() => {
    getPostCategories()
      .then((ks) => setLabels(Object.fromEntries(ks.map((k: PostCategory) => [k.key, k.name]))))
      .catch(() => setLabels({}));
  }, []);

  async function folgenUmschalten() {
    if (!profil || busy) return;
    setBusy(true);
    try {
      setProfil(profil.is_following
        ? await unfollowProfile(handle)
        : await followProfile(handle));
    } catch (e) {
      setFehler(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  if (fehler && !profil) {
    return (
      <main className="flex-1 min-w-0 px-8 py-7">
        <div className="bg-red-500/10 border border-red-500/40 text-red-400 text-sm rounded-xl px-4 py-3">
          {fehler}
        </div>
      </main>
    );
  }

  if (!profil) {
    return (
      <main className="flex-1 min-w-0 px-8 py-7 flex justify-center">
        <Loader2 size={28} className="text-brand-400 animate-spin mt-8" />
      </main>
    );
  }

  const links = Object.entries(profil.links ?? {});

  return (
    <main className="flex-1 min-w-0 px-8 py-7 max-w-3xl">
      <Link to="/projekte-feed"
        className="inline-flex items-center gap-1.5 text-sm text-muted hover:text-white">
        <ArrowLeft size={16} /> Zurück zu den Projekten
      </Link>

      <div className="mt-5 bg-ink-850 border border-ink-700 rounded-2xl p-6">
        <div className="flex items-start gap-4">
          <div className="w-16 h-16 rounded-full bg-gradient-to-br from-amber-500 to-orange-700 shrink-0 flex items-center justify-center text-lg font-bold text-white">
            {profil.artist_name.trim().slice(0, 2).toUpperCase()}
          </div>
          <div className="flex-1 min-w-0">
            <h1 className="text-2xl font-bold tracking-tight truncate">{profil.artist_name}</h1>
            <p className="text-sm text-muted">@{profil.handle}</p>
            {profil.city && (
              <p className="flex items-center gap-1 text-sm text-muted mt-1">
                <MapPin size={14} /> {profil.city}
              </p>
            )}
          </div>
          {!profil.is_self && (
            <button onClick={folgenUmschalten} disabled={busy}
              className={`flex items-center gap-2 text-sm font-semibold px-4 py-2.5 rounded-xl transition-colors shrink-0 ${
                profil.is_following
                  ? "bg-ink-800 hover:bg-ink-700 text-white"
                  : "bg-brand-500 hover:bg-brand-600 text-ink-950"
              }`}>
              {profil.is_following
                ? <><UserCheck size={16} /> Folgst du</>
                : <><UserPlus size={16} /> Folgen</>}
            </button>
          )}
        </div>

        {profil.bio && (
          <p className="text-sm mt-4 leading-relaxed whitespace-pre-wrap">{profil.bio}</p>
        )}

        <div className="flex flex-wrap items-center gap-2 mt-4">
          {profil.genres.map((g) => (
            <span key={g} className="text-xs px-2 py-1 rounded-md bg-ink-800 text-muted">{g}</span>
          ))}
        </div>

        <div className="flex items-center gap-5 mt-4 text-sm">
          <span><strong>{profil.followers ?? 0}</strong> <span className="text-muted">Follower</span></span>
          <span><strong>{profil.following ?? 0}</strong> <span className="text-muted">Folge ich</span></span>
        </div>

        {links.length > 0 && (
          <div className="flex flex-wrap gap-2 mt-4 pt-4 border-t border-ink-700">
            {links.map(([art, url]) => (
              <a key={art} href={url} target="_blank" rel="noopener noreferrer"
                className="flex items-center gap-1.5 text-sm px-3 py-1.5 rounded-lg bg-ink-800 hover:bg-ink-700 text-muted hover:text-white transition-colors">
                {art} <ExternalLink size={12} />
              </a>
            ))}
          </div>
        )}
      </div>

      <h2 className="text-lg font-semibold mt-8">
        Projekte von {profil.artist_name} ({beitraege.length})
      </h2>
      <div className="mt-3 space-y-3">
        {beitraege.map((p) => (
          <Link key={p.id} to={`/projekt/${p.id}`} className="block">
            <BeitragsKarte post={p} labels={labels} />
          </Link>
        ))}
        {beitraege.length === 0 && (
          <p className="text-sm text-muted">Noch keine Projekte gepostet.</p>
        )}
      </div>
    </main>
  );
}
