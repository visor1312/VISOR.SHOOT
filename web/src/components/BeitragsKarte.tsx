import { Heart, MessageCircle, PlayCircle, CheckCircle2 } from "lucide-react";
import type { Post } from "../api";
import { formatDate } from "../lib/format";

/** Ein offenes Projekt als Karte - im Feed und auf Profilseiten.
 *
 * Die Kategorie-Bezeichnungen kommen als labels herein, statt sie hier noch
 * einmal aufzuschreiben: das Backend liefert sie ueber /post-categories, und
 * zwei Listen wuerden frueher oder spaeter auseinanderlaufen.
 */
export default function BeitragsKarte({ post, labels = {}, children }: {
  post: Post;
  labels?: Record<string, string>;
  children?: React.ReactNode;
}) {
  return (
    <div className="bg-ink-850 border border-ink-700 rounded-2xl p-5">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <h3 className="font-semibold truncate">{post.title}</h3>
          {post.author && (
            <p className="text-xs text-muted mt-0.5">
              {post.author.artist_name} · @{post.author.handle}
              {post.author.city && ` · ${post.author.city}`}
            </p>
          )}
        </div>
        {post.open_state === "closed" && (
          <span className="flex items-center gap-1 text-xs px-2 py-1 rounded-md bg-ink-700 text-muted shrink-0">
            <CheckCircle2 size={13} /> Erledigt
          </span>
        )}
      </div>

      {post.body && (
        <p className="text-sm text-muted mt-3 line-clamp-2 leading-relaxed">{post.body}</p>
      )}

      <div className="flex flex-wrap items-center gap-2 mt-3">
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
      </div>

      <div className="flex items-center gap-4 mt-4 text-xs text-muted">
        {post.has_audio && (
          <span className="flex items-center gap-1 text-brand-400">
            <PlayCircle size={14} /> Hörprobe
          </span>
        )}
        <span className="flex items-center gap-1"><Heart size={14} /> {post.interest_count ?? 0}</span>
        <span className="flex items-center gap-1">
          <MessageCircle size={14} /> {post.comment_count ?? 0}
        </span>
        <span className="ml-auto">{formatDate(post.created_at, { year: true })}</span>
      </div>

      {children}
    </div>
  );
}
