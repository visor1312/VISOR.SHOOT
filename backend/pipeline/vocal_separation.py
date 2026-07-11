"""Hook-Detector 2.0, Baustein 1: Vocal-Separation via Demucs (Meta, MIT).

Trennt einen Song in Vocal- und Instrumental-Stem. Der Vocal-Stem liefert
der Hook-Erkennung Features, die aus dem Gesamtmix nicht ablesbar sind
(Vocal-Praesenz, Flow-Dichte).

Design-Entscheidungen:
- Aufruf ueber die Demucs-CLI als Subprocess (wie unsere ffmpeg-Aufrufe),
  nicht ueber interne Python-APIs - die CLI ist die stabile Schnittstelle
  des Pakets (demucs.api existiert erst ab 4.1, nicht auf PyPI).
- Ergebnis-Cache auf Platte: die Trennung dauert auf CPU 1-3 Minuten pro
  Song und laeuft deshalb pro Song nur einmal.
- Demucs ist OPTIONAL: jeder Fehler (Paket fehlt, Modell-Download
  blockiert, Laufzeitfehler) fuehrt zu Rueckgabe None statt Exception.
  Aufrufer behandeln None als "kein Vocal-Stem verfuegbar" und rechnen
  ohne Vocal-Features weiter.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

DEMUCS_MODEL = "htdemucs"
SEPARATION_TIMEOUT_SEC = 30 * 60


def is_demucs_available() -> bool:
    """Prueft nur, ob das demucs-Paket importierbar ist (nicht, ob der
    Modell-Download funktioniert - das zeigt sich erst beim ersten Lauf)."""
    try:
        import demucs  # noqa: F401
        return True
    except ImportError:
        return False


def _cache_path(song_path: Path) -> Path:
    return song_path.parent / f"{song_path.stem}.vocals.wav"


def separate_vocals(song_path: str | Path) -> Path | None:
    """Liefert den Pfad zum Vocal-Stem-WAV des Songs, oder None.

    None bedeutet: Vocal-Separation nicht verfuegbar (demucs fehlt,
    Modell-Download gescheitert o.ae.) - der Aufrufer soll dann ohne
    Vocal-Features weiterrechnen.
    """
    song_path = Path(song_path)
    cached = _cache_path(song_path)
    if cached.exists():
        return cached

    if not is_demucs_available():
        return None

    out_root = song_path.parent / "_demucs_tmp"
    try:
        result = subprocess.run(
            [
                sys.executable, "-m", "demucs",
                "--two-stems=vocals",
                "-n", DEMUCS_MODEL,
                "-d", "cpu",
                "-o", str(out_root),
                str(song_path),
            ],
            capture_output=True,
            text=True,
            timeout=SEPARATION_TIMEOUT_SEC,
        )
        if result.returncode != 0:
            return None
        # Demucs schreibt nach <out>/<modell>/<trackname>/vocals.wav
        vocals = out_root / DEMUCS_MODEL / song_path.stem / "vocals.wav"
        if not vocals.exists():
            return None
        shutil.move(str(vocals), str(cached))
        return cached
    except (subprocess.TimeoutExpired, OSError):
        return None
    finally:
        shutil.rmtree(out_root, ignore_errors=True)
