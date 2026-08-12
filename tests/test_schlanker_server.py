"""Beweist, dass der Server OHNE die schweren Analyse-Pakete laeuft.

Der gehostete Server installiert nur `requirements-server.txt` (fastapi,
uvicorn, bcrypt, python-multipart). librosa, numpy, scipy und faster_whisper
sind dort gar nicht vorhanden - demucs laesst sich auf einem schlanken Server
nicht einmal bauen. Wandert irgendwann wieder ein Import dieser Pakete an den
Kopf von backend/main.py, startet der Server online nicht mehr - und das
faellt sonst erst beim Deployment auf. Dieser Test zieht es nach vorne.

Der Test laeuft in einem EIGENEN Interpreter: hier sind die Pakete
installiert und von anderen Tests laengst importiert - nur ein frischer
Prozess mit Import-Sperre beweist wirklich etwas.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

PROJEKT = Path(__file__).resolve().parent.parent

# Erster Teil: die Import-Sperre. Steht getrennt, weil die Gegenprobe unten
# genau diesen Teil allein braucht.
SPERRE = '''
import sys

GESPERRT = {"librosa", "numpy", "scipy", "faster_whisper", "demucs",
            "soundfile", "torch", "gradio"}


class Sperre:
    """Behandelt die schweren Pakete so, als waeren sie nicht installiert -
    genau die Lage auf dem gehosteten Server."""

    def find_spec(self, name, pfad=None, ziel=None):
        if name.split(".")[0] in GESPERRT:
            raise ImportError(f"{name} ist auf dem schlanken Server nicht installiert")
        return None


sys.meta_path.insert(0, Sperre())
'''

# Zweiter Teil: der eigentliche Beweis.
BEWEIS = '''
import io
import wave

from fastapi.testclient import TestClient

from backend import db
from backend.main import app

uebrig = sorted(m for m in sys.modules if m.split(".")[0] in GESPERRT)
assert not uebrig, f"schwere Pakete doch geladen: {uebrig}"

with TestClient(app) as c:
    # Oeffentliche Kataloge muessen auch online antworten.
    for pfad in ("/health", "/auth/config", "/presets", "/styles",
                 "/platforms", "/post-categories"):
        r = c.get(pfad)
        assert r.status_code == 200, f"{pfad} -> {r.status_code} {r.text[:200]}"

    # Netzwerk komplett: registrieren, posten, Hoerprobe hochladen.
    code = db.create_invite_code("schlank-test")
    r = c.post("/auth/register", json={
        "invite_code": code, "email": "schlank@example.com",
        "display_name": "Schlank", "password": "geheim123",
    })
    assert r.status_code == 200, r.text

    puffer = io.BytesIO()
    with wave.open(puffer, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(8000)
        w.writeframes(bytes(2 * 16000))  # 2 Sekunden Stille
    r = c.post("/posts", data={"title": "Suche Refrain", "categories": "refrain"},
               files={"audio": ("probe.wav", puffer.getvalue(), "audio/wav")})
    assert r.status_code == 200, r.text
    post = r.json()
    # Die Dauer kommt von ffprobe - der Beweis, dass die Hoerproben-Pruefung
    # ohne librosa auskommt.
    assert post["has_audio"] is True, post
    assert 1.5 < post["audio_duration_sec"] < 2.5, post
    assert c.get("/feed").status_code == 200

    # Aufraeumen: loescht auch die abgelegte Datei unter projects/posts/.
    assert c.delete(f"/posts/{post['id']}").status_code == 200

print("OK")
'''


def _lauf(tmp_path: Path, quelltext: str, dateiname: str) -> subprocess.CompletedProcess:
    skript = tmp_path / dateiname
    skript.write_text(quelltext, encoding="utf-8")
    umgebung = {**os.environ,
                "PYTHONPATH": str(PROJEKT),
                "HOOKCUT_DB": str(tmp_path / "state.db")}
    return subprocess.run([sys.executable, str(skript)], cwd=PROJEKT,
                          env=umgebung, capture_output=True, text=True)


def test_server_startet_ohne_schwere_pakete(tmp_path):
    ergebnis = _lauf(tmp_path, SPERRE + BEWEIS, "schlanker_start.py")
    assert ergebnis.returncode == 0, (
        "Der schlanke Server startet nicht - vermutlich ist ein Import von "
        "librosa/numpy/scipy/faster_whisper an den Kopf von backend/main.py "
        f"gewandert.\n--- stdout ---\n{ergebnis.stdout}"
        f"\n--- stderr ---\n{ergebnis.stderr}")
    assert "OK" in ergebnis.stdout


def test_sperre_wirkt_wirklich(tmp_path):
    """Gegenprobe - ohne sie waere der Test oben wertlos.

    Ein Test, der immer gruen ist, beweist nichts. Hier wird librosa bei
    aktiver Sperre absichtlich importiert: schlaegt das NICHT fehl, greift
    die Sperre nicht und der Beweis oben ist keiner.
    """
    ergebnis = _lauf(tmp_path, SPERRE + "\nimport librosa\n", "gegenprobe.py")
    assert ergebnis.returncode != 0
    assert "nicht installiert" in ergebnis.stderr
