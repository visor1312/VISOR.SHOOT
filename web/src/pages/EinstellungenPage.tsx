import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  Mail, User as UserIcon, KeyRound, Ticket, Users, Check, Loader2, Plus, Copy, Flag,
  Trash2,
} from "lucide-react";
import {
  updateDisplayName, changePassword, listInvites, createInvite, listUsers,
  listReports, handleReport, deleteMe,
  type InviteCode, type AdminUser, type Meldung,
} from "../api";
import { useApp } from "../components/app-context";
import { formatDate } from "../lib/format";

export default function EinstellungenPage() {
  const { user, setUser } = useApp();
  return (
    <main className="flex-1 min-w-0 px-8 py-7 max-w-3xl">
      <h1 className="text-3xl font-bold tracking-tight">Einstellungen</h1>
      <p className="text-muted mt-1">Dein Konto{user.is_admin ? " und die Verwaltung" : ""}.</p>

      <div className="mt-6 space-y-4">
        <NameCard user={user} onUpdated={setUser} />
        <PasswordCard />
        {user.is_admin && <AdminSection />}
        {/* Ganz unten und optisch abgesetzt: nichts hier ist so endgueltig. */}
        <KontoLoeschenCard />
      </div>
    </main>
  );
}

function Card({ title, icon, children }: { title: string; icon: React.ReactNode; children: React.ReactNode }) {
  return (
    <div className="bg-ink-850 border border-ink-700 rounded-2xl p-6">
      <h2 className="flex items-center gap-2 font-semibold">{icon} {title}</h2>
      <div className="mt-4">{children}</div>
    </div>
  );
}

function Feedback({ ok, err }: { ok: string; err: string }) {
  if (err) return <p className="text-sm text-red-400 mt-2">{err}</p>;
  if (ok) return <p className="text-sm text-brand-400 mt-2 flex items-center gap-1"><Check size={14} /> {ok}</p>;
  return null;
}

const inputClass =
  "w-full text-sm bg-ink-800 border border-ink-700 focus:border-brand-500 rounded-xl px-3 py-2.5 outline-none";

