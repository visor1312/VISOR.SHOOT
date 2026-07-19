"""Schritt 04 (Phase 2): Deutsche Transkription mit Wort-Zeitstempeln.

Nutzt faster-whisper (CTranslate2). Laeuft komplett lokal/offline nach dem
ersten Modell-Download - kein Cloud-Zwang.

Wichtig: Wird auf der bereits SYNCHRONISIERTEN Output-Audiospur aufgerufen
(nicht auf der rohen Songdatei), damit die zurueckgegebenen Zeitstempel
direkt im Zeitrahmen des fertigen Videos liegen und keine zusaetzliche
Offset-Verrechnung noetig ist.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from functools import lru_cache
from pathlib import Path

from faster_whisper import WhisperModel

DEFAULT_MODEL_SIZE = "large-v3"
MODEL_SIZES = ("tiny", "base", "small", "medium", "large-v3")


@dataclass
class Word:
    word: str
    start: float  # Sekunden, relativ zum Anfang der uebergebenen Audiodatei
    end: float


@lru_cache(maxsize=4)
def _get_model(model_size: str, device: str, compute_type: str) -> WhisperModel:
    return WhisperModel(model_size, device=device, compute_type=compute_type)


def transcribe(
    audio_path: str | Path,
    language: str = "de",
    model_size: str = DEFAULT_MODEL_SIZE,
    device: str = "cpu",
    compute_type: str = "int8",
) -> list[Word]:
    """Transkribiert eine Audio-/Videodatei mit Wort-Zeitstempeln.

    `language="de"` erzwingt Deutsch (kein Auto-Detect noetig/gewuenscht -
    siehe Anforderung). Fuer teils englische Songtexte kann `language`
    trotzdem auf "en" gesetzt werden.
    """
    model = _get_model(model_size, device, compute_type)
    segments, _info = model.transcribe(
        str(audio_path), language=language, word_timestamps=True, vad_filter=True,
        # Genauigkeits-Feintuning fuer Songtexte:
        # - beam_size 5: gruendlichere Suche als das Default-Greedy
        # - condition_on_previous_text False: verhindert, dass sich ein Fehler
        #   (oder Wiederholungs-Loops bei Musik) durch den Text fortpflanzt
        beam_size=5,
        condition_on_previous_text=False,
    )

    words: list[Word] = []
    for segment in segments:
        if not segment.words:
            continue
        for w in segment.words:
            text = w.word.strip()
            if text:
                words.append(Word(word=text, start=w.start, end=w.end))
    return words


def _main() -> None:
    parser = argparse.ArgumentParser(description="Deutsche Transkription mit Wort-Zeitstempeln")
    parser.add_argument("audio_path")
    parser.add_argument("--language", default="de")
    parser.add_argument("--model-size", default=DEFAULT_MODEL_SIZE, choices=MODEL_SIZES)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--compute-type", default="int8")
    parser.add_argument("--json", action="store_true", help="Ausgabe als JSON statt Tabelle")
    args = parser.parse_args()

    words = transcribe(args.audio_path, args.language, args.model_size, args.device, args.compute_type)
    if args.json:
        print(json.dumps([asdict(w) for w in words], ensure_ascii=False, indent=2))
    else:
        for w in words:
            print(f"{w.start:7.2f} - {w.end:7.2f}  {w.word}")


if __name__ == "__main__":
    _main()
