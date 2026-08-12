"""Waechter gegen versehentlich doppelt definierte Funktionen.

Anlass: beim Anhaengen an db.py ist eine Funktion entstanden, die eine
bestehende gleichen Namens verdeckt hat (list_posts_by_user). Python meldet
das nicht - die zweite Definition gewinnt einfach, und ein voellig anderer
Programmteil faellt mit einem TypeError um. Gefunden hat es erst ein Test
an ganz anderer Stelle.

Statisch und schnell: keine Importe, kein Ausfuehren, nur der Syntaxbaum.
"""
from __future__ import annotations

import ast
from collections import Counter
from pathlib import Path

import pytest

PROJEKT = Path(__file__).resolve().parent.parent
DATEIEN = sorted((PROJEKT / "backend").rglob("*.py"))


@pytest.mark.parametrize("datei", DATEIEN, ids=lambda p: str(p.relative_to(PROJEKT)))
def test_keine_doppelten_definitionen(datei: Path):
    baum = ast.parse(datei.read_text(encoding="utf-8"), filename=str(datei))

    def pruefe(koerper, wo: str):
        namen = [k.name for k in koerper
                 if isinstance(k, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))]
        doppelt = sorted(n for n, anzahl in Counter(namen).items() if anzahl > 1)
        assert not doppelt, (
            f"{datei.relative_to(PROJEKT)}{wo}: doppelt definiert -> {doppelt}. "
            "Die zweite Definition verdeckt die erste; wer die erste aufruft, "
            "bekommt stillschweigend die falsche Funktion.")

    pruefe(baum.body, "")
    for knoten in baum.body:
        if isinstance(knoten, ast.ClassDef):
            pruefe(knoten.body, f" (Klasse {knoten.name})")
