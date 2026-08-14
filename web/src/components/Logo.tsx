import { useState } from "react";

/** Die selfsign-Marke - an EINER Stelle, damit ein Austausch ueberall wirkt.
 *
 *  Die Grafiken kommen bewusst als Dateien aus web/public/ und nicht als
 *  eingebettetes SVG im Quelltext: so lassen sie sich gegen die Originale
 *  tauschen, ohne dass jemand TypeScript anfassen muss. Dateiname beibehalten,
 *  Seite neu laden, fertig. Dafuer gibt es logo-einsetzen.bat.
 *
 *  Drei Dateien, alle optional ausser der ersten:
 *
 *    selfsign-mark.svg       nur die Bildmarke (Balken + Unterschrift)
 *    selfsign-lockup-h.svg   Bildmarke UND Schriftzug nebeneinander
 *    selfsign-lockup-v.svg   Bildmarke UEBER Schriftzug
 *
 *  Liegt eine Lockup-Datei da, wird sie benutzt - dann kommt auch der
 *  Schriftzug im Original-Font. Fehlt sie, setzt die Oberflaeche die
 *  Bildmarke mit "selfsign" in der System-Schrift zusammen. Das ist nah
 *  dran, aber nicht dasselbe; deshalb ist die Lockup-Datei der bessere Weg.
 */

/** Bild, das sich stillschweigend zurueckzieht, wenn es die Datei nicht gibt.
 *  Ohne das haette eine fehlende Lockup-Datei ein kaputtes Bild-Symbol
 *  hinterlassen. */
function BildOderNichts(
  { src, hoehe, onFehler }: { src: string; hoehe: number; onFehler: () => void },
) {
  return (
    <img src={src} alt="selfsign" style={{ height: hoehe, width: "auto" }}
      onError={onFehler} />
  );
}

/** Nur die Bildmarke (Signalbalken + Unterschrift). */
export function Mark({ size = 36, className = "" }: { size?: number; className?: string }) {
  return (
    <img
      src="/selfsign-mark.svg"
      alt=""
      aria-hidden="true"
      // Das Seitenverhaeltnis gibt die Datei vor - hier nur die Hoehe setzen,
      // sonst verzerrt ein Austausch gegen das Original das Bild.
      style={{ height: size, width: "auto" }}
      className={className}
    />
  );
}

/** Marke + Schriftzug nebeneinander (Seitenleiste, Kopfzeilen). */
export function LogoZeile({ size = 30 }: { size?: number }) {
  const [lockupFehlt, setLockupFehlt] = useState(false);
  if (!lockupFehlt) {
    return (
      <BildOderNichts src="/selfsign-lockup-h.svg" hoehe={size * 1.15}
        onFehler={() => setLockupFehlt(true)} />
    );
  }
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
  const [lockupFehlt, setLockupFehlt] = useState(false);
  return (
    <div className="flex flex-col items-center gap-3">
      {!lockupFehlt ? (
        <BildOderNichts src="/selfsign-lockup-v.svg" hoehe={size * 2.1}
          onFehler={() => setLockupFehlt(true)} />
      ) : (
        <>
          <Mark size={size} />
          <span className="font-semibold tracking-tight leading-none"
            style={{ fontSize: size * 0.58 }}>
            selfsign
          </span>
        </>
      )}
      {claim && (
        <span className="flex items-center gap-2 text-muted"
          style={{ fontSize: Math.max(11, size * 0.19) }}>
          <span className="h-px w-5 bg-brand-500" aria-hidden="true" />
          Sign yourself.
          <span className="h-px w-5 bg-brand-500" aria-hidden="true" />
        </span>
      )}
    </div>
  );
}
