"""Interner Runner fuer die Vocal-Separation - wird von vocal_separation.py
als Subprocess gestartet (nicht direkt importieren).

Warum nicht einfach `python -m demucs`? Die demucs-CLI (4.0.1, unmaintained)
speichert ihre Stems ueber torchaudio.save, und torchaudio >= 2.9 delegiert
das an das optionale torchcodec-Paket - fehlt es, stirbt demucs erst NACH
der minutenlangen Trennung mit einem ImportError. Dieser Runner wendet das
demucs-Modell direkt an (reines torch, unabhaengig von torchaudio) und
schreibt den Vocal-Stem mit soundfile.

Aufruf:  python -m backend.pipeline._demucs_runner <song> <out_vocals_wav>
Exit 0 = out_vocals_wav wurde geschrieben. Alles andere = Fehler.
"""
from __future__ import annotations

import sys
from pathlib import Path

DEMUCS_MODEL = "htdemucs"


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: _demucs_runner <song> <out_vocals_wav>", file=sys.stderr)
        return 2
    song_path, out_path = Path(sys.argv[1]), Path(sys.argv[2])

    import soundfile as sf
    import torch
    from demucs.apply import apply_model
    from demucs.audio import AudioFile
    from demucs.pretrained import get_model

    model = get_model(DEMUCS_MODEL)
    model.eval()

    # AudioFile dekodiert ueber die ffmpeg-Systembinary (bei uns ohnehin
    # Pflicht) - torchaudio wird also auch beim LADEN nicht gebraucht.
    wav = AudioFile(song_path).read(
        streams=0, samplerate=model.samplerate, channels=model.audio_channels
    )

    # Normalisierung wie in demucs.separate: Modell erwartet standardisiertes
    # Signal, Rueckskalierung danach stellt die Original-Lautstaerke wieder her.
    ref = wav.mean(0)
    wav_norm = (wav - ref.mean()) / ref.std()

    with torch.no_grad():
        sources = apply_model(
            model, wav_norm[None], device="cpu", shifts=1, split=True,
            overlap=0.25, progress=False,
        )[0]
    sources = sources * ref.std() + ref.mean()

    vocals = sources[model.sources.index("vocals")]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(out_path), vocals.cpu().numpy().T, model.samplerate)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
