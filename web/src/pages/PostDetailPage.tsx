import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  Loader2, Heart, MessageCircle, Trash2, CheckCircle2, RotateCcw, ArrowLeft, ExternalLink,
  Flag,
} from "lucide-react";
import MeldenDialog from "../components/MeldenDialog";
import {
  getPost, getPostCategories, getInterest, setInterest, getComments, addComment,
  deleteComment, setPostOpenState, deletePost, postAudioUrl,
  type Post, type Comment, type InterestState, type Profile, type PostCategory,
} from "../api";
import { useApp } from "../components/app-context";
import { formatDate } from "../lib/format";

/** Ein offenes Projekt in voller Ansicht: anhoeren, Interesse zeigen,
 *  kommentieren. Der Autor sieht hier, WER helfen will. */
export default function PostDetailPage() {
  const { postId = "" } = useParams();
  const { user } = useApp();
  const navigate = useNavigate();

  const [post, setPost] = useState<Post | null>(null);
  const [labels, setLabels] = useState<Record<string, string>>({});
  const [interesse, setInteresse] = useState<InterestState | null>(null);
  const [kommentare, setKommentare] = useState<Comment[]>([]);
  const [neuerText, setNeuerText] = useState("");
  const [busy, setBusy] = useState(false);
  const [fehler, setFehler] = useState("");
  // Was gerade gemeldet wird (null = kein Dialog offen).
  const [melden, setMelden] = useState<{ art: "post" | "comment"; id: string } | null>(null);

  const istAutor = post?.user_id === user.id;

  const laden = useCallback(async () => {
    setFehler("");
    try {
      const [p, i, k] = await Promise.all([
        getPost(postId), getInterest(postId), getComments(postId),
      ]);
      setPost(p);
      setInteresse(i);
      setKommentare(k);
    } catch (e) {
      setFehler(e instanceof Error ? e.message : String(e));
    }
  }, [postId]);

  useEffect(() => { laden(); }, [laden]);
  useEffect(() => {
    getPostCategories()
      .then((ks) => setLabels(Object.fromEntries(ks.map((k: PostCategory) => [k.key, k.name]))))
      .catch(() => setLabels({}));
  }, []);

  async function interesseUmschalten() {
    if (!interesse || busy) return;
    setBusy(true);
    try {
      await setInterest(postId, !interesse.interested);
      setInteresse(await getInterest(postId));
    } catch (e) {
      setFehler(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  async function kommentieren(e: React.FormEvent) {
    e.preventDefault();
    if (!neuerText.trim() || busy) return;
    setBusy(true);
    try {
      await addComment(postId, neuerText);
      setNeuerText("");
      setKommentare(await getComments(postId));
    } catch (ex) {
      setFehler(ex instanceof Error ? ex.message : String(ex));
    } finally {
      setBusy(false);
    }
  }

  async function kommentarLoeschen(id: string) {
    await deleteComment(id).catch((e) => setFehler(String(e)));
    setKommentare(await getComments(postId));
  }

  async function erledigtUmschalten() {
    if (!post) return;
    setPost(await setPostOpenState(postId, post.open_state === "closed"));
  }

  async function beitragLoeschen() {
    if (!confirm("Dieses Projekt wirklich löschen? Das lässt sich nicht rückgängig machen.")) return;
    await deletePost(postId);
    navigate("/projekte-feed");
  }

  if (fehler && !post) {
    return (
      <main className="flex-1 min-w-0 px-8 py-7">
        <div className="bg-red-500/10 border border-red-500/40 text-red-400 text-sm rounded-xl px-4 py-3">
          {fehler}
        </div>
      </main>
    );
  }

  if (!post) {
    return (
      <main className="flex-1 min-w-0 px-8 py-7 flex justify-center">
        <Loader2 size={28} className="text-brand-400 animate-spin mt-8" />
      </main>
    );
  }

  return (
    <main className="flex-1 min-w-0 px-8 py-7 max-w-3xl">
      <Link to="/projekte-feed"
        className="inline-flex items-center gap-1.5 text-sm text-muted hover:text-white">
        <ArrowLeft size={16} /> Zurück zu den Projekten
      </Link>

      <div className="mt-5 bg-ink-850 border border-ink-700 rounded-2xl p-6">
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <h1 className="text-2xl font-bold tracking-tight">{post.title}</h1>
            {post.author && (
              <Link to={`/musiker/${post.author.handle}`}
                className="text-sm text-muted hover:text-brand-400 mt-1 inline-block">
                {post.author.artist_name} · @{post.author.handle}
                {post.author.city && ` · ${post.author.city}`}
              </Link>
            )}
          </div>
          {post.open_state === "closed" && (
            <span className="flex items-center gap-1 text-xs px-2.5 py-1 rounded-md bg-ink-700 text-muted shrink-0">
              <CheckCircle2 size={13} /> Erledigt
            </span>
          )}
        </div>

        {post.body && (
          <p className="text-sm mt-4 leading-relaxed whitespace-pre-wrap">{post.body}</p>
        )}

        <div className="flex flex-wrap items-center gap-2 mt-4">
          {post.categories.map((c) => (
            <span key={c} className="text-xs px-2 py-1 rounded-md bg-brand-500/12 text-brand-400">
              {labels[c] ?? c}
            </span>
          ))}
          {post.genres.map((g) => (
            <span key={g} className="text-xs px-2 py-1 rounded-md bg-ink-800 text-muted">{g}</span>
          ))}
          {post.bpm && (
            <span className="text-xs px-2 py-1 rounded-md bg-ink-800 text-muted">{post.bpm} BPM</span>
          )}
          <span className="text-xs text-ink-600 ml-auto">
            {formatDate(post.created_at, { year: true })}
          </span>
        </div>

        {post.has_audio && (
          <div className="mt-5">
            <p className="text-sm text-muted mb-2">Hörprobe</p>
            <audio controls src={postAudioUrl(post.id)} className="w-full" />
          </div>
        )}

        {/* Handlungen */}
        <div className="flex flex-wrap items-center gap-3 mt-6 pt-5 border-t border-ink-700">
          {!istAutor && (
            <button onClick={interesseUmschalten} disabled={busy}
              className={`flex items-center gap-2 text-sm font-semibold px-4 py-2.5 rounded-xl transition-colors ${
                interesse?.interested
                  ? "bg-brand-500/15 text-brand-400 hover:bg-brand-500/25"
                  : "bg-brand-500 hover:bg-brand-600 text-ink-950"
              }`}>
              <Heart size={16} className={interesse?.interested ? "fill-current" : ""} />
              {interesse?.interested ? "Interesse zurückziehen" : "Ich hab Interesse"}
            </button>
          )}
          {/* Melden: nur bei fremden Beitraegen sinnvoll - eigene loescht man.
              Unauffaellig, aber ohne Suchen auffindbar (DSA). */}
          {!istAutor && (
            <button onClick={() => setMelden({ art: "post", id: post.id })}
              className="flex items-center gap-2 text-sm px-4 py-2.5 rounded-xl text-muted hover:text-red-400 hover:bg-red-500/10 transition-colors ml-auto">
              <Flag size={16} /> Melden
            </button>
          )}
          {istAutor && (
            <>
              <button onClick={erledigtUmschalten}
                className="flex items-center gap-2 text-sm font-medium px-4 py-2.5 rounded-xl bg-ink-800 hover:bg-ink-700 transition-colors">
                {post.open_state === "open"
                  ? <><CheckCircle2 size={16} /> Als erledigt markieren</>
                  : <><RotateCcw size={16} /> Wieder öffnen</>}
              </button>
              <button onClick={beitragLoeschen}
                className="flex items-center gap-2 text-sm px-4 py-2.5 rounded-xl text-red-400 hover:bg-red-500/10 transition-colors">
                <Trash2 size={16} /> Löschen
              </button>
            </>
          )}
        </div>
      </div>

      {/* Wer helfen will - der Kontaktweg */}
      {istAutor && (
        <section className="mt-6">
          <h2 className="text-lg font-semibold">
            Wer helfen will ({interesse?.count ?? 0})
          </h2>
          {interesse && interesse.people.length === 0 ? (
            <p className="text-sm text-muted mt-2">
              Noch niemand. Sobald sich jemand meldet, siehst du ihn hier mit Profil.
            </p>
          ) : (
            <div className="mt-3 space-y-2">
              {interesse?.people.map((p) => <InteressentenZeile key={p.user_id} profil={p} />)}
            </div>
          )}
        </section>
      )}

      {/* Kommentare */}
      <section className="mt-8">
        <h2 className="flex items-center gap-2 text-lg font-semibold">
          <MessageCircle size={18} /> Kommentare ({kommentare.length})
        </h2>

        <form onSubmit={kommentieren} className="mt-3 flex gap-2">
          <input value={neuerText} onChange={(e) => setNeuerText(e.target.value)}
            maxLength={1000} placeholder="Schreib etwas dazu…"
            className="flex-1 text-sm bg-ink-800 border border-ink-700 focus:border-brand-500 rounded-xl px-3 py-2.5 outline-none" />
          <button type="submit" disabled={!neuerText.trim() || busy}
            className="bg-brand-500 hover:bg-brand-600 disabled:opacity-40 text-ink-950 font-semibold text-sm px-4 rounded-xl transition-colors">
            Senden
          </button>
        </form>

        <div className="mt-4 space-y-3">
          {kommentare.map((k) => {
            // Loeschen darf der Verfasser - und der Eigentuemer des Projekts.
            const darfLoeschen = k.author.user_id === user.id || istAutor;
            return (
              <div key={k.id} className="bg-ink-850 border border-ink-700 rounded-xl px-4 py-3">
                <div className="flex items-center justify-between gap-3">
                  <Link to={`/musiker/${k.author.handle}`}
                    className="text-sm font-medium hover:text-brand-400">
                    {k.author.artist_name}
                    <span className="text-xs text-muted font-normal"> · @{k.author.handle}</span>
                  </Link>
                  <div className="flex items-center gap-2 shrink-0">
                    <span className="text-xs text-ink-600">
                      {formatDate(k.created_at, { year: true })}
                    </span>
                    {darfLoeschen && (
                      <button onClick={() => kommentarLoeschen(k.id)} title="Kommentar löschen"
                        className="text-muted hover:text-red-400">
                        <Trash2 size={14} />
                      </button>
                    )}
                    {k.author.user_id !== user.id && (
                      <button onClick={() => setMelden({ art: "comment", id: k.id })}
                        title="Kommentar melden"
                        className="text-muted hover:text-red-400">
                        <Flag size={14} />
                      </button>
                    )}
                  </div>
                </div>
                <p className="text-sm mt-1.5 whitespace-pre-wrap">{k.body}</p>
              </div>
            );
          })}
          {kommentare.length === 0 && (
            <p className="text-sm text-muted">Noch keine Kommentare.</p>
          )}
        </div>
      </section>

      {fehler && (
        <div className="mt-5 bg-red-500/10 border border-red-500/40 text-red-400 text-sm rounded-xl px-4 py-3">
          {fehler}
        </div>
      )}

      {melden && (
        <MeldenDialog art={melden.art} zielId={melden.id}
          onClose={() => setMelden(null)} />
      )}
    </main>
  );
}

/** Ein Interessent samt seiner Links - genau hier laeuft der Kontakt.
 *  Direktnachrichten gibt es (noch) nicht; die Profile tragen die Kanaele,
 *  die Musiker ohnehin benutzen. */
function InteressentenZeile({ profil }: { profil: Profile }) {
  const links = Object.entries(profil.links ?? {});
  return (
    <div className="bg-ink-850 border border-ink-700 rounded-xl px-4 py-3">
      <div className="flex items-center justify-between gap-3">
        <Link to={`/musiker/${profil.handle}`} className="min-w-0 hover:text-brand-400">
          <p className="text-sm font-medium truncate">{profil.artist_name}</p>
          <p className="text-xs text-muted truncate">
            @{profil.handle}{profil.city && ` · ${profil.city}`}
          </p>
        </Link>
        <div className="flex flex-wrap gap-1.5 shrink-0">
          {links.map(([art, url]) => (
            <a key={art} href={url} target="_blank" rel="noopener noreferrer"
              className="flex items-center gap-1 text-xs px-2 py-1 rounded-lg bg-ink-800 hover:bg-ink-700 text-muted hover:text-white transition-colors">
              {art} <ExternalLink size={11} />
            </a>
          ))}
        </div>
      </div>
      {links.length === 0 && (
        <p className="text-xs text-ink-600 mt-1.5">
          Keine Links im Profil – schreib einen Kommentar, um Kontakt aufzunehmen.
        </p>
      )}
    </div>
  );
}