function NameCard({ user, onUpdated }: { user: { display_name: string; email: string }; onUpdated: (u: import("../api").User) => void }) {
  const [name, setName] = useState(user.display_name);
  const [busy, setBusy] = useState(false);
  const [ok, setOk] = useState("");
  const [err, setErr] = useState("");

  async function save() {
    setBusy(true); setOk(""); setErr("");
    try {
      const updated = await updateDisplayName(name.trim());
      onUpdated(updated);
      setOk("Gespeichert.");
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card title="Konto" icon={<UserIcon size={18} className="text-brand-400" />}>
      <label className="block">
        <span className="text-sm text-muted">Anzeigename</span>
        <input value={name} onChange={(e) => setName(e.target.value)} className={`${inputClass} mt-1.5`} />
      </label>
      <div className="flex items-center gap-2 mt-3 text-sm text-muted">
        <Mail size={15} /> {user.email} <span className="text-ink-600">(nicht änderbar)</span>
      </div>
      <button disabled={busy || name.trim() === "" || name.trim() === user.display_name} onClick={save}
        className="mt-4 bg-brand-500 hover:bg-brand-600 disabled:opacity-40 text-ink-950 font-semibold text-sm px-4 py-2 rounded-xl transition-colors flex items-center gap-2">
        {busy && <Loader2 size={15} className="animate-spin" />} Namen speichern
      </button>
      <Feedback ok={ok} err={err} />
    </Card>
  );
}

function PasswordCard() {
  const [cur, setCur] = useState("");
  const [next, setNext] = useState("");
  const [repeat, setRepeat] = useState("");
  const [busy, setBusy] = useState(false);
  const [ok, setOk] = useState("");
  const [err, setErr] = useState("");

  async function save() {
    setOk(""); setErr("");
    if (next !== repeat) { setErr("Die neuen Passwörter stimmen nicht überein."); return; }
    setBusy(true);
    try {
      await changePassword(cur, next);
      setOk("Passwort geändert. Andere Geräte wurden abgemeldet.");
      setCur(""); setNext(""); setRepeat("");
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card title="Passwort ändern" icon={<KeyRound size={18} className="text-brand-400" />}>
      <div className="space-y-3">
        <input type="password" placeholder="Aktuelles Passwort" autoComplete="current-password"
          value={cur} onChange={(e) => setCur(e.target.value)} className={inputClass} />
        <input type="password" placeholder="Neues Passwort (mind. 8 Zeichen)" autoComplete="new-password"
          value={next} onChange={(e) => setNext(e.target.value)} className={inputClass} />
        <input type="password" placeholder="Neues Passwort wiederholen" autoComplete="new-password"
          value={repeat} onChange={(e) => setRepeat(e.target.value)} className={inputClass} />
      </div>
      <button disabled={busy || !cur || !next || !repeat} onClick={save}
        className="mt-4 bg-brand-500 hover:bg-brand-600 disabled:opacity-40 text-ink-950 font-semibold text-sm px-4 py-2 rounded-xl transition-colors flex items-center gap-2">
        {busy && <Loader2 size={15} className="animate-spin" />} Passwort ändern
      </button>
      <Feedback ok={ok} err={err} />
    </Card>
  );
}

function AdminSection() {
  const [invites, setInvites] = useState<InviteCode[]>([]);
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [err, setErr] = useState("");
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    let cancelled = false;
    Promise.all([listInvites(), listUsers()])
      .then(([i, u]) => { if (!cancelled) { setInvites(i); setUsers(u); } })
      .catch((e) => !cancelled && setErr(e instanceof Error ? e.message : String(e)));
    return () => { cancelled = true; };
  }, []);

  async function makeInvite() {
    setCreating(true); setErr("");
    try {
      const inv = await createInvite();
      setInvites((prev) => [...prev, inv]);
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setCreating(false);
    }
  }

  return (
    <>
      {/* Meldungen zuerst: das ist die einzige Liste hier, bei der Warten
          echte Folgen hat. */}
      <MeldungenCard />

      <Card title="Einladungscodes" icon={<Ticket size={18} className="text-brand-400" />}>
        <p className="text-sm text-muted">
          Neue Konten können sich nur mit einem Einladungscode registrieren.
        </p>
        <button disabled={creating} onClick={makeInvite}
          className="mt-3 bg-brand-500 hover:bg-brand-600 disabled:opacity-40 text-ink-950 font-semibold text-sm px-4 py-2 rounded-xl transition-colors flex items-center gap-2">
          {creating ? <Loader2 size={15} className="animate-spin" /> : <Plus size={15} />} Neuen Code erzeugen
        </button>
        {err && <p className="text-sm text-red-400 mt-2">{err}</p>}
        <div className="mt-4 space-y-1.5">
          {invites.length === 0 && <p className="text-sm text-muted">Noch keine Codes.</p>}
          {invites.map((inv) => (
            <div key={inv.code}
              className="flex items-center gap-3 bg-ink-800 rounded-lg px-3 py-2 text-sm">
              <code className={`font-mono ${inv.used ? "text-ink-600 line-through" : "text-white"}`}>{inv.code}</code>
              <span className="flex-1 text-xs text-muted">
                {inv.used ? `verwendet von ${inv.used_by_email}` : "offen"}
              </span>
              {!inv.used && (
                <button title="Code kopieren" onClick={() => navigator.clipboard.writeText(inv.code)}
                  className="text-muted hover:text-white"><Copy size={14} /></button>
              )}
            </div>
          ))}
        </div>
      </Card>

      <Card title={`Nutzer (${users.length})`} icon={<Users size={18} className="text-brand-400" />}>
        <div className="space-y-1.5">
          {users.map((u) => (
            <div key={u.id} className="flex items-center gap-3 bg-ink-800 rounded-lg px-3 py-2 text-sm">
              <div className="flex-1 min-w-0">
                <p className="font-medium truncate">{u.display_name}</p>
                <p className="text-xs text-muted truncate">{u.email}</p>
              </div>
              {u.is_admin && (
                <span className="text-[10px] uppercase tracking-wide px-1.5 py-0.5 rounded bg-brand-500/15 text-brand-400">
                  Admin
                </span>
              )}
              <span className="text-xs text-muted shrink-0">{formatDate(u.created_at, { year: true })}</span>
            </div>
          ))}
        </div>
      </Card>
    </>
  );
}

/** Konto loeschen (DSGVO Art. 17).
 *
 * Zwei Huerden, mit Absicht: erst aufklappen, dann Passwort eingeben. Das
 * ist unwiderruflich, und der Knopf sitzt auf derselben Seite wie harmlose
 * Einstellungen - ein Fehlklick darf nicht reichen.
 *
 * Ehrlich benennen, was verschwindet: wer nicht weiss, dass seine Beitraege
 * mitgehen, fuehlt sich hinterher betrogen.
 */
