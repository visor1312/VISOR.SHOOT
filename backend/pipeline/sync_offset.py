"""Schritt 02: Zeitversatz zwischen Songdatei und extrahiertem Video-Ton berechnen.

Kreuzkorreliert die Lautstaerke-/Onset-Einhuellende (nicht das Rohsignal) von
Songdatei und Video-Ton, um zu bestimmen, an welcher Stelle im Song der
Video-Clip zeitlich liegt.

Die Einhuellende statt des Rohsignals zu nutzen, hat sich beim Testen mit
echtem Handymaterial als noetig erwiesen: Eine per Telefonmikro aufgenommene
Performance (Raumhall, Lautsprecher-/Mikro-Verzerrung) korreliert im
Rohsignal nur schwach mit einer sauber aufgenommenen Songreferenz (Konfidenz
~0.1 trotz korrektem Offset), waehrend die Lautstaerke-Einhuellende (die
Raumhall/Verzerrung weit besser uebersteht) denselben Offset mit deutlich
hoeherer Konfidenz (~0.5-0.8) findet.

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

DEFAULT_CORR_SAMPLE_RATE = 22050
DEFAULT_HOP_LENGTH = 512
LOW_CONFIDENCE_THRESHOLD = 0.2


@dataclass
class SyncResult:
    offset_ms: float
    confidence: float  # normierte Korrelation, 0..1 (grob), niedrig = manuell pruefen


def _load_mono(path: str | Path, sr: int) -> np.ndarray:
    audio, _ = librosa.load(str(path), sr=sr, mono=True)
    return audio.astype(np.float64) - float(np.mean(audio))


def _onset_envelope(audio: np.ndarray, sr: int, hop_length: int) -> np.ndarray:
    env = librosa.onset.onset_strength(y=audio, sr=sr, hop_length=hop_length)
    return env - env.mean()


def compute_offset(
    song_path: str | Path,
    video_audio_path: str | Path,
    corr_sample_rate: int = DEFAULT_CORR_SAMPLE_RATE,
    hop_length: int = DEFAULT_HOP_LENGTH,
) -> SyncResult:
    """Berechnet den Zeitversatz zwischen Songdatei und Video-Ton.

    Funktioniert unabhaengig davon, ob der Song laenger oder kuerzer als der
    Video-Clip ist (voller Song-Upload oder bereits zugeschnittener Ausschnitt).
    """
    song = _load_mono(song_path, corr_sample_rate)
    video_audio = _load_mono(video_audio_path, corr_sample_rate)

    if len(song) == 0 or len(video_audio) == 0:
        raise ValueError("Song- oder Video-Audio ist leer (Stille/keine Tonspur?)")

    song_env = _onset_envelope(song, corr_sample_rate, hop_length)
    video_env = _onset_envelope(video_audio, corr_sample_rate, hop_length)
    frame_rate = corr_sample_rate / hop_length

    corr = correlate(song_env, video_env, mode="full", method="fft")
    lags = correlation_lags(len(song_env), len(video_env), mode="full")

    best_idx = int(np.argmax(np.abs(corr)))
    lag_frames = int(lags[best_idx])

    # Overlappenden Ausschnitt fuer Konfidenzberechnung bestimmen.
    seg_start = max(lag_frames, 0)
    seg_end = min(lag_frames + len(video_env), len(song_env))
    song_seg = song_env[seg_start:seg_end]
    video_seg_start = max(-lag_frames, 0)
    video_seg = video_env[video_seg_start:video_seg_start + len(song_seg)]

    denom = np.linalg.norm(song_seg) * np.linalg.norm(video_seg)
    confidence = float(abs(np.dot(song_seg, video_seg) / denom)) if denom > 0 else 0.0
    confidence = min(confidence, 1.0)

    offset_ms = (lag_frames / frame_rate) * 1000.0
    return SyncResult(offset_ms=offset_ms, confidence=confidence)


def _main() -> None:
    parser = argparse.ArgumentParser(description="Zeitversatz zwischen Song und Video-Ton berechnen")
    parser.add_argument("song_path", help="Pfad zur Songdatei (mp3/wav)")
    parser.add_argument("video_audio_path", help="Pfad zur extrahierten Video-Audiodatei (wav)")
    parser.add_argument("--corr-sample-rate", type=int, default=DEFAULT_CORR_SAMPLE_RATE)
    parser.add_argument("--hop-length", type=int, default=DEFAULT_HOP_LENGTH)
    args = parser.parse_args()

    result = compute_offset(args.song_path, args.video_audio_path, args.corr_sample_rate, args.hop_length)
    print(f"offset_ms={result.offset_ms:.1f} confidence={result.confidence:.3f}")
    if result.confidence < LOW_CONFIDENCE_THRESHOLD:
        print("WARNUNG: niedrige Konfidenz - Ergebnis manuell pruefen (z.B. Video ohne brauchbaren Ton).")


if __name__ == "__main__":
    _main()
