"""Tests fuer die Lyrics-Wort-Ausrichtung (exakte Untertitel)."""
from __future__ import annotations

from backend.pipeline.lyrics_align import align_lyrics_to_words
from backend.pipeline.transcribe import Word


def _w(text: str, start: float, end: float) -> Word:
    return Word(word=text, start=start, end=end)


def test_exact_match_inherits_timestamps():
    rec = [_w("real", 1.0, 1.3), _w("talk", 1.3, 1.6), _w("kein", 1.6, 1.9), _w("cap", 1.9, 2.2)]
    out = align_lyrics_to_words("Real Talk kein Cap", rec)
    assert [w.word for w in out] == ["Real", "Talk", "kein", "Cap"]
    assert out[0].start == 1.0 and out[3].end == 2.2


def test_misheard_words_get_replaced_but_keep_time_span():
    # Whisper hat sich in der Mitte verhoert ("bein kabb" statt "kein Cap").
    rec = [_w("real", 1.0, 1.3), _w("bein", 1.6, 1.9), _w("kabb", 1.9, 2.2), _w("facts", 2.5, 2.8)]
    out = align_lyrics_to_words("real kein Cap facts", rec)
    assert [w.word for w in out] == ["real", "kein", "Cap", "facts"]
    # Ersetzte Woerter liegen in der verhoerten Zeitspanne.
    assert out[1].start >= 1.55 and out[2].end <= 2.35
    assert out[3].start == 2.5


def test_swallowed_word_interpolated_between_anchors():
    # "ganz" wurde verschluckt.
    rec = [_w("wir", 0.5, 0.8), _w("unten", 1.4, 1.8)]
    out = align_lyrics_to_words("wir ganz unten", [
        _w("wir", 0.5, 0.8), _w("x", 0.9, 1.0), _w("unten", 1.4, 1.8), _w("y", 2.0, 2.1)][:3] or rec)
    words = [w.word for w in out]
    assert words == ["wir", "ganz", "unten"]
    # Monotonie
    for a, b in zip(out, out[1:]):
        assert b.start >= a.start


def test_hallucinated_words_are_dropped():
    # Whisper hat ein Wort dazuerfunden ("uh") - darf nicht auftauchen.
    rec = [_w("real", 1.0, 1.3), _w("uh", 1.3, 1.5), _w("talk", 1.5, 1.8)]
    out = align_lyrics_to_words("real talk", rec)
    assert [w.word for w in out] == ["real", "talk"]


def test_monotonic_and_min_duration():
    rec = [_w("a", 1.0, 1.1), _w("b", 1.0, 1.05), _w("c", 0.9, 1.0)]
    out = align_lyrics_to_words("a b c", rec)
    t = 0.0
    for w in out:
        assert w.start >= t
        assert w.end - w.start >= 0.1
        t = w.end


def test_sparse_recognition_spreads_evenly():
    rec = [_w("x", 2.0, 2.2), _w("y", 8.0, 8.2)]
    out = align_lyrics_to_words("eins zwei drei vier", rec)
    assert len(out) == 4
    assert out[0].start >= 2.0 and out[-1].end <= 8.2 + 0.5


def test_empty_inputs():
    assert align_lyrics_to_words("", [_w("a", 0, 1)]) == []
    assert align_lyrics_to_words("text", []) == []