function KontoLoeschenCard() {
  const [offen, setOffen] = useState(false);
  const [passwort, setPasswort] = useState("");
  const [laeuft, setLaeuft] = useState(false);
  const [err, setErr] = useState("");

  async function loeschen(e: React.FormEvent) {
    e.preventDefault();
    setLaeuft(true); setErr("");
    try {
      await deleteMe(passwort);
      // Das Konto gibt es nicht mehr - komplett neu laden ist hier das
      // Ehrlichste: die App startet auf der Anmeldemaske, ohne Reste im
      // Zustand des Browsers.
      window.location.href = "/";
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
      setLaeuft(false);
    }
  }

  return (
    <div className="bg-ink-900 border border-red-500/25 rounded-2xl p-5">
      <h2 className="flex items-center gap-2 font-semibold">
        <Trash2 size={18} className="text-red-400" />
        Konto löschen
      </h2>

      {!offen ? (
        <>
          <p className="text-sm text-muted mt-2 leading-relaxed">
            Löscht dein Konto, dein Profil, alle deine Beiträge samt Hörproben
            und alle deine Kommentare – endgültig und ohne
            Wiederherstellungsmöglichkeit.
          </p>
          <button onClick={() => setOffen(true)}
            className="mt-3 text-sm px-4 py-2 rounded-xl bg-red-500/15 text-red-400 hover:bg-red-500/25 transition-colors">
            Konto löschen…
          </button>
        </>
      ) : (
        <form onSubmit={loeschen} className="mt-3 space-y-3">
          <p className="text-sm text-muted leading-relaxed">
            Das lässt sich <strong className="text-white">nicht</strong>{" "}
            rückgängig machen. Zum Bestätigen bitte dein Passwort eingeben.
          </p>
          <input type="password" value={passwort} autoFocus
            onChange={(e) => setPasswort(e.target.value)}
            placeholder="Dein Passwort"
            className="w-full text-sm bg-ink-800 border border-ink-700 focus:border-red-500 rounded-xl px-3 py-2.5 outline-none" />
          {err && <p className="text-sm text-red-400">{err}</p>}
          <div className="flex gap-2">
            <button type="button" onClick={() => { setOffen(false); setPasswort(""); setErr(""); }}
              className="flex-1 text-sm px-4 py-2.5 rounded-xl bg-ink-800 hover:bg-ink-700 transition-colors">
              Abbrechen
            </button>
            <button type="submit" disabled={!passwort || laeuft}
              className="flex-1 flex items-center justify-center gap-2 bg-red-500 hover:bg-red-600 disabled:opacity-40 text-white font-semibold text-sm px-4 py-2.5 rounded-xl transition-colors">
              {laeuft ? <Loader2 size={16} className="animate-spin" /> : <Trash2 size={16} />}
              Endgültig löschen
            </button>
          </div>
        </form>
      )}
    </div>
  );
}

/** Gemeldete Inhalte - die Arbeitsliste des Betreibers.
 *
 * Bewusst mit Vorschau und Sprung zum Beitrag: eine Meldung ohne den
 * Zusammenhang zu sehen laesst sich nicht entscheiden. Beide Knoepfe sind
 * gleichwertig - "ist in Ordnung" ist genauso eine Entscheidung wie
 * "ausblenden", und beide raeumen die Meldung aus der Liste.
 */
function MeldungenCard() {
  const [meldungen, setMeldungen] = useState<Meldung[]>([]);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState("");

  const laden = useCallback(() => {
    listReports("open")
      .then(setMeldungen)
      .catch((e) => setErr(e instanceof Error ? e.message : String(e)));
  }, []);

  useEffect(laden, [laden]);

  async function entscheiden(id: string, aktion: "ausblenden" | "behalten") {
    setBusy(id); setErr("");
    try {
      await handleReport(id, aktion);
      laden();
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy("");
    }
  }

  return (
    <Card title={`Gemeldete Inhalte (${meldungen.length})`}
      icon={<Flag size={18} className={meldungen.length ? "text-red-400" : "text-brand-400"} />}>
      {err && <p className="text-sm text-red-400 mb-2">{err}</p>}
      {meldungen.length === 0 && (
        <p className="text-sm text-muted">Nichts offen. Gut so.</p>
      )}
      <div className="space-y-2">
        {meldungen.map((m) => (
          <div key={m.id} className="bg-ink-800 rounded-lg px-3 py-2.5 text-sm">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-xs px-2 py-0.5 rounded bg-red-500/15 text-red-400">
                {m.reason_label}
              </span>
              <span className="text-xs text-muted">
                {m.target_type === "post" ? "Beitrag" : "Kommentar"} · gemeldet von {m.reporter_name}
              </span>
              <span className="text-xs text-ink-600 ml-auto">
                {formatDate(m.created_at, { year: true })}
              </span>
            </div>

            {m.vorschau === null ? (
              <p className="text-sm text-ink-600 italic mt-1.5">
                Inhalt wurde inzwischen gelöscht.
              </p>
            ) : (
              <p className="mt-1.5 line-clamp-2">{m.vorschau}</p>
            )}
            {m.note && (
              <p className="text-xs text-muted mt-1 italic">„{m.note}"</p>
            )}

            <div className="flex items-center gap-2 mt-2.5">
              {m.post_id && (
                <Link to={`/projekt/${m.post_id}`}
                  className="text-xs text-brand-400 hover:underline">
                  Ansehen
                </Link>
              )}
              <button disabled={busy === m.id}
                onClick={() => entscheiden(m.id, "ausblenden")}
                className="ml-auto text-xs px-3 py-1.5 rounded-lg bg-red-500/15 text-red-400 hover:bg-red-500/25 disabled:opacity-40 transition-colors">
                Ausblenden
              </button>
              <button disabled={busy === m.id}
                onClick={() => entscheiden(m.id, "behalten")}
                className="text-xs px-3 py-1.5 rounded-lg bg-ink-700 hover:bg-ink-600 disabled:opacity-40 transition-colors">
                Ist in Ordnung
              </button>
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}
