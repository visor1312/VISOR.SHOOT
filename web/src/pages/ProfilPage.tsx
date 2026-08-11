import { useEffect, useState } from "react";
import { Loader2, Check, Music2, MapPin, Link as LinkIcon } from "lucide-react";
import {
  getMyProfile, updateMyProfile, PROFILE_LINK_KEYS,
  type Profile, type ProfileLinkKey,
} from "../api";

const LINK_LABELS: Record<ProfileLinkKey, string> = {
  spotify: "Spotify",
  instagram: "Instagram",
  youtube: "YouTube",
  tiktok: "TikTok",
  soundcloud: "SoundCloud",
  website: "Webseite",
};

/** Das eigene Musiker-Profil: das, was andere im Netzwerk von dir sehen. */
export default function ProfilPage() {
  const [profil, setProfil] = useState<Profile | null>(null);
  const [ladeFehler, setLadeFehler] = useState("");

  const [artistName, setArtistName] = useState("");
  const [bio, setBio] = useState("");
  const [city, setCity] = useState("");
  const [genres, setGenres] = useState("");
  const [links, setLinks] = useState<Partial<Record<ProfileLinkKey, string>>>({});

  const [speichert, setSpeichert] = useState(false);
  const [gespeichert, setGespeichert] = useState(false);
  const [fehler, setFehler] = useState("");

  useEffect(() => {
    let cancelled = false;
    getMyProfile()
      .then((p) => {
        if (cancelled) return;
        uebernehmen(p);
      })
      .catch((e) => {
        if (!cancelled) setLadeFehler(e instanceof Error ? e.message : String(e));
      });
    return () => { cancelled = true; };
  }, []);

  function uebernehmen(p: Profile) {
    setProfil(p);
    setArtistName(p.artist_name);
    setBio(p.bio);
    setCity(p.city);
    setGenres(p.genres.join(", "));
    setLinks(p.links);
  }

  async function speichern(e: React.FormEvent) {
    e.preventDefault();
    if (speichert) return;
    setSpeichert(true);
    setFehler("");
    setGespeichert(false);
    try {
      const aktualisiert = await updateMyProfile({
        artist_name: artistName,
        bio,
        city,
        genres: genres.split(",").map((g) => g.trim()).filter(Boolean),
        links,
      });
      uebernehmen(aktualisiert);
      setGespeichert(true);
    } catch (ex) {
      setFehler(ex instanceof Error ? ex.message : String(ex));
    } finally {
      setSpeichert(false);
    }
  }

  if (ladeFehler) {
    return (
      <main className="flex-1 min-w-0 px-8 py-7">
        <div className="bg-red-500/10 border border-red-500/40 text-red-400 text-sm rounded-xl px-4 py-3">
          {ladeFehler}
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

  return (
    <main className="flex-1 min-w-0 px-8 py-7">
      <h1 className="text-3xl font-bold tracking-tight">Mein Profil</h1>
      <p className="text-muted mt-1">
        Das sehen andere Musiker von dir. Deine E-Mail bleibt privat.
      </p>

      <div className="mt-4 inline-flex items-center gap-2 text-sm bg-ink-850 border border-ink-700 rounded-xl px-3 py-2">
        <span className="text-muted">Deine Profil-Adresse:</span>
        <span className="font-medium text-brand-400">@{profil.handle}</span>
      </div>

      <form onSubmit={speichern} className="mt-6 max-w-2xl space-y-5">
        <Feld label="Künstlername" icon={<Music2 size={16} className="text-muted" />}>
          <input value={artistName} onChange={(e) => setArtistName(e.target.value)}
            maxLength={60} placeholder="z.B. YngLyric"
            className="w-full text-sm bg-ink-800 border border-ink-700 focus:border-brand-500 rounded-xl px-3 py-2.5 outline-none" />
        </Feld>

        <Feld label="Über dich">
          <textarea value={bio} onChange={(e) => setBio(e.target.value)}
            rows={4} maxLength={500}
            placeholder="Woran arbeitest du? Was suchst du?"
            className="w-full text-sm bg-ink-800 border border-ink-700 focus:border-brand-500 rounded-xl px-3 py-2.5 outline-none resize-none" />
          <p className="text-xs text-ink-600 mt-1">{bio.length}/500</p>
        </Feld>

        <Feld label="Stadt" icon={<MapPin size={16} className="text-muted" />}>
          <input value={city} onChange={(e) => setCity(e.target.value)}
            maxLength={80} placeholder="z.B. Hamburg"
            className="w-full text-sm bg-ink-800 border border-ink-700 focus:border-brand-500 rounded-xl px-3 py-2.5 outline-none" />
        </Feld>

        <Feld label="Genres (mit Komma trennen, max. 5)">
          <input value={genres} onChange={(e) => setGenres(e.target.value)}
            placeholder="z.B. Deutschrap, Trap, Boom Bap"
            className="w-full text-sm bg-ink-800 border border-ink-700 focus:border-brand-500 rounded-xl px-3 py-2.5 outline-none" />
        </Feld>

        <div>
          <span className="flex items-center gap-2 text-sm text-muted">
            <LinkIcon size={16} /> Deine Links
          </span>
          <div className="mt-2 grid grid-cols-1 sm:grid-cols-2 gap-3">
            {PROFILE_LINK_KEYS.map((schluessel) => (
              <label key={schluessel} className="block">
                <span className="text-xs text-ink-600">{LINK_LABELS[schluessel]}</span>
                <input
                  value={links[schluessel] ?? ""}
                  onChange={(e) => setLinks({ ...links, [schluessel]: e.target.value })}
                  placeholder="https://…"
                  className="mt-1 w-full text-sm bg-ink-800 border border-ink-700 focus:border-brand-500 rounded-xl px-3 py-2 outline-none" />
              </label>
            ))}
          </div>
          <p className="text-xs text-ink-600 mt-2">
            Nur Adressen, die mit http:// oder https:// beginnen, werden übernommen.
          </p>
        </div>

        {fehler && (
          <div className="bg-red-500/10 border border-red-500/40 text-red-400 text-sm rounded-xl px-4 py-3">
            {fehler}
          </div>
        )}

        <div className="flex items-center gap-3">
          <button type="submit" disabled={speichert}
            className="flex items-center gap-2 bg-brand-500 hover:bg-brand-600 disabled:opacity-40 text-ink-950 font-semibold text-sm px-5 py-2.5 rounded-xl transition-colors">
            {speichert ? <Loader2 size={16} className="animate-spin" /> : <Check size={16} />}
            Speichern
          </button>
          {gespeichert && !speichert && (
            <span className="text-sm text-brand-400">Gespeichert.</span>
          )}
        </div>
      </form>
    </main>
  );
}

function Feld({ label, icon, children }: {
  label: string; icon?: React.ReactNode; children: React.ReactNode;
}) {
  return (
    <label className="block">
      <span className="flex items-center gap-2 text-sm text-muted">
        {icon}{label}
      </span>
      <div className="mt-1.5">{children}</div>
    </label>
  );
}
