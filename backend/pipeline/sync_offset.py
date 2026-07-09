"""Schritt 02: Zeitversatz zwischen Songdatei und extrahiertem Video-Ton berechnen.

Nutzt FFT-Cross-Correlation (scipy.signal.correlate) zwischen der (ggf. langen)
Songdatei und dem kurzen Video-Ton, um zu bestimmen, an welcher Stelle im Song
der Video-Clip zeitlich liegt.

Konvention (wichtig fuer render_sync.py):
  offset_ms > 0  ->  Video-Start (t=0) entspricht `offset_ms` ms *innerhalb* des Songs.
                      Der Song muss beim Rendern um offset_ms nach vorne geschnitten
                      werden (z.B. ffmpeg -ss auf den Song-Input).
  offset_ms < 0  ->  Der Song hat beim Video-Start noch nicht begonnen (der Nutzer
                      hat die Kamera vor dem Playback-Einsatz gestartet). Der Song
                      muss beim Rendern um |offset_ms| verzoegert werden (Stille
                      voranstellen).
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import librosa
import numpy as np
from scipy.signal import correlate, correlation_lags

DEFAULT_CORR_SAMPLE_RATE = 8000


@dataclass
class SyncResult:
    offset_ms: float
    confidence: float  # normierte Korrelation, 0..1 (grob), niedrig = manuell pruefen


def _load_mono(path: str | Path, sr: int) -> np.ndarray:
    audio, _ = librosa.load(str(path), sr=sr, mono=True)
    return audio.astype(np.float64) - float(np.mean(audio))


def compute_offset(
    song_path: str | Path,
    video_audio_path: str | Path,
    corr_sample_rate: int = DEFAULT_CORR_SAMPLE_RATE,
) -> SyncResult:
    """Berechnet den Zeitversatz zwischen Songdatei und Video-Ton.

    Funktioniert unabhaengig davon, ob der Song laenger oder kuerzer als der
    Video-Clip ist (voller Song-Upload oder bereits zugeschnittener Ausschnitt).
    """
    song = _load_mono(song_path, corr_sample_rate)
    video_audio = _load_mono(video_audio_path, corr_sample_rate)

    if len(song) == 0 or len(video_audio) == 0:
        raise ValueError("Song- oder Video-Audio ist leer (Stille/keine Tonspur?)")

    corr = correlate(song, video_audio, mode="full", method="fft")
    lags = correlation_lags(len(song), len(video_audio), mode="full")

    best_idx = int(np.argmax(np.abs(corr)))
    lag_samples = int(lags[best_idx])

    # Overlappenden Ausschnitt fuer Konfidenzberechnung bestimmen.
    seg_start = max(lag_samples, 0)
    seg_end = min(lag_samples + len(video_audio), len(song))
    song_seg = song[seg_start:seg_end]
    video_seg_start = max(-lag_samples, 0)
    video_seg = video_audio[video_seg_start:video_seg_start + len(song_seg)]

    denom = np.linalg.norm(song_seg) * np.linalg.norm(video_seg)
    confidence = float(abs(np.dot(song_seg, video_seg) / denom)) if denom > 0 else 0.0
    confidence = min(confidence, 1.0)

    offset_ms = (lag_samples / corr_sample_rate) * 1000.0
    return SyncResult(offset_ms=offset_ms, confidence=confidence)


def _main() -> None:
    parser = argparse.ArgumentParser(description="Zeitversatz zwischen Song und Video-Ton berechnen")
    parser.add_argument("song_path", help="Pfad zur Songdatei (mp3/wav)")
    parser.add_argument("video_audio_path", help="Pfad zur extrahierten Video-Audiodatei (wav)")
    parser.add_argument("--corr-sample-rate", type=int, default=DEFAULT_CORR_SAMPLE_RATE)
    args = parser.parse_args()

    result = compute_offset(args.song_path, args.video_audio_path, args.corr_sample_rate)
    print(f"offset_ms={result.offset_ms:.1f} confidence={result.confidence:.3f}")
    if result.confidence < 0.15:
        print("WARNUNG: niedrige Konfidenz - Ergebnis manuell pruefen (z.B. Video ohne brauchbaren Ton).")


if __name__ == "__main__":
    _main()
