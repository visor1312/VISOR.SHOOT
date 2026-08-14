import { useEffect, useState } from "react";
import { Loader2, LogIn, Ticket, UserPlus } from "lucide-react";
import { getAuthConfig, login, register, type User } from "../api";
import Footer from "./Footer";
import { LogoBlock } from "./Logo";

type Mode = "login" | "register";

/** Vollbild-Login/Registrierung im selfsign-Look. Ob ein Einladungscode noetig
 * ist, sagt der Server (/auth/config): das lokale Werkzeug verlangt einen,
 * die offene Plattform nicht. */
export default function AuthScreen({ onAuthed }: { onAuthed: (user: User) => void }) {
  const [mode, setMode] = useState<Mode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [inviteCode, setInviteCode] = useState("");
  const [inviteRequired, setInviteRequired] = useState(true);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  // Bis die Antwort da ist, bleibt es beim strengeren Fall (Code noetig) -
  // so wird nie faelschlich ein Feld ausgeblendet, das der Server braucht.
  useEffect(() => {
    let cancelled = false;
    getAuthConfig()
      .then((c) => !cancelled && setInviteRequired(c.invite_required))
      .catch(() => { /* Standard beibehalten */ });
    return () => { cancelled = true; };
  }, []);

  const canSubmit = mode === "login"
    ? email.trim() !== "" && password !== ""
    : email.trim() !== "" && password !== "" && displayName.trim() !== ""
      && (!inviteRequired || inviteCode.trim() !== "");

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!canSubmit || busy) return;
    setBusy(true);
    setErr("");
    try {
      const user = mode === "login"
        ? await login(email, password)
        : await register(inviteCode, email, displayName, password);
      onAuthed(user);
    } catch (ex) {
      setErr(ex instanceof Error ? ex.message : String(ex));
      setBusy(false);
    }
  }

  function switchMode(next: Mode) {
    setMode(next);
    setErr("");
  }

  return (
    <div className="min-h-screen bg-ink-950 text-white flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Der erste Eindruck: Marke gross, mit Claim. */}
        <div className="mb-7">
          <LogoBlock size={68} />
        </div>

        <div className="bg-ink-850 border border-ink-700 rounded-2xl p-8">
          <h1 className="text-xl font-semibold">
            {mode === "login" ? "Anmelden" : "Konto erstellen"}
          </h1>
          <p className="text-sm text-muted mt-1">
            {mode === "login"
              ? "Willkommen zurück – melde dich mit deinem Konto an."
              : inviteRequired
                ? "Registrierung nur mit Einladungscode."
                : "Kostenlos für Musiker – in unter einer Minute startklar."}
          </p>

          {err && (
            <div className="mt-4 bg-red-500/10 border border-red-500/40 text-red-400 text-sm rounded-xl px-4 py-3">
              {err}
            </div>
          )}

          <form onSubmit={submit} className="mt-5 space-y-4">
            {mode === "register" && (
              <>
                {inviteRequired && (
                  <Field label="Einladungscode">
                    <div className="relative">
                      <Ticket size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
                      <input value={inviteCode} onChange={(e) => setInviteCode(e.target.value)}
                        placeholder="Code aus selfsign-einladung.bat" autoComplete="off"
                        className="w-full text-sm bg-ink-800 border border-ink-700 focus:border-brand-500 rounded-xl pl-9 pr-3 py-2.5 outline-none" />
                    </div>
                  </Field>
                )}
                <Field label="Anzeigename">
                  <input value={displayName} onChange={(e) => setDisplayName(e.target.value)}
                    placeholder="z.B. YngLyric" autoComplete="nickname"
                    className="w-full text-sm bg-ink-800 border border-ink-700 focus:border-brand-500 rounded-xl px-3 py-2.5 outline-none" />
                </Field>
              </>
            )}
            <Field label="E-Mail">
              <input type="email" value={email} onChange={(e) => setEmail(e.target.value)}
                placeholder="du@beispiel.de" autoComplete="email"
                className="w-full text-sm bg-ink-800 border border-ink-700 focus:border-brand-500 rounded-xl px-3 py-2.5 outline-none" />
            </Field>
            <Field label="Passwort">
              <input type="password" value={password} onChange={(e) => setPassword(e.target.value)}
                placeholder={mode === "register" ? "mind. 8 Zeichen" : "••••••••"}
                autoComplete={mode === "register" ? "new-password" : "current-password"}
                className="w-full text-sm bg-ink-800 border border-ink-700 focus:border-brand-500 rounded-xl px-3 py-2.5 outline-none" />
            </Field>

            <button type="submit" disabled={!canSubmit || busy}
              className="w-full flex items-center justify-center gap-2 bg-brand-500 hover:bg-brand-600 disabled:opacity-40 text-ink-950 font-semibold py-3 rounded-xl transition-colors">
              {busy ? <Loader2 size={18} className="animate-spin" />
                : mode === "login" ? <LogIn size={18} /> : <UserPlus size={18} />}
              {mode === "login" ? "Anmelden" : "Registrieren"}
            </button>
          </form>

          <div className="mt-5 text-center text-sm text-muted">
            {mode === "login" ? (
              <>
                Noch keinen Zugang?{" "}
                <button onClick={() => switchMode("register")}
                  className="text-brand-400 hover:text-brand-500 font-medium">
                  {inviteRequired ? "Mit Einladungscode registrieren" : "Kostenlos registrieren"}
                </button>
              </>
            ) : (
              <>
                Schon registriert?{" "}
                <button onClick={() => switchMode("login")}
                  className="text-brand-400 hover:text-brand-500 font-medium">
                  Anmelden
                </button>
              </>
            )}
          </div>
        </div>

        <p className="text-center text-xs text-ink-600 mt-4">
          Passwort vergessen? Am selfsign-Rechner „selfsign-passwort-reset.bat" doppelklicken.
        </p>

        {/* Impressum und Datenschutz muessen auch OHNE Konto erreichbar sein -
            wer hier steht, ist noch kein Mitglied. */}
        <Footer />
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="text-sm text-muted">{label}</span>
      <div className="mt-1.5">{children}</div>
    </label>
  );
}
