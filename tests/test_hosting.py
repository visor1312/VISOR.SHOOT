"""Tests fuer das Hybrid-Hosting-Fundament: Config, Health, WAL, Render-Vertrag.

Der Render-Vertrag wird mit direkt angelegten Pack-Items geprueft (die echte
Analyse braucht echte Audio-/Videodateien und laeuft nur beim Nutzer) - so
ist die Agent-Interaktion (pending -> claim -> result) deterministisch testbar.
client/auth_client/second_auth_client aus conftest.py.
"""
from __future__ import annotations

import json
import sqlite3

from backend import config, db


# --- Config (Env-Parsing) -------------------------------------------------

def test_env_bool(monkeypatch):
    monkeypatch.setenv("HOOKCUT_X", "1")
    assert config._env_bool("HOOKCUT_X", False) is True
    monkeypatch.setenv("HOOKCUT_X", "off")
    assert config._env_bool("HOOKCUT_X", True) is False
    monkeypatch.delenv("HOOKCUT_X", raising=False)
    assert config._env_bool("HOOKCUT_X", True) is True


def test_env_list(monkeypatch):
    monkeypatch.setenv("HOOKCUT_Y", "https://a.de, https://b.de ,")
    assert config._env_list("HOOKCUT_Y", []) == ["https://a.de", "https://b.de"]
    monkeypatch.delenv("HOOKCUT_Y", raising=False)
    assert config._env_list("HOOKCUT_Y", ["x"]) == ["x"]


# --- Health + WAL ---------------------------------------------------------

def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"


def test_wal_mode_enabled(tmp_path):
    dbp = tmp_path / "wal.db"
    db.init_db(dbp)
    conn = sqlite3.connect(str(dbp))
    try:
        mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
    finally:
        conn.close()
    assert mode.lower() == "wal"


# --- Render-Job-Vertrag (Agent) -------------------------------------------

def _pending_pack(user_id: str) -> tuple[str, str]:
    """Legt einen Pack mit einem 'pending' Item direkt an. -> (pack_id, item_id)."""
    pack_id = db.create_content_pack("v.mp4", "s.wav", with_subtitles=False, user_id=user_id)
    db.update_content_pack(pack_id, offset_ms=1000.0,
                           hooks_json=json.dumps([{"start_sec": 5.0, "end_sec": 20.0}]))
    item_id = db.create_pack_item(pack_id, idx=0, hook_index=0, style_key="clean",
                                  platform="reel")
    return pack_id, item_id


def test_render_requires_login(client):
    assert client.get("/render/pending").status_code == 401
    assert client.post("/render/x/claim").status_code == 401


def test_render_pending_lists_own_items(auth_client):
    pack_id, item_id = _pending_pack(auth_client.user["id"])
    pending = auth_client.get("/render/pending").json()
    mine = [p for p in pending if p["item_id"] == item_id]
    assert len(mine) == 1
    spec = mine[0]
    assert spec["pack_id"] == pack_id and spec["style"] == "clean"
    assert spec["platform"] == "reel" and spec["offset_ms"] == 1000.0
    assert spec["hook"] == {"start_sec": 5.0, "end_sec": 20.0}


def test_render_claim_then_result_completes_pack(auth_client):
    pack_id, item_id = _pending_pack(auth_client.user["id"])
    # claim: pending -> rendering
    r = auth_client.post(f"/render/{item_id}/claim")
    assert r.status_code == 200 and r.json()["item_id"] == item_id
    # zweites claim scheitert (nicht mehr offen)
    assert auth_client.post(f"/render/{item_id}/claim").status_code == 409
    # result: MP4 hochladen -> Item done, und da es das einzige ist -> Pack done
    up = auth_client.post(f"/render/{item_id}/result",
                          files={"video": ("out.mp4", b"fake-mp4-bytes", "video/mp4")})
    assert up.status_code == 200
    detail = auth_client.get(f"/packs/{pack_id}").json()
    assert detail["status"] == "done"
    assert detail["items"][0]["status"] == "done" and detail["items"][0]["ready"] is True
    # Download klappt jetzt
    assert auth_client.get(f"/packs/{pack_id}/items/0/download").status_code == 200


def test_render_item_ownership(auth_client, second_auth_client):
    _pack_id, item_id = _pending_pack(auth_client.user["id"])
    assert second_auth_client.post(f"/render/{item_id}/claim").status_code == 404
    assert second_auth_client.post(
        f"/render/{item_id}/result",
        files={"video": ("out.mp4", b"x", "video/mp4")}).status_code == 404
    # und taucht nicht in der pending-Liste des anderen Nutzers auf
    assert all(p["item_id"] != item_id for p in second_auth_client.get("/render/pending").json())
