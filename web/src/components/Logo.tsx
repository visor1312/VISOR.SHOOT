/** Die selfsign-Marke - an EINER Stelle, damit ein Austausch ueberall wirkt.
 *
 *  Die Bildmarke kommt bewusst als Datei aus web/public/selfsign-mark.svg und
 *  nicht als eingebettetes SVG im Code: so laesst sie sich gegen die
 *  Originaldatei tauschen, ohne dass jemand TypeScript anfassen muss.
 *  Dateiname beibehalten, fertig.
 */

/** Nur die Bildmarke (Signalbalken + Unterschrift). */
export function Mark({ size = 36, className = "" }: { size?: number; className?: string }) {
  return (
    <img
      src="/selfsign-mark.svg"
      alt=""
      aria-hidden="true"
      // Das Seitenverhaeltnis der Marke ist rund 2:1 - die Hoehe gibt den Ton
      // an, die Breite ergibt sich. Kein feste Breite, sonst verzerrt ein
      // Austausch gegen die Originaldatei das Bild.
      style={{ height: size, width: "auto" }}
      className={className}
    />
  );
}

/** Marke + Schriftzug nebeneinander (Seitenleiste, Kopfzeilen). */
export function LogoZeile({ size = 30 }: { size?: number }) {
  return (
    <span className="flex items-center gap-2.5">
      <Mark size={size} />
      <span className="font-semibold tracking-tight" style={{ fontSize: size * 0.62 }}>
        selfsign
      </span>
    </span>
  );
}

/** Marke ueber Schriftzug, mittig - Anmeldung und Ladebildschirm. */
export function LogoBlock({ size = 64, claim = true }: { size?: number; claim?: boolean }) {
  return (
    <div className="flex flex-col items-center gap-3">
      <Mark size={size} />
      <div className="flex flex-col items-center gap-1.5">
        <span className="font-semibold tracking-tight leading-none"
          style={{ fontSize: size * 0.58 }}>
          selfsign
        </span>
        {claim && (
          <span className="flex items-center gap-2 text-muted"
            style={{ fontSize: Math.max(11, size * 0.19) }}>
            <span className="h-px w-5 bg-brand-500" aria-hidden="true" />
            Sign yourself.
            <span className="h-px w-5 bg-brand-500" aria-hidden="true" />
          </span>
        )}
      </div>
    </div>
  );
}
