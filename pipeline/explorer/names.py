"""Unique, human station names per line (spec section 5.5).

Order: owner override, then the nearest unused landmark within 300 m, then the nearest
unused OSM place within 700 m, then "{nearest road} km {chainage}". Greedy in station order.
"""
from __future__ import annotations

import numpy as np
from shapely.geometry import LineString, Point

LANDMARK_M = 300.0
PLACE_M = 700.0


def _nearest_unused(x, y, cands, used, limit):
    best = None
    for name, cx, cy in cands:
        if name in used:
            continue
        d = float(np.hypot(cx - x, cy - y))
        if d <= limit and (best is None or d < best[0]):
            best = (d, name)
    return best[1] if best else None


def name_stations(stations: list[dict], landmarks: list[tuple[str, float, float]],
                  places: list[tuple[str, float, float]], roads: list[tuple[str, LineString]],
                  line_xy: np.ndarray, overrides: dict[str, str], return_rules: bool = False):
    line = LineString(np.asarray(line_xy, float))
    used = set(overrides.get(s["key"]) for s in stations if s["key"] in overrides)
    names, rules = {}, {}
    for s in stations:
        k, x, y = s["key"], s["x"], s["y"]
        if k in overrides:
            names[k], rules[k] = overrides[k], "override"
            continue
        nm = _nearest_unused(x, y, landmarks, used, LANDMARK_M)
        rule = "landmark"
        if nm is None:
            nm, rule = _nearest_unused(x, y, places, used, PLACE_M), "place"
        if nm is None:
            rule = "road"
            road = min(roads, key=lambda r: r[1].distance(Point(x, y)))[0] if roads else "Station"
            nm = f"{road} km {line.project(Point(x, y)) / 1000:.1f}"
            base, i = nm, 2
            while nm in used:
                nm, i = f"{base} ({i})", i + 1
        used.add(nm)
        names[k], rules[k] = nm, rule
    return (names, rules) if return_rules else names
