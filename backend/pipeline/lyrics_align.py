"""Exakte Untertitel: richtet den BEKANNTEN Songtext an der Whisper-Erkennung aus.

Idee (CapCut-Ansatz): Der Nutzer hat den Text selbst geschrieben - die Woerter
stehen also fest. Whisper liefert nur noch die Zeitstempel. Wir alignieren die
Lyrics-Woerter gegen die erkannten Woerter (SequenceMatcher auf normalisierten
Tokens):

- Uebereinstimmende Woerter erben den erkannten Zeitstempel 1:1.
- Ersetzte Bloecke (Whisper hat sich verhoert) verteilen die erkannte Zeitspanne
  proportional auf die wahren Lyrics-Woerter.
- Eingefuegte Lyrics-Woerter (Whisper hat etwas verschluckt) werden linear
  zwischen den Nachbar-Ankern interpoliert.

Ergebnis: Angezeigt wird IMMER exakt der Nutzertext; nur das Timing kommt aus
der Erkennung. Rein stdlib (difflib), keine neue Abhaengigkeit.
"""
from __future__ import annotations

import re
from difflib import SequenceMatcher

from backend.pipeline.transcribe import Word

_MIN_WORD_DUR = 0.12  # Sekunden - untere Schranke, damit kein Wort "0 lang" ist


def _norm(token: str) -> str:
    """Vergleichsform: klein, nur Buchstaben/Ziffern (Umlaute bleiben)."""
    return re.sub(r"[^\w]", "", token.lower(), flags=re.UNICODE)


def _tokenize_lyrics(text: str) -> list[str]:
    return [t for t in text.split() if _norm(t)]


def _spread(tokens: list[str], start: float, end: float) -> list[Word]:
    """Verteilt Woerter proportional zur Zeichenlaenge auf [start, end]."""
    if not tokens:
        return []
    end = max(end, start + _MIN_WORD_DUR * len(tokens))
    weights = [max(1, len(_norm(t))) for t in tokens]
    total = sum(weights)
    out: list[Word] = []
    t = start
    for tok, w in zip(tokens, weights):
        dur = (end - start) * w / total
        out.append(Word(word=tok, start=round(t, 3), end=round(t + dur, 3)))
        t += dur
    return out


def align_lyrics_to_words(lyrics_text: str, recognized: list[Word]) -> list[Word]:
    """Mappt die Lyrics-Woerter auf die Zeitstempel der Erkennung.

    Faellt bei zu duenner Erkennung (<3 Woerter) auf gleichmaessige Verteilung
    ueber die erkannte Zeitspanne zurueck; ohne jede Erkennung -> leere Liste
    (Aufrufer nutzt dann die reine Erkennung bzw. keine Untertitel).
    """
    tokens = _tokenize_lyrics(lyrics_text)
    if not tokens or not recognized:
        return []
    if len(recognized) < 3:
        return _spread(tokens, recognized[0].start, recognized[-1].end)

    a = [_norm(t) for t in tokens]           # Lyrics (Wahrheit)
    b = [_norm(w.word) for w in recognized]  # Erkennung (Timing)

    out: list[Word] = []
    pending: list[str] = []          # Lyrics-Woerter ohne direkten Anker
    pending_time: tuple[float, float] | None = None  # Zeitspanne ersetzter Bloecke
    last_end: float | None = None

    def flush(next_start: float | None) -> None:
        """Verteilt aufgestaute Woerter zwischen letztem Anker und next_start."""
        nonlocal pending, pending_time, last_end
        if not pending:
            pending_time = None
            return
        if pending_time is not None:
            s, e = pending_time
        else:
            s = last_end if last_end is not None else (
                next_start - _MIN_WORD_DUR * len(pending) if next_start is not None else 0.0)
            e = next_start if next_start is not None else s + _MIN_WORD_DUR * len(pending)
        s = max(0.0, s)
        out.extend(_spread(pending, s, max(e, s)))
        last_end = out[-1].end
        pending = []
        pending_time = None

    for tag, i1, i2, j1, j2 in SequenceMatcher(a=a, b=b, autojunk=False).get_opcodes():
        if tag == "equal":
            flush(recognized[j1].start)
            for k in range(i2 - i1):
                r = recognized[j1 + k]
                out.append(Word(word=tokens[i1 + k], start=r.start, end=r.end))
            last_end = recognized[j2 - 1].end
        elif tag == "replace":
            pending.extend(tokens[i1:i2])
            span = (recognized[j1].start, recognized[j2 - 1].end)
            pending_time = (min(pending_time[0], span[0]), max(pending_time[1], span[1])) \
                if pending_time else span
        elif tag == "delete":  # Lyrics-Woerter, die Whisper verschluckt hat
            pending.extend(tokens[i1:i2])
        # tag == "insert": Whisper-Halluzination -> ignorieren (kein Lyrics-Wort)

    flush(None)

    # Monotonie absichern (keine rueckwaerts laufenden Zeiten).
    t = 0.0
    fixed: list[Word] = []
    for w in out:
        s = max(w.start, t)
        e = max(w.end, s + _MIN_WORD_DUR)
        fixed.append(Word(word=w.word, start=round(s, 3), end=round(e, 3)))
        t = e
    return fixed
