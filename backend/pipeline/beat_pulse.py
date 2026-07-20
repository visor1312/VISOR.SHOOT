"""Beat-Pulse fuer beat-synchrone Effekte im FreeCut-Render.

Liefert die erkannten Taktschlaege eines Songs als sparsame Puls-Liste
(Frame relativ zum Clip-Start + Amplitude 0..1), zugeschnitten auf das
Render-Fenster des Reels. Das ist exakt das Format, das FreeCuts
AudioPulse-Modulation erwartet (editor/src/types/effects.ts:
AudioPulseBeat {frame, amplitude}) - der Effekt selbst wird dann zur
Render-Zeit prozedural ausgewertet, keine gebackenen Keyframes noetig.

Die Amplitude kommt aus der Onset-Staerke am jeweiligen Taktschlag
(librosa.onset.onset_strength), normalisiert auf das 95. Perzentil der
Einhuellenden - laute Schlaege pulsieren staerker als leise.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import librosa
import numpy as np

DEFAULT_SAMPLE_RATE = 22050

# Puls-Envelope im Editor dauert ~0.36s (fps * 0.36 Frames). Liegen Beats
# dichter als das + eine kleine Ruhepause, ueberlappen sich die Pulse und der
# Effekt flackert durchgehend statt zu "zucken". Passiert bei Rap schnell,
# weil librosa auf Hi-Hats gern das DOPPELTE Tempo erkennt (Oktavfehler) -
# dann wird automatisch nur jeder 2./3./... Beat genommen.
MIN_PULSE_SPACING_SEC = 0.42


@dataclass
class BeatPulse:
    frame: int        # relativ zum Clip-Start, in Projekt-FPS
    amplitude: float  # 0..1


def beat_pulses_for_window(
    song_path: str | Path,
    win_start_sec: float,
    win_end_sec: float,
    fps: float,
    *,
    stride: int = 1,
    sample_rate: int = DEFAULT_SAMPLE_RATE,
) -> list[BeatPulse]:
    """Taktschlaege im Song-Fenster [win_start_sec, win_end_sec) als Pulse.

    stride=2/4 nimmt nur jeden 2./4. Taktschlag (gezaehlt ab Fensterbeginn),
    falls ein Effekt auf jedem Beat zu hektisch wirkt. Unabhaengig davon wird
    automatisch ausgeduennt, wenn die erkannten Beats dichter liegen als
    MIN_PULSE_SPACING_SEC (Doppeltempo-Oktavfehler bei Rap/Hi-Hats).
    """
    y, sr = librosa.load(str(song_path), sr=sample_rate, mono=True)
    onset_env = librosa.onset.onset_strength(y=y, sr=sr)
    _tempo, beat_frames = librosa.beat.beat_track(onset_envelope=onset_env, sr=sr)
    if len(beat_frames) == 0:
        return []

    beat_times = librosa.frames_to_time(beat_frames, sr=sr)
    strengths = onset_env[np.clip(beat_frames, 0, len(onset_env) - 1)]
    ref = float(np.percentile(onset_env, 95))
    if ref <= 0:
        ref = 1.0

    in_window = [(float(t), float(s)) for t, s in zip(beat_times, strengths)
                 if win_start_sec <= t < win_end_sec]
    if not in_window:
        return []

    # Auto-Stride: erkannten Beat-Abstand messen und so ausduennen, dass
    # zwischen zwei Pulsen mindestens MIN_PULSE_SPACING_SEC liegt.
    stride = max(1, int(stride))
    if len(in_window) >= 2:
        median_interval = float(np.median(np.diff([t for t, _ in in_window])))
        if median_interval > 0:
            auto = int(np.ceil(MIN_PULSE_SPACING_SEC / median_interval))
            stride = max(stride, auto)

    pulses: list[BeatPulse] = []
    seen_frames: set[int] = set()
    for i, (t, s) in enumerate(in_window):
        if i % stride != 0:
            continue
        frame = round((t - win_start_sec) * fps)
        if frame in seen_frames:
            continue
        seen_frames.add(frame)
        # 0.35 Sockel: auch leise Beats sollen sichtbar pulsieren, die
        # Onset-Staerke moduliert nur die Spitze.
        amplitude = float(np.clip(0.35 + 0.65 * (s / ref), 0.0, 1.0))
        pulses.append(BeatPulse(frame=frame, amplitude=amplitude))
    return pulses


def _main() -> None:
    import argparse
    import json
    from dataclasses import asdict

    p = argparse.ArgumentParser(description="Beat-Pulse fuers Render-Fenster berechnen")
    p.add_argument("song")
    p.add_argument("--start", type=float, default=0.0)
    p.add_argument("--end", type=float, required=True)
    p.add_argument("--fps", type=float, default=30.0)
    p.add_argument("--stride", type=int, default=1)
    args = p.parse_args()
    pulses = beat_pulses_for_window(args.song, args.start, args.end, args.fps, stride=args.stride)
    print(json.dumps([asdict(x) for x in pulses], indent=2))


if __name__ == "__main__":
    _main()
