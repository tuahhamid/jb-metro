"""Spike v2: tangent-and-arc alignment (PI method) from road-following concept routes.

Rules (owner-approved 2026-11-14 for this spike):
  R = 150 m; 100 m only where 150 m cannot fit (flagged); below that, flagged as a violation.
  Each station: 100 m platform + 30 m straight both sides => 80 m clear straight each side of center.
  Station centers stay where Stage 2 put them; the line bends to reach them.
"""
import sys, json, math
import numpy as np
from shapely.geometry import LineString, Point, Polygon, box, mapping
from shapely import affinity
from shapely.strtree import STRtree
from pyproj import Transformer
import osmium
sys.stdout.reconfigure(encoding="utf-8")
repo, out = sys.argv[1], sys.argv[2]
FW = Transformer.from_crs(4326, 3375, always_xy=True)
BW = Transformer.from_crs(3375, 4326, always_xy=True)
HALF, R1, R2 = 80.0, 150.0, 100.0

def resample(xy, step=10.0):
    ln = LineString(xy); n = max(int(ln.length // step), 1)
    return np.array([ln.interpolate(i * ln.length / n).coords[0] for i in range(n + 1)])

def remove_loops(P, look=800.0, ratio=1.6, min_len=60.0):
    s = np.concatenate([[0], np.cumsum(np.hypot(*np.diff(P, axis=0).T))])
    keep, i = [0], 0
    while i < len(P) - 1:
        best, j = i + 1, i + 2
        while j < len(P) and s[j] - s[i] <= look:
            if s[j] - s[i] > min_len and (s[j] - s[i]) > ratio * max(np.hypot(*(P[j] - P[i])), 1.0):
                best = j
            j += 1
        keep.append(best); i = best
    return resample(P[keep])

def unit(v): return v / np.linalg.norm(v)
def defl(a, b, c):
    u, v = unit(b - a), unit(c - b)
    return math.acos(max(-1.0, min(1.0, float(u @ v))))
def intersect(p1, d1, p2, d2):
    M = np.array([d1, -d2]).T
    if abs(np.linalg.det(M)) < 1e-9: return None
    t = np.linalg.solve(M, p2 - p1)
    return p1 + t[0] * d1, t

def build(oid, raw, stns):
    P = remove_loops(resample(raw))
    ln = LineString(P)
    S = []
    for p in stns:
        c = np.array(FW.transform(p["lon"], p["lat"]))
        d = ln.project(Point(c))
        a = np.array(ln.interpolate(max(d - 250, 0)).coords[0]); b = np.array(ln.interpolate(min(d + 250, ln.length)).coords[0])
        S.append({"c": c, "u": unit(b - a), "d": d, "p": p})
    S.sort(key=lambda s: s["d"])
    # PI list
    PI = []
    first, last = S[0], S[-1]
    PI.append({"xy": first["c"] - first["u"] * HALF, "k": "end"})
    for i, s in enumerate(S):
        if i > 0:
            PI.append({"xy": s["c"] - s["u"] * (HALF + 40), "k": "s-", "st": s})
        if i < len(S) - 1:
            PI.append({"xy": s["c"] + s["u"] * (HALF + 40), "k": "s+", "st": s})
            # free PIs from the simplified road path between this station and the next
            seg = LineString([ln.interpolate(x).coords[0] for x in np.arange(s["d"], S[i + 1]["d"], 10.0)] + [tuple(S[i + 1]["c"])])
            simp = np.array(seg.simplify(35.0).coords)[1:-1]
            for q in simp:
                if np.hypot(*(q - s["c"])) > HALF + 120 and np.hypot(*(q - S[i + 1]["c"])) > HALF + 120:
                    PI.append({"xy": q, "k": "free"})
    PI.append({"xy": last["c"] + last["u"] * HALF, "k": "end"})
    flags = []; rot = {}
    for loop in range(3000):
        n = len(PI)
        D = [0.0] + [defl(PI[i - 1]["xy"], PI[i]["xy"], PI[i + 1]["xy"]) for i in range(1, n - 1)] + [0.0]
        for i in range(n):
            PI[i].setdefault("R", R1)
        T = [PI[i]["R"] * math.tan(D[i] / 2) for i in range(n)]
        changed = False
        # station PIs: the arc must not enter the 80 m clear zone -> push PI outward along the axis
        for i, q in enumerate(PI):
            if q["k"] in ("s+", "s-"):
                s = q["st"]; sign = 1 if q["k"] == "s+" else -1
                L = float((q["xy"] - s["c"]) @ s["u"]) * sign
                if T[i] > L - HALF + 0.5 and D[i] < math.radians(170):
                    q["xy"] = s["c"] + sign * s["u"] * (HALF + T[i] + 1.0); changed = True
        if changed:
            continue
        # segment feasibility
        bad = None
        for i in range(n - 1):
            Lseg = np.hypot(*(PI[i + 1]["xy"] - PI[i]["xy"]))
            # a station straight between s+ and s- of the same station never happens; between s- and s+ of same station the clear zone is reserved
            if PI[i]["k"] == "s-" and PI[i + 1]["k"] == "s+" and PI[i]["st"] is PI[i + 1]["st"]:
                continue
            if T[i] + T[i + 1] > Lseg + 0.5 or D[i] > math.radians(150) or D[i + 1] > math.radians(150):
                bad = i; break
        if bad is None:
            break
        i = bad; a, b = PI[i], PI[i + 1]
        if a["k"] == "free" and b["k"] == "free" and 0 < i and i + 2 < n:
            hit = intersect(a["xy"], a["xy"] - PI[i - 1]["xy"], b["xy"], b["xy"] - PI[i + 2]["xy"])
            if hit is not None and hit[1][0] > 0 and hit[1][1] > 0 and np.hypot(*(hit[0] - a["xy"])) < 400:
                PI[i:i + 2] = [{"xy": hit[0], "k": "free"}]; continue
            del PI[i if D[i] < D[i + 1] else i + 1]; continue
        if a["k"] == "free":
            del PI[i]; continue
        if b["k"] == "free":
            del PI[i + 1]; continue
        # two station-side PIs (or end) too close: relax radius, then flag
        relaxed = False
        for q in (a, b):
            if q["k"] != "end" and q["R"] > R2:
                q["R"] = R2; relaxed = True
        if relaxed:
            continue
        # last resort: rotate both platforms toward each other (centers fixed), then re-place their PIs
        if a["k"] == "s+" and b["k"] == "s-":
            sa, sb = a["st"], b["st"]
            key = (sa["p"]["seq"], sb["p"]["seq"])
            tries = rot.get(key, 0)
            if tries < 12:
                rot[key] = tries + 1
                chord = unit(sb["c"] - sa["c"])
                for s in (sa, sb):
                    s["u"] = unit(s["u"] + 0.35 * chord)
                for q in PI:
                    if q["k"] in ("s+", "s-"):
                        sg = 1 if q["k"] == "s+" else -1
                        q["xy"] = q["st"]["c"] + sg * q["st"]["u"] * (HALF + 40)
                PI[0]["xy"] = first["c"] - first["u"] * HALF
                PI[-1]["xy"] = last["c"] + last["u"] * HALF
                continue
        flags.append({"at_stations": [PI[i].get("st", {}).get("p", {}).get("seq"), PI[i + 1].get("st", {}).get("p", {}).get("seq")], "issue": "unresolved; left as is"}); break
    # geometry
    n = len(PI)
    D = [0.0] + [defl(PI[i - 1]["xy"], PI[i]["xy"], PI[i + 1]["xy"]) for i in range(1, n - 1)] + [0.0]
    pts = [PI[0]["xy"]]; used = []
    for i in range(1, n - 1):
        A, B, C = PI[i - 1]["xy"], PI[i]["xy"], PI[i + 1]["xy"]
        if D[i] < 1e-4: pts.append(B); continue
        R = PI[i]["R"]; Tn = R * math.tan(D[i] / 2)
        u1, u2 = unit(B - A), unit(C - B)
        t1, t2 = B - u1 * Tn, B + u2 * Tn
        side = np.sign(u1[0] * u2[1] - u1[1] * u2[0])
        nrm = np.array([-u1[1], u1[0]]) * side
        ctr = t1 + nrm * R
        a0 = math.atan2(*(t1 - ctr)[::-1]); a1 = math.atan2(*(t2 - ctr)[::-1])
        da = (a1 - a0 + math.pi) % (2 * math.pi) - math.pi
        m = max(int(abs(da) * R / 5), 2)
        for k in range(m + 1):
            ang = a0 + da * k / m
            pts.append(ctr + R * np.array([math.cos(ang), math.sin(ang)]))
        used.append(R)
    pts.append(PI[-1]["xy"])
    return np.array(pts), S, used, flags, len(PI)

al = {f["properties"]["option_id"]: f for f in json.load(open(f"{repo}/data/concept/alignments.geojson"))["features"]}
st = json.load(open(f"{repo}/data/concept/stations.geojson"))["features"]
lines_out, ext, stations_out, report = [], [], [], {}
for oid in ("T1", "IP2"):
    raw = np.array([FW.transform(*c) for c in al[oid]["geometry"]["coordinates"]])
    stns = [f["properties"] for f in st if f["properties"]["option_id"] == oid]
    import os
    if oid == "T1" and os.path.exists(f"{out}/t1_override.json"):  # spike: T1 extended to Ulu Tiram
        ov = json.load(open(f"{out}/t1_override.json", encoding="utf-8"))
        raw = np.array([FW.transform(*c) for c in ov["coords"]]); stns = ov["stations"]
        al["T1"] = {"geometry": {"type": "LineString", "coordinates": ov["coords"]}}
    SKIP = {"IP2": {2, 3}}.get(oid, set())  # spike call: IP2's NE detour duplicates T1 (Olympia College is T1 stn 2)
    if SKIP:
        stns = [p for p in stns if p["seq"] not in SKIP]
        nxt = min((p for p in stns if p["seq"] > 1), key=lambda p: p["seq"])
        rl = LineString(raw); d = rl.project(Point(FW.transform(nxt["lon"], nxt["lat"])))
        rest = [c for c in raw if rl.project(Point(c)) > d]
        raw = np.array([raw[0], rl.interpolate(d).coords[0]] + rest)
        report_skip = sorted(SKIP)
    G, S, used, flags, npi = build(oid, raw, stns)
    g = LineString(G); orig = LineString(raw)
    # verify: station centers on line, straight +-80 m
    stn_err = []
    for s in S:
        d = g.project(Point(s["c"]))
        a = np.array(g.interpolate(d - HALF).coords[0]); b = np.array(g.interpolate(d + HALF).coords[0]); m = np.array(g.interpolate(d).coords[0])
        dev = LineString([a, b]).distance(Point(m))
        stn_err.append(round(max(np.hypot(*(m - s["c"])), dev), 1))
    report[oid] = {"PIs": npi, "length_km_before": round(orig.length / 1000, 2), "length_km_after": round(g.length / 1000, 2),
                   "curves": len(used), "curves_R150": sum(r >= R1 for r in used), "curves_R100": sum(R2 <= r < R1 for r in used),
                   "curves_below_R100": sum(r < R2 for r in used), "flags": flags,
                   "max_station_error_m": max(stn_err), "max_offset_from_road_route_m": round(max(orig.distance(Point(q)) for q in G[::4]))}
    lines_out.append({"type": "Feature", "geometry": {"type": "LineString", "coordinates": [list(BW.transform(*q)) for q in G]}, "properties": {"kind": "line", "line": oid}})
    lines_out.append({"type": "Feature", "geometry": al[oid]["geometry"], "properties": {"kind": "roadroute", "line": oid}})
    via = g.buffer(4.5, cap_style=2)
    ext.append({"type": "Feature", "geometry": via, "properties": {"kind": "viaduct", "line": oid, "base": 11, "top": 13.5}})
    for s in S:
        p = s["p"]
        if oid == "IP2" and p["seq"] == 1: continue
        d = g.project(Point(s["c"])); a = np.array(g.interpolate(d - 40).coords[0]); b = np.array(g.interpolate(d + 40).coords[0])
        u = unit(b - a); c = s["c"]; ang = math.degrees(math.atan2(u[1], u[0]))
        ext.append({"type": "Feature", "geometry": affinity.rotate(box(c[0] - 50, c[1] - 12, c[0] + 50, c[1] + 12), ang, origin=Point(c)), "properties": {"kind": "station", "line": oid, "base": 9, "top": 21}})
        ext.append({"type": "Feature", "geometry": affinity.rotate(box(c[0] - 56, c[1] - 15, c[0] + 56, c[1] + 15), ang, origin=Point(c)), "properties": {"kind": "roof", "line": oid, "base": 21, "top": 22.5}})
        lon, lat = BW.transform(*c)
        stations_out.append({"line": oid, "seq": p["seq"], "name": p["label_near"] or f"Station {p['seq']}", "lon": lon, "lat": lat})

class Bh(osmium.SimpleHandler):
    def __init__(s): super().__init__(); s.polys = []
    def area(s, a):
        if "building" not in a.tags: return
        try:
            for ring in a.outer_rings():
                s.polys.append(Polygon([FW.transform(n.lon, n.lat) for n in ring]))
        except Exception: pass
h = Bh(); h.apply_file(f"{repo}/data/raw/osm/jb-study.osm.pbf", locations=True)
tree = STRtree(h.polys)
for f in list(lines_out):
    if f["properties"]["kind"] != "line": continue
    oid = f["properties"]["line"]
    g = LineString([FW.transform(*c) for c in f["geometry"]["coordinates"]])
    old = LineString([FW.transform(*c) for c in al[oid]["geometry"]["coordinates"]])
    hits = [h.polys[i] for i in tree.query(g, predicate="intersects")]
    new = [p for p in hits if not p.intersects(old)]
    report[oid]["buildings_crossed"] = len(hits); report[oid]["buildings_crossed_new"] = len(new)
    for p in new:
        lines_out.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": list(BW.transform(*p.centroid.coords[0]))}, "properties": {"kind": "clip", "line": oid}})
from shapely.ops import transform as tr
for e in ext:
    e["geometry"] = mapping(tr(lambda x, y, z=None: BW.transform(x, y), e["geometry"]))
json.dump({"type": "FeatureCollection", "features": lines_out}, open(f"{out}/smooth_lines.geojson", "w"))
json.dump({"type": "FeatureCollection", "features": ext}, open(f"{out}/smooth_ext.geojson", "w"))
json.dump(stations_out, open(f"{out}/smooth_stations.json", "w"), ensure_ascii=False)
print(json.dumps(report, indent=1))
