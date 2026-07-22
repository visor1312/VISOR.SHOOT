"""Tests fuer den Wochen-Content / Content-Pack-Generator.

Reine Bausteine (Hook-Auswahl, Matrix) werden direkt getestet; der echte
Chrome-Render laeuft nur beim Nutzer. Die API wird wie die Edit-Tests mit
Junk-Dateien geprueft (Analyse schlaegt fehl -> Pack-Status 'error'), plus
Ownership-Isolation. client/auth_client/second_auth_client aus conftest.py.
"""
from __future__ import annotations

from dataclasses import dataclass

from backend import db
from backend.pipeline.content_pack import (
    MAX_PACK_ITEMS,
    build_item_matrix,
    select_hook_windows,
)


@dataclass
class _C:
    start_sec: float
    end_sec: float


# --- select_hook_windows --------------------------------------------------

def test_select_hook_windows_picks_fitting_in_rank_order():
    # offset 0, Video 30s lang. best passt, erste Alternative passt, zweite ragt raus.
    best = _C(5.0, 20.0)
    alts = [_C(2.0, 18.0), _C(40.0, 55.0)]
    wins = select_hook_windows(0.0, 30.0, best, alts, count=3)
    assert [(w.start_sec, w.end_sec) for w in wins] == [(5.0, 20.0), (2.0, 18.0)]


def test_select_hook_windows_respects_count():
    best = _C(0.0, 10.0)
    alts = [_C(1.0, 11.0), _C(2.0, 12.0), _C(3.0, 13.0)]
    assert len(select_hook_windows(0.0, 60.0, best, alts, count=2)) == 2


def test_select_hook_windows_clamps_slight_overrun():
    # Video 20s, Kandidat 8..21 ragt 1s raus -> wird auf ...20 gekuerzt.
    best = _C(8.0, 21.0)
    wins = select_hook_windows(0.0, 20.0, best, [], count=1)
    assert len(wins) == 1
    assert wins[0].start_sec == 8.0 and wins[0].end_sec == 20.0


def test_select_hook_windows_drops_far_overrun():
    best = _C(8.0, 30.0)  # ragt 10s ueber ein 20s-Video -> raus
    assert select_hook_windows(0.0, 20.0, best, [], count=3) == []


def test_select_hook_windows_dedups():
    best = _C(5.0, 20.0)
    alts = [_C(5.0, 20.0)]  # Duplikat
    assert len(select_hook_windows(0.0, 30.0, best, alts, count=5)) == 1


# --- build_item_matrix ----------------------------------------------------

def test_matrix_is_cartesian_product():
    specs = build_item_matrix(2, ["clean", "vibrant"], ["reel", "square"])
    assert len(specs) == 2 * 2 * 2
    # Reihenfolge: pro Hook alle Styles, pro Style alle Formate.
    first = specs[0]
    assert first.hook_index == 0 and first.style_key == "clean" and first.platform == "reel"
    assert [s.idx for s in specs] == list(range(8))


def test_matrix_capped_at_max():
    specs = build_item_matrix(6, ["a", "b", "c", "d"], ["r", "s"])  # 48 > MAX
    assert len(specs) == MAX_PACK_ITEMS


# --- API ------------------------------------------------------------------

def test_packs_require_login(client):
    assert client.get("/packs").status_code == 401
    assert client.get("/packs/nope").status_code == 401
    assert client.post("/packs").status_code in (401, 422)  # 422 = fehlende Dateien


def test_create_pack_with_junk_ends_in_error(auth_client):
    r = auth_client.post("/packs",
                         files={"video": ("v.mp4", b"junk", "video/mp4"),
                                "song": ("s.wav", b"junk", "audio/wav")},
                         data={"styles": "clean,vibrant", "hook_count": "2",
                               "platforms": "reel", "with_subtitles": "false"})
    assert r.status_code == 200
    body = r.json()
    pid = body["pack_id"]
    assert body["planned_items"] == 2 * 2 * 1  # 2 hooks x 2 styles x 1 format
    # Analyse mit Junk schlaegt fehl -> Pack landet sauber im Fehlerstatus.
    detail = auth_client.get(f"/packs/{pid}").json()
    assert detail["status"] == "error" and detail["error"]
    # Taucht in der eigenen Liste auf.
    assert any(p["pack_id"] == pid for p in auth_client.get("/packs").json())


def test_pack_ownership_isolation(auth_client, second_auth_client):
    r = auth_client.post("/packs",
                         files={"video": ("v.mp4", b"junk", "video/mp4"),
                                "song": ("s.wav", b"junk", "audio/wav")},
                         data={"styles": "clean", "platforms": "reel"})
    pid = r.json()["pack_id"]
    assert second_auth_client.get(f"/packs/{pid}").status_code == 404
    assert second_auth_client.get(f"/packs/{pid}/items/0/download").status_code == 404
    assert all(p["pack_id"] != pid for p in second_auth_client.get("/packs").json())


def test_invalid_styles_fall_back_to_clean(auth_client):
    r = auth_client.post("/packs",
                         files={"video": ("v.mp4", b"junk", "video/mp4"),
                                "song": ("s.wav", b"junk", "audio/wav")},
                         data={"styles": "gibtsnicht,auchnicht", "hook_count": "1",
                               "platforms": "reel"})
    assert r.status_code == 200
    assert r.json()["planned_items"] == 1  # 1 hook x 1 style(clean-fallback) x 1 format
