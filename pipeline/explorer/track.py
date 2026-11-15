"""Turn a road-following concept route into track-like geometry (tangents and arcs).

Method (spec section 5.3, ported from the spike `track2.py`): resample the road route,
remove loops and ramps, then place intersection points (PIs): two per station on the
platform axis and a few "free" PIs from the simplified road. Every PI gets a circular
arc (150 m; 100 m only where 150 m cannot fit). Conflicts are resolved by merging or
dropping free PIs, pushing station PIs outward, relaxing the radius, and as a last
resort rotating two platforms toward each other. Station centers never move.

All coordinates are metres in a projected CRS (the pipeline uses EPSG:32648).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
from shapely.geometry import LineString, Point
from shapely.strtree import STRtree


@dataclass(frozen=True)
class TrackRules:
    r_min: float = 150.0
    r_fallback: float = 100.0
    clear_half: float = 80.0          # 100 m platform + 30 m each side -> 80 m each side of center
    resample_m: float = 10.0
    loop_look_m: float = 800.0
    loop_ratio: float = 1.6
    loop_min_m: float = 60.0
    simplify_tol_m: float = 35.0
    free_pi_keepout_m: float = 200.0


@dataclass(frozen=True)
class StationIn:
    key: str
    x: float
    y: float


@dataclass
class TrackResult:
    xy: np.ndarray
    stations: dict[str, tuple[float, float, float, float]]
    radii: list[float] = field(default_factory=list)
    flags: list[dict] = field(default_factory=list)


_MAX_ITER = 3000
_MAX_ROTATIONS = 12
_STATION_PI_GAP = 40.0               # initial distance of a station PI beyond the clear zone
_AXIS_LOOK_M = 250.0                 # platform axis = road direction over +-250 m


def resample(xy: np.ndarray, step: float) -> np.ndarray:
    ln = LineString(np.asarray(xy, float))
    n = max(int(ln.length // step), 1)
    return np.array([ln.interpolate(i * ln.length / n).coords[0] for i in range(n + 1)])


def remove_loops(xy: np.ndarray, look_m: float, ratio: float, min_len_m: float) -> np.ndarray:
    """Shortcut every stretch whose path length exceeds `ratio` x its chord, for chords up to `look_m`.

    "Within look_m" is the straight-line (chord) distance, so a loop is cut from the first
    point that can see past it, and the cut lands beyond the loop, not inside it.
    """
    P = np.asarray(xy, float)
    s = np.concatenate([[0.0], np.cumsum(np.hypot(*np.diff(P, axis=0).T))])
    keep, i = [0], 0
    while i < len(P) - 1:
        best, j = i + 1, i + 2
        while j < len(P) and s[j] - s[i] <= 3 * look_m:
            run, chord = s[j] - s[i], float(np.hypot(*(P[j] - P[i])))
            if chord <= look_m and run > min_len_m and run > ratio * max(chord, 1.0):
                best = j
            j += 1
        keep.append(best)
        i = best
    step = float(np.median(np.diff(s))) if len(s) > 1 else 10.0
    return resample(P[keep], max(step, 1.0))


def _unit(v: np.ndarray) -> np.ndarray:
    n = float(np.linalg.norm(v))
    return v / n if n > 0 else v


def _defl(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> float:
    u, v = _unit(b - a), _unit(c - b)
    return math.acos(max(-1.0, min(1.0, float(u @ v))))


def _intersect(p1, d1, p2, d2):
    M = np.array([d1, -d2]).T
    if abs(np.linalg.det(M)) < 1e-9:
        return None
    t = np.linalg.solve(M, p2 - p1)
    return p1 + t[0] * d1, t


def _arc_points(A, B, C, R, D):
    Tn = R * math.tan(D / 2)
    u1, u2 = _unit(B - A), _unit(C - B)
    t1, t2 = B - u1 * Tn, B + u2 * Tn
    side = np.sign(u1[0] * u2[1] - u1[1] * u2[0])
    ctr = t1 + np.array([-u1[1], u1[0]]) * side * R
    a0 = math.atan2(*(t1 - ctr)[::-1])
    a1 = math.atan2(*(t2 - ctr)[::-1])
    da = (a1 - a0 + math.pi) % (2 * math.pi) - math.pi
    m = max(math.ceil(abs(da) * R / 5.0), 2)   # arcs sampled at <= 5 m
    return [ctr + R * np.array([math.cos(a0 + da * k / m), math.sin(a0 + da * k / m)]) for k in range(m + 1)]


def build_track(road_xy: np.ndarray, stations: list[StationIn], rules: TrackRules = TrackRules()) -> TrackResult:
    HALF = rules.clear_half
    P = remove_loops(resample(road_xy, rules.resample_m), rules.loop_look_m, rules.loop_ratio, rules.loop_min_m)
    ln = LineString(P)

    S = []
    for st in stations:
        c = np.array([st.x, st.y], float)
        d = ln.project(Point(c))
        a = np.array(ln.interpolate(max(d - _AXIS_LOOK_M, 0)).coords[0])
        b = np.array(ln.interpolate(min(d + _AXIS_LOOK_M, ln.length)).coords[0])
        S.append({"c": c, "u": _unit(b - a), "d": d, "key": st.key})
    S.sort(key=lambda s: s["d"])
    first, last = S[0], S[-1]
    keepout = rules.free_pi_keepout_m

    PI = [{"xy": first["c"] - first["u"] * HALF, "k": "end"}]
    for i, s in enumerate(S):
        if i > 0:
            PI.append({"xy": s["c"] - s["u"] * (HALF + _STATION_PI_GAP), "k": "s-", "st": s})
        if i < len(S) - 1:
            PI.append({"xy": s["c"] + s["u"] * (HALF + _STATION_PI_GAP), "k": "s+", "st": s})
            nxt = S[i + 1]
            pts = [ln.interpolate(x).coords[0] for x in np.arange(s["d"], nxt["d"], rules.resample_m)]
            seg = LineString(pts + [tuple(nxt["c"])]) if pts else LineString([tuple(s["c"]), tuple(nxt["c"])])
            for q in np.array(seg.simplify(rules.simplify_tol_m).coords)[1:-1]:
                if np.hypot(*(q - s["c"])) > keepout and np.hypot(*(q - nxt["c"])) > keepout:
                    PI.append({"xy": q, "k": "free"})
    PI.append({"xy": last["c"] + last["u"] * HALF, "k": "end"})

    def place_station_pis():
        for q in PI:
            if q["k"] in ("s+", "s-"):
                sg = 1 if q["k"] == "s+" else -1
                q["xy"] = q["st"]["c"] + sg * q["st"]["u"] * (HALF + _STATION_PI_GAP)
        PI[0]["xy"] = first["c"] - first["u"] * HALF
        PI[-1]["xy"] = last["c"] + last["u"] * HALF

    flags: list[dict] = []
    rotations: dict[tuple, int] = {}
    for _ in range(_MAX_ITER):
        n = len(PI)
        D = [0.0] + [_defl(PI[i - 1]["xy"], PI[i]["xy"], PI[i + 1]["xy"]) for i in range(1, n - 1)] + [0.0]
        for q in PI:
            q.setdefault("R", rules.r_min)
        T = [PI[i]["R"] * math.tan(D[i] / 2) for i in range(n)]

        changed = False
        for i, q in enumerate(PI):
            if q["k"] in ("s+", "s-"):
                s, sign = q["st"], (1 if q["k"] == "s+" else -1)
                L = float((q["xy"] - s["c"]) @ s["u"]) * sign
                if T[i] > L - HALF + 0.5 and D[i] < math.radians(170):
                    q["xy"] = s["c"] + sign * s["u"] * (HALF + T[i] + 1.0)
                    changed = True
        if changed:
            continue

        bad = None
        for i in range(n - 1):
            if PI[i]["k"] == "s-" and PI[i + 1]["k"] == "s+" and PI[i]["st"] is PI[i + 1]["st"]:
                continue
            Lseg = float(np.hypot(*(PI[i + 1]["xy"] - PI[i]["xy"])))
            if T[i] + T[i + 1] > Lseg + 0.5 or D[i] > math.radians(150) or D[i + 1] > math.radians(150):
                bad = i
                break
        if bad is None:
            break

        i = bad
        a, b = PI[i], PI[i + 1]
        if a["k"] == "free" and b["k"] == "free" and 0 < i and i + 2 < n:
            hit = _intersect(a["xy"], a["xy"] - PI[i - 1]["xy"], b["xy"], b["xy"] - PI[i + 2]["xy"])
            if hit is not None and hit[1][0] > 0 and hit[1][1] > 0 and np.hypot(*(hit[0] - a["xy"])) < 400:
                PI[i:i + 2] = [{"xy": hit[0], "k": "free"}]
                continue
            del PI[i if D[i] < D[i + 1] else i + 1]
            continue
        if a["k"] == "free":
            del PI[i]
            continue
        if b["k"] == "free":
            del PI[i + 1]
            continue
        relaxed = False
        for q in (a, b):
            if q["k"] != "end" and q["R"] > rules.r_fallback:
                q["R"] = rules.r_fallback
                relaxed = True
        if relaxed:
            continue
        if a["k"] == "s+" and b["k"] == "s-":
            sa, sb = a["st"], b["st"]
            key = (sa["key"], sb["key"])
            if rotations.get(key, 0) < _MAX_ROTATIONS:
                rotations[key] = rotations.get(key, 0) + 1
                chord = _unit(sb["c"] - sa["c"])
                for s in (sa, sb):
                    s["u"] = _unit(s["u"] + 0.35 * chord)
                place_station_pis()
                continue
        flags.append({"issue": "unresolved conflict; left as is",
                      "at_stations": [a.get("st", {}).get("key"), b.get("st", {}).get("key")]})
        break

    n = len(PI)
    D = [0.0] + [_defl(PI[i - 1]["xy"], PI[i]["xy"], PI[i + 1]["xy"]) for i in range(1, n - 1)] + [0.0]
    pts, radii = [PI[0]["xy"]], []
    for i in range(1, n - 1):
        A, B, C = PI[i - 1]["xy"], PI[i]["xy"], PI[i + 1]["xy"]
        if D[i] < 1e-4:
            pts.append(B)
            continue
        R = float(PI[i]["R"])
        pts.extend(_arc_points(A, B, C, R, D[i]))
        radii.append(R)
        if R < rules.r_min:
            flags.append({"issue": f"radius {R:g} m (fallback)", "at": [round(float(B[0]), 1), round(float(B[1]), 1)]})
    pts.append(PI[-1]["xy"])

    st_out = {s["key"]: (float(s["c"][0]), float(s["c"][1]), float(s["u"][0]), float(s["u"][1])) for s in S}
    return TrackResult(xy=np.array(pts), stations=st_out, radii=radii, flags=flags)


def track_report(result: TrackResult, road_xy: np.ndarray, buildings: list[tuple],
                 rules: TrackRules = TrackRules()) -> dict:
    g = LineString(result.xy)
    road = LineString(np.asarray(road_xy, float))
    err = []
    for x, y, _, _ in result.stations.values():
        d = g.project(Point(x, y))
        m = np.array(g.interpolate(d).coords[0])
        # clamp: shapely measures negative distances from the far end
        a, b = g.interpolate(max(d - rules.clear_half, 0.0)), g.interpolate(min(d + rules.clear_half, g.length))
        dev = LineString([a, b]).distance(Point(m))
        err.append(max(float(np.hypot(m[0] - x, m[1] - y)), float(dev)))
    polys = [b[0] for b in buildings]
    crossed = []
    if polys:
        tree = STRtree(polys)
        crossed = [buildings[i][2] for i in sorted(tree.query(g, predicate="intersects"))]
    r = result.radii
    return {
        "curves": len(r),
        "curves_r150": sum(x >= rules.r_min for x in r),
        "curves_r100": sum(rules.r_fallback <= x < rules.r_min for x in r),
        "curves_below_r100": sum(x < rules.r_fallback for x in r),
        "flags": result.flags,
        "max_station_error_m": round(max(err), 2) if err else 0.0,
        "length_km_before": round(road.length / 1000, 2),
        "length_km_after": round(g.length / 1000, 2),
        "max_offset_from_road_m": round(max(road.distance(Point(q)) for q in result.xy), 1),
        "buildings_crossed": crossed,
    }
