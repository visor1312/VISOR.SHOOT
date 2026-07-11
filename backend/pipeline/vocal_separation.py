"""Hook-Detector 2.0, Baustein 1: Vocal-Separation via Demucs (Meta, MIT).

Trennt einen Song in Vocal- und Instrumental-Stem. Der Vocal-Stem liefert
der Hook-Erkennung Features, die aus dem Gesamtmix nicht ablesbar sind
(Vocal-Praesenz, Flow-Dichte).

Design-Entscheidungen:
- Aufruf ueber unseren eigenen Runner (_demucs_runner.py) als Subprocess.
  NICHT ueber die demucs-CLI: deren Stem-Speichern laeuft ueber
  torchaudio.save, das ab torchaudio 2.9 das optionale torchcodec-Paket
  verlangt und sonst erst nach der minutenlangen Trennung crasht. Der
  Runner speichert stattdessen mit soundfile.
- Ergebnis-Cache auf Platte: die Trennung dauert auf CPU 1-3 Minuten pro
  Song und laeuft deshalb pro Song nur einmal.
- Demucs ist OPTIONAL: jeder Fehler (Paket fehlt, Modell-Download
  blockiert, Laufzeitfehler) fuehrt zu Rueckgabe None statt Exception.
  Aufrufer behandeln None als "kein Vocal-Stem verfuegbar" und rechnen
  ohne Vocal-Features weiter.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SEPARATION_TIMEOUT_SEC = 30 * 60
_REPO_ROOT = Path(__file__).resolve().parents[2]


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
    song_path = Path(song_path).resolve()
    cached = _cache_path(song_path)
    if cached.exists():
        return cached

    if not is_demucs_available():
        return None

    # Erst in eine .tmp-Datei schreiben und nur bei Erfolg umbenennen -
    # ein abgebrochener Lauf hinterlaesst so nie einen halben Cache.
    tmp_out = cached.with_suffix(".tmp.wav")
    try:
        result = subprocess.run(
            [
                sys.executable, "-m", "backend.pipeline._demucs_runner",
                str(song_path), str(tmp_out),
            ],
            capture_output=True,
            text=True,
            timeout=SEPARATION_TIMEOUT_SEC,
            cwd=_REPO_ROOT,  # damit "backend.pipeline" importierbar ist
        )
        if result.returncode != 0 or not tmp_out.exists():
            return None
        tmp_out.replace(cached)
        return cached
    except (subprocess.TimeoutExpired, OSError):
        return None
    finally:
        tmp_out.unlink(missing_ok=True)
