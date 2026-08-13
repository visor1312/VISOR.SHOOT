"""Hochgeladene Dateien sicher auf die Platte schreiben.

EINE Stelle fuer das Deckeln von Uploads. Der Unterschied ist wichtig:

* Innerhalb des lokalen Werkzeugs laedt der Besitzer seine eigenen Rohvideos
  hoch - da ist eine Obergrenze nur im Weg (ein 4K-Take sind schnell 3 GB).
* Alles, was ONLINE erreichbar ist, muss gedeckelt sein. Sonst kann jedes
  angemeldete Konto die gemietete Festplatte vollschreiben, und dann steht
  nicht nur der eine Upload, sondern der ganze Dienst.

Deshalb schreibt save_upload_capped() blockweise und bricht beim
Ueberschreiten sofort ab; die halbe Datei wird weggeraeumt.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import UploadFile

BLOCK_BYTES = 64 * 1024


class UploadTooLarge(Exception):
    """Der Upload hat die erlaubte Groesse gesprengt (-> HTTP 413)."""


def save_upload_capped(upload: UploadFile, dest: Path, max_bytes: int) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    geschrieben = 0
    try:
        with dest.open("wb") as f:
            while True:
                block = upload.file.read(BLOCK_BYTES)
                if not block:
                    break
                geschrieben += len(block)
                if geschrieben > max_bytes:
                    raise UploadTooLarge()
                f.write(block)
    except UploadTooLarge:
        dest.unlink(missing_ok=True)
        raise
    return dest


def mb(max_bytes: int) -> int:
    """Fuer Fehlermeldungen: Bytes als glatte Megabyte-Zahl."""
    return max_bytes // (1024 * 1024)
