"""Wochen-Content / Content-Pack: aus EINEM Song/Video viele fertige Posts.

Idee: Die teure Analyse (Sync-Versatz + Hook-Erkennung + optional Untertitel)
laeuft EINMAL. Daraus wird eine Matrix aus (Hook-Fenster x Style x Format)
gebaut - jedes Element ist ein einzelner Render-Auftrag (pack_item). Vielfalt
kommt fast geschenkt: detect_hook liefert schon mehrere Kandidaten, styles.py
die Looks, platforms.py die Formate.

Die reinen, testbaren Bausteine (Hook-Auswahl, Matrix) leben hier; der
eigentliche Render pro Item (build_workspace + headless Chrome) wird von
main.py im Hintergrund aufgerufen und laeuft nur beim Nutzer.
"""
from __future__ import annotations

from dataclasses import dataclass

# Sicherheits-Deckel: verhindert, dass eine grosse Matrix (viele Hooks x viele
# Styles x viele Formate) versehentlich hunderte Render-Auftraege erzeugt.
MAX_PACK_ITEMS = 24

# gleiche Toleranz wie render_pipeline._choose_hook: ein Kandidat darf max. 1s
# ueber das gefilmte Video hinausragen (wird dann gekuerzt).
CLAMP_TOLERANCE_SEC = 1.0
MIN_HOOK_LEN_SEC = 3.0


@dataclass
class HookWindow:
    start_sec: float
    end_sec: float


def select_hook_windows(offset_sec: float, video_dur: float, best, alternatives,
                        count: int) -> list[HookWindow]:
    """Bis zu `count` Hook-Fenster, die (mit 1s-Clamp) ins gefilmte Video
    passen - gleiche Logik wie render_pipeline._choose_hook, nur mehrere.
    Reihenfolge = Ranking (best zuerst). Keine Duplikate."""
    windows: list[HookWindow] = []
    seen: set[tuple[float, float]] = set()
    for c in [best, *alternatives]:
        if len(windows) >= count:
            break
        vstart, vend = c.start_sec - offset_sec, c.end_sec - offset_sec
        if vstart < 0:
            continue
        if vend <= video_dur:
            win = HookWindow(c.start_sec, c.end_sec)
        elif vend - video_dur <= CLAMP_TOLERANCE_SEC:
            clamped_end = c.end_sec - (vend - video_dur)
            if clamped_end <= c.start_sec + MIN_HOOK_LEN_SEC:
                continue
            win = HookWindow(c.start_sec, clamped_end)
        else:
            continue
        key = (round(win.start_sec, 2), round(win.end_sec, 2))
        if key in seen:
            continue
        seen.add(key)
        windows.append(win)
    return windows


# --- Spotify Canvas -------------------------------------------------------
# Canvas ist ein 3-8s-9:16-Loop. Wir schneiden ein duration_sec-Fenster am Hook
# aus, das vollstaendig ins gefilmte Video passt.
CANVAS_MIN_SEC = 3.0
CANVAS_MAX_SEC = 8.0


def clamp_canvas_duration(sec: float) -> float:
    return max(CANVAS_MIN_SEC, min(CANVAS_MAX_SEC, sec))


def canvas_window(hook_start_sec: float, offset_sec: float, video_dur: float,
                  duration_sec: float) -> HookWindow | None:
    """Ein `duration_sec`-Fenster (in Song-Zeit) ab dem Hook, das ins gefilmte
    Video passt. Song-Zeit -> Video-Zeit ist v = s - offset. Gibt None zurueck,
    wenn nicht einmal CANVAS_MIN_SEC gefilmtes Material verfuegbar ist."""
    dur = clamp_canvas_duration(duration_sec)
    v_start = max(0.0, hook_start_sec - offset_sec)   # Startpunkt im Video (>=0)
    if v_start + dur > video_dur:                      # ragt hinten raus -> nach vorn schieben
        v_start = max(0.0, video_dur - dur)
    avail = video_dur - v_start
    if avail < CANVAS_MIN_SEC:                          # Video zu kurz fuer einen Canvas
        return None
    dur = min(dur, avail)
    song_start = v_start + offset_sec
    return HookWindow(song_start, song_start + dur)


@dataclass
class PackItemSpec:
    idx: int
    hook_index: int
    style_key: str
    platform: str


def build_item_matrix(hook_count: int, style_keys: list[str],
                      platform_keys: list[str]) -> list[PackItemSpec]:
    """Kartesische Matrix Hook x Style x Format, auf MAX_PACK_ITEMS gedeckelt.
    Reihenfolge ist hook-major (bester Hook zuerst, in ALLEN Styles/Formaten,
    dann der naechste Hook): So enthaelt ein bei MAX_PACK_ITEMS gekuerztes Paket
    die wichtigsten Hooks vollstaendig statt von jedem Hook nur Bruchstuecke."""
    specs: list[PackItemSpec] = []
    idx = 0
    for hook_index in range(max(1, hook_count)):
        for style_key in style_keys:
            for platform in platform_keys:
                if idx >= MAX_PACK_ITEMS:
                    return specs
                specs.append(PackItemSpec(idx, hook_index, style_key, platform))
                idx += 1
    return specs
