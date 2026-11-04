"""Stage 2: build alignment hypotheses and screen their constraints.

Every line, station and depot produced here is status=concept (lines/stations) or
inferred (screening values). Nothing is official. Inputs:
  --osm   OSM study clip (ODbL)
  --dem   Copernicus GLO-30 DSM crop (optional; grades skipped if missing)
  --flood JRC RP100 river-flood depth crop (optional)
  --gtfs  BAS.MY GTFS zip, --ktmb KTMB GTFS zip (bus/rail interchange counts)
  --options pipeline/stage2/options.json

Outputs (see docs/alignments/README.md for definitions):
  data/concept/alignments.geojson, stations.geojson, depot-candidates.geojson
  results/stage2/option_comparison.csv, pinch_points.csv, flood_spots.csv,
  interchange_access.csv, segments.csv, run_report.json, options-map.png

Screening thresholds are assumptions A-026..A-034 in docs/assumptions/assumptions-log.csv.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import re
import time
import zipfile
from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd
import shapely
from scipy.spatial import cKDTree
from shapely.geometry import LineString, Point, mapping
from shapely.ops import substring

from osm_layers import NO_WALK, ROAD_CLASSES, DEPOT_LANDUSE, TO_UTM, TO_WGS, read_osm

# ---- Screening parameters (assumptions log ids in comments) -------------------------
CLASS_FACTOR = {  # routing preference: guideways follow wide road reserves (A-026)
    "motorway": 4.0, "motorway_link": 5.0, "trunk": 1.0, "trunk_link": 2.5, "primary": 1.05,
    "primary_link": 2.5, "secondary": 1.3, "secondary_link": 2.5, "tertiary": 1.8,
    "tertiary_link": 3.0,
}
PREFER_FACTOR = 0.3   # named roads in the option spec are followed wherever they connect the vias
WALK_CUTOFF_M = 800            # station catchment (A-027)
SPACING_MIN_M, SPACING_MAX_M = 1000, 1500   # brief: ~1-1.5 km (A-028)
CAND_STEP_M = 100
CLEAR_WIDTH_LINE_M = (16, 20, 25)    # building-to-building width needed for a viaduct (A-029)
CLEAR_WIDTH_STATION_M = (24, 30, 36)  # ... at an elevated station (A-029)
SIDE_SETBACK_M = (10, 15)            # facade this close to the route centerline on either side: line / station (A-029)
CURVE_R_FLAG_M = (50, 100)           # ART-ish / rail-APM minimum radius screens (A-030)
GRADE_FLAG = (0.05, 0.08)            # rail / rubber-tired screens (A-031)
LOW_LYING_M = 5.0                    # DEM low-lying proxy (A-032)
NEAR_WATER_M = 150
DEPOT_MIN_HA = (5, 8, 15)            # ART small / base / LRT-scale (A-033)
DEPOT_MAX_DIST_M = 1500
BUS_WALK_M = 400                     # bus interchange catchment (A-034)
WATER_EXCLUDE_M = 25                 # station candidates closer than this to a waterway/coast are dropped
FORCED_MAX_OFFSET_M = 500            # anchors farther than this from the line are reported as not served


def lonlat(x, y):
    lo, la = TO_WGS.transform(x, y)
    return round(lo, 6), round(la, 6)


# ---- Graph construction ---------------------------------------------------------------
def build_graphs(L):
    road = nx.Graph()
    walk = nx.Graph()
    edge_tags = {}
    for w in L.ways:
        t = w["tags"]
        hw = t.get("highway", "")
        ns = w["nodes"]
        is_road = hw in ROAD_CLASSES and t.get("area") != "yes"
        walkable = (hw not in NO_WALK and t.get("foot") not in ("no", "private")
                    and t.get("access") not in ("private", "no") or t.get("foot") in ("yes", "designated"))
        for a, b in zip(ns[:-1], ns[1:]):
            (xa, ya), (xb, yb) = L.node_xy[a], L.node_xy[b]
            d = math.hypot(xb - xa, yb - ya)
            if d == 0:
                continue
            if is_road:
                f = CLASS_FACTOR.get(hw, 2.0)
                if not road.has_edge(a, b) or road[a][b]["base"] > d * f:
                    road.add_edge(a, b, length=d, base=d * f, way=w["id"])
            if walkable:
                walk.add_edge(a, b, length=d, way=w["id"])
        edge_tags[w["id"]] = t
    return road, walk, edge_tags


def kdtree(G, node_xy):
    ids = np.array(list(G.nodes))
    xy = np.array([node_xy[i] for i in ids])
    return ids, xy, cKDTree(xy)


# ---- Anchors --------------------------------------------------------------------------
def resolve_anchors(spec, L):
    out = {}
    feats = [(x, y, t, oid) for (x, y, t, oid) in L.points] + [(x, y, t, oid) for (x, y, t, oid) in L.named_areas]
    for key, a in spec["anchors"].items():
        if not a.get("match"):
            fx, fy = TO_UTM.transform(*a["fallback_lonlat"])
            out[key] = {"label": a["label"], "x": fx, "y": fy, "resolved_by": "coordinate_on_osm_road",
                        "osm_id": None, "osm_name": None, "offset_from_fallback_m": 0}
            continue
        rx = re.compile(a["match"]["name"], re.I)
        tk, tv = a["match"]["tag"]
        hits = [f for f in feats if rx.search(f[2].get("name", "")) and tk in f[2]
                and (tv is None or f[2].get(tk) == tv)]
        fx, fy = TO_UTM.transform(*a["fallback_lonlat"])
        if hits:
            # nearest hit to the fallback point (guards against same-name features elsewhere)
            h = min(hits, key=lambda f: math.hypot(f[0] - fx, f[1] - fy))
            dist = math.hypot(h[0] - fx, h[1] - fy)
            if dist < 3000:
                out[key] = {"label": a["label"], "x": h[0], "y": h[1], "resolved_by": "osm",
                            "osm_id": int(h[3]), "osm_name": h[2].get("name"), "offset_from_fallback_m": round(dist)}
                continue
        out[key] = {"label": a["label"], "x": fx, "y": fy, "resolved_by": "fallback_coordinate",
                    "osm_id": None, "osm_name": None, "offset_from_fallback_m": 0}
    return out


# ---- Routing --------------------------------------------------------------------------
def route_option(opt, anchors, road, L, rtree):
    ids, xy, tree = rtree
    prefer = set(opt.get("prefer_roads", []))
    way_name = {}
    for w in L.ways:
        way_name[w["id"]] = w["tags"].get("name", "")

    def weight(u, v, d):
        if way_name.get(d["way"], "") in prefer:
            return d["length"] * PREFER_FACTOR
        return d["base"]

    path = []
    via_nodes = []
    for k in opt["vias"]:
        a = anchors[k]
        _, i = tree.query([a["x"], a["y"]])
        via_nodes.append(int(ids[i]))
    for s, t in zip(via_nodes[:-1], via_nodes[1:]):
        seg = nx.shortest_path(road, s, t, weight=weight)
        path.extend(seg if not path else seg[1:])
    # remove loops and spurs: if a node repeats, cut the path back to its first visit
    clean, seen = [], {}
    for n in path:
        if n in seen:
            k = seen[n]
            for m in clean[k + 1:]:
                seen.pop(m, None)
            clean = clean[:k + 1]
            continue
        seen[n] = len(clean)
        clean.append(n)
    coords = [L.node_xy[n] for n in clean]
    line = LineString(coords)
    ways = [road[a][b]["way"] for a, b in zip(clean[:-1], clean[1:])]
    return line, clean, ways, via_nodes


def chainage_of(line, x, y):
    return line.project(Point(x, y))


# ---- Walk catchments ------------------------------------------------------------------
class Walk:
    def __init__(self, walk, L):
        self.G = walk
        self.ids, self.xy, self.tree = kdtree(walk, L.node_xy)
        self.index = {int(n): i for i, n in enumerate(self.ids)}
        # buildings -> nearest walk node (<=150 m), weight = footprint area x levels (if tagged)
        bxy, bw = [], []
        for poly, lv, _ in L.buildings:
            c = poly.centroid
            bxy.append((c.x, c.y))
            bw.append(poly.area * (lv if lv and 0 < lv < 80 else 1.0))
        self.bxy = np.array(bxy) if bxy else np.zeros((0, 2))
        self.bw = np.array(bw)
        d, j = self.tree.query(self.bxy) if len(bxy) else (np.array([]), np.array([], int))
        self.b_node = np.where(d <= 150, j, -1)
        order = np.argsort(self.b_node)
        self.b_sorted = order
        self.b_keys = self.b_node[order]

    def snap(self, x, y):
        d, i = self.tree.query([x, y])
        return int(self.ids[i]), float(d)

    def reach(self, x, y, cutoff=WALK_CUTOFF_M):
        n, d0 = self.snap(x, y)
        dist = nx.single_source_dijkstra_path_length(self.G, n, cutoff=max(cutoff - d0, 0), weight="length")
        return dist, d0

    def buildings_in(self, dist):
        idx = np.array([self.index[n] for n in dist], dtype=int)
        lo = np.searchsorted(self.b_keys, idx, "left")
        hi = np.searchsorted(self.b_keys, idx, "right")
        sel = [self.b_sorted[a:b] for a, b in zip(lo, hi) if b > a]
        return np.concatenate(sel) if sel else np.array([], int)

    def catchment_ratio(self, dist, x, y):
        pts = self.xy[[self.index[n] for n in dist]]
        if len(pts) < 3:
            return 0.0
        geom = shapely.buffer(shapely.multipoints(pts), 50).intersection(Point(x, y).buffer(WALK_CUTOFF_M))
        return float(geom.area / (math.pi * WALK_CUTOFF_M ** 2))


def place_stations(line, forced_ch, W, water=None):
    """Exclusive-catchment dynamic program: choose stations along the line maximizing the unique
    building floor-area proxy within an 800 m network walk, with 1.0-1.5 km spacing. Forced
    chainages (interchanges, termini) are always stations."""
    Lm = line.length
    cands = sorted(set([round(c) for c in np.arange(0, Lm, CAND_STEP_M)] + [round(Lm)] +
                       [round(c) for c in forced_ch]))
    cands = np.array(cands, float)
    forced_c = {round(c) for c in forced_ch} | {round(Lm), 0}
    if water is not None:  # no station on a river bridge or at the water's edge (unless forced)
        keep = [c for c in cands if round(c) in forced_c or water.distance(line.interpolate(c)) > WATER_EXCLUDE_M]
        cands = np.array(keep, float)
    forced = {int(np.argmin(abs(cands - c))) for c in forced_ch} | {0, len(cands) - 1}
    sets, score, reach = [], [], []
    for c in cands:
        p = line.interpolate(c)
        dist, _ = W.reach(p.x, p.y)
        b = W.buildings_in(dist)
        sets.append(set(b.tolist()))
        score.append(float(W.bw[b].sum()) if len(b) else 0.0)
        reach.append(dist)
    n = len(cands)
    best = np.full(n, -np.inf)
    prev = np.full(n, -1)
    best[0] = score[0]
    for i in range(1, n):
        for j in range(i - 1, -1, -1):
            gap = cands[i] - cands[j]
            if gap > SPACING_MAX_M and not (i in forced and j in forced):
                # allow the gap only if no candidate can bridge it (handled by min spacing below)
                if gap > SPACING_MAX_M * 1.6:
                    break
            if best[j] == -np.inf:
                continue
            short_ok = gap >= SPACING_MIN_M or (i in forced and j in forced) or (gap >= 600 and (i in forced or j in forced))
            if not short_ok:
                continue
            # a forced station may not be skipped
            if any(k in forced for k in range(j + 1, i)):
                continue
            ov = len(sets[i] & sets[j])
            gain = score[i] - (float(W.bw[list(sets[i] & sets[j])].sum()) if ov else 0.0)
            penalty = 0.0 if gap <= SPACING_MAX_M else 1e12  # gaps > max only if unavoidable
            val = best[j] + gain - penalty
            if val > best[i]:
                best[i], prev[i] = val, j
    chosen = []
    i = n - 1
    while i >= 0:
        chosen.append(i)
        i = prev[i]
        if i == -1:
            break
    chosen = chosen[::-1]
    return [(float(cands[i]), score[i], reach[i], i in forced) for i in chosen]


# ---- Cross-section and structure screens ---------------------------------------------
def segment_screens(line, ways, path_nodes, L, edge_tags, btree, bgeoms):
    """Every 100 m: road class, lanes, carriageway type, building setbacks left/right."""
    rows = []
    # per-chainage way lookup
    cum = [0.0]
    for a, b in zip(path_nodes[:-1], path_nodes[1:]):
        (xa, ya), (xb, yb) = L.node_xy[a], L.node_xy[b]
        cum.append(cum[-1] + math.hypot(xb - xa, yb - ya))
    cum = np.array(cum)
    for s in np.arange(50, line.length, 100):
        k = min(int(np.searchsorted(cum, s, "right")) - 1, len(ways) - 1)
        t = edge_tags.get(ways[k], {})
        p = line.interpolate(s)
        q = line.interpolate(min(s + 10, line.length))
        r = line.interpolate(max(s - 10, 0))
        dx, dy = q.x - r.x, q.y - r.y
        nrm = math.hypot(dx, dy) or 1
        nx_, ny_ = -dy / nrm, dx / nrm
        setbacks = []
        for sign in (1, -1):
            ray = LineString([(p.x, p.y), (p.x + sign * nx_ * 60, p.y + sign * ny_ * 60)])
            hits = btree.query(ray, predicate="intersects")
            dmin = min((Point(p.x, p.y).distance(bgeoms[h]) for h in hits), default=60.0)
            setbacks.append(min(dmin, 60.0))
        lanes = t.get("lanes")
        try:
            lanes = float(lanes)
        except (TypeError, ValueError):
            lanes = None
        oneway = t.get("oneway") in ("yes", "1", "true")
        rows.append({
            "chainage_m": round(float(s)), "x": p.x, "y": p.y, "way_id": ways[k],
            "road_name": t.get("name", ""), "road_ref": t.get("ref", ""), "highway": t.get("highway", ""),
            "lanes_tag": lanes, "width_tag": t.get("width", ""), "oneway": oneway,
            "carriageway": "dual (one-way pair)" if oneway else "single",
            "bridge_or_flyover": t.get("bridge") not in (None, "no") or (t.get("layer", "0").lstrip("-").isdigit() and int(t.get("layer", "0")) > 0),
            "setback_left_m": round(setbacks[0], 1), "setback_right_m": round(setbacks[1], 1),
            "clear_width_m": round(setbacks[0] + setbacks[1], 1),
        })
    return pd.DataFrame(rows)


def curvature_flags(line):
    out = []
    step, half = 20.0, 40.0
    for s in np.arange(half, line.length - half, step):
        a, b, c = (line.interpolate(s - half), line.interpolate(s), line.interpolate(s + half))
        ab, bc, ca = a.distance(b), b.distance(c), c.distance(a)
        area2 = abs((b.x - a.x) * (c.y - a.y) - (c.x - a.x) * (b.y - a.y))
        R = (ab * bc * ca) / (2 * area2) if area2 > 1e-6 else 1e9
        out.append((s, R, b.x, b.y))
    return out


def merge_spans(df, flag_col, ch_col="chainage_m", gap=150):
    spans = []
    cur = None
    for _, r in df[df[flag_col]].iterrows():
        if cur and r[ch_col] - cur["end"] <= gap:
            cur["end"] = r[ch_col]
            cur["rows"].append(r)
        else:
            if cur:
                spans.append(cur)
            cur = {"start": r[ch_col], "end": r[ch_col], "rows": [r]}
    if cur:
        spans.append(cur)
    return spans


# ---- DEM / flood sampling -------------------------------------------------------------
class Raster:
    def __init__(self, path):
        import rasterio
        self.ds = rasterio.open(path)
        self.a = self.ds.read(1).astype(float)
        nod = self.ds.nodata
        if nod is not None:
            self.a[self.a == nod] = np.nan

    def sample(self, xs, ys):
        lo, la = TO_WGS.transform(np.asarray(xs), np.asarray(ys))
        inv = ~self.ds.transform
        cf, rf = inv * (np.asarray(lo, float), np.asarray(la, float))
        r, c = np.floor(np.atleast_1d(rf)).astype(int), np.floor(np.atleast_1d(cf)).astype(int)
        ok = (r >= 0) & (r < self.a.shape[0]) & (c >= 0) & (c < self.a.shape[1])
        v = np.full(len(r), np.nan)
        v[ok] = self.a[r[ok], c[ok]]
        return v


def grade_profile(line, dem):
    s = np.arange(0, line.length, 25.0)
    pts = [line.interpolate(v) for v in s]
    z = dem.sample([p.x for p in pts], [p.y for p in pts])
    zs = pd.Series(z).rolling(11, center=True, min_periods=3).median().to_numpy()  # 250 m median: DSM noise
    g = np.full(len(s), np.nan)
    w = 8  # 200 m base
    g[w:] = (zs[w:] - zs[:-w]) / (s[w:] - s[:-w])
    return s, z, zs, g


# ---- GTFS -----------------------------------------------------------------------------
def gtfs_stops(path, agency):
    out = []
    try:
        with zipfile.ZipFile(path) as z:
            stops = pd.read_csv(z.open("stops.txt"), dtype=str)
            trips = pd.read_csv(z.open("trips.txt"), dtype=str)
            st = pd.read_csv(z.open("stop_times.txt"), dtype=str, usecols=["trip_id", "stop_id"])
        sr = st.merge(trips[["trip_id", "route_id"]], on="trip_id").groupby("stop_id")["route_id"] \
            .apply(lambda s: sorted(set(s))).to_dict()
        for _, r in stops.iterrows():
            x, y = TO_UTM.transform(float(r["stop_lon"]), float(r["stop_lat"]))
            out.append({"agency": agency, "stop_id": r["stop_id"], "name": r.get("stop_name", ""), "x": x, "y": y,
                        "routes": sr.get(r["stop_id"], [])})
    except Exception as e:  # noqa: BLE001
        print("GTFS read failed", path, e)
    return out


# ---- Main -----------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--osm", required=True)
    ap.add_argument("--dem")
    ap.add_argument("--flood")
    ap.add_argument("--gtfs")
    ap.add_argument("--ktmb")
    ap.add_argument("--options", default="pipeline/stage2/options.json")
    ap.add_argument("--only", help="comma-separated option ids (development)")
    ap.add_argument("--concept-out", default="data/concept")
    ap.add_argument("--out", default="results/stage2")
    a = ap.parse_args()
    t0 = time.time()
    spec = json.loads(Path(a.options).read_text())
    out, cdir = Path(a.out), Path(a.concept_out)
    out.mkdir(parents=True, exist_ok=True)
    cdir.mkdir(parents=True, exist_ok=True)

    L = read_osm(a.osm)
    print(f"OSM read: {len(L.ways)} highway ways, {len(L.buildings)} buildings, {len(L.landuse)} landuse "
          f"({time.time()-t0:.0f}s)")
    road, walkG, edge_tags = build_graphs(L)
    # keep the largest connected component of each graph
    road = road.subgraph(max(nx.connected_components(road), key=len)).copy()
    walkG = walkG.subgraph(max(nx.connected_components(walkG), key=len)).copy()
    rtree = kdtree(road, L.node_xy)
    W = Walk(walkG, L)
    bgeoms = np.array([b[0] for b in L.buildings], dtype=object)
    btree = shapely.STRtree(bgeoms)
    water = shapely.union_all([g for g, _, _ in L.water_lines] + L.coastline) if (L.water_lines or L.coastline) else None
    rail = [(g, t) for g, t in L.rail_lines if t.get("railway") in ("rail", "light_rail", "subway", "construction")]
    dem = Raster(a.dem) if a.dem and Path(a.dem).exists() else None
    flood = Raster(a.flood) if a.flood and Path(a.flood).exists() else None
    stops = (gtfs_stops(a.gtfs, "BAS.MY") if a.gtfs else []) + (gtfs_stops(a.ktmb, "KTMB") if a.ktmb else [])
    stop_xy = np.array([(s["x"], s["y"]) for s in stops]) if stops else np.zeros((0, 2))
    stop_tree = cKDTree(stop_xy) if len(stop_xy) else None
    if flood:
        fa = flood.a[np.isfinite(flood.a)]
        report_flood = {"cells": int(fa.size), "cells_depth_gt0": int((fa > 0).sum()),
                        "max_depth_m": float(fa.max()) if fa.size else None}
    else:
        report_flood = None
    anchors = resolve_anchors(spec, L)
    print("anchors:", {k: v["resolved_by"] for k, v in anchors.items()})

    # named features for readable station labels
    label_feats = [(x, y, t) for x, y, t, _ in L.named_areas + L.points
                   if t.get("name") and (t.get("shop") == "mall" or t.get("place") in ("suburb", "neighbourhood", "quarter", "town", "village")
                                         or t.get("railway") == "station" or t.get("amenity") in ("bus_station", "hospital", "university", "college"))]
    lab_tree = cKDTree(np.array([(x, y) for x, y, _ in label_feats])) if label_feats else None

    def label_for(x, y):
        if lab_tree is None:
            return ""
        d, i = lab_tree.query([x, y], k=min(5, len(label_feats)))
        for dd, ii in zip(np.atleast_1d(d), np.atleast_1d(i)):
            if dd < 700:
                return label_feats[ii][2]["name"]
        return ""

    # Bukit Chagar reference points for interchange walking access
    def pt_named(rx, key=None, val=None):
        r = re.compile(rx, re.I)
        for x, y, t, oid in L.points + L.named_areas:
            if r.search(t.get("name", "")) and (key is None or t.get(key) == val):
                return (x, y, oid)
        return None
    hubs = {
        "RTS Bukit Chagar (station node)": (anchors["BKC"]["x"], anchors["BKC"]["y"], anchors["BKC"]["osm_id"]),
        "JB Sentral (KTM)": pt_named(r"^Johor Bahru Sentral$", "railway", "station"),
        "JB Sentral Bus Terminal": pt_named(r"^JB Sentral Bus Terminal$", "amenity", "bus_station"),
        "Bukit Chagar ICQ building": pt_named(r"Bukit Chagar Immigration"),
        "Larkin Sentral bus terminal": pt_named(r"^Larkin Sentral$", "amenity", "bus_station"),
    }
    rts_entrances = [(x, y, t, oid) for x, y, t, oid in L.ped_nodes
                     if ("entrance" in t or t.get("railway") in ("subway_entrance", "train_station_entrance"))
                     and math.hypot(x - anchors["BKC"]["x"], y - anchors["BKC"]["y"]) < 250]

    only = set(a.only.split(",")) if a.only else None
    feats_line, feats_st, feats_depot = [], [], []
    comp, pinch_rows, flood_rows, ix_rows, seg_all = [], [], [], [], []
    report = {"run_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "anchors": anchors,
              "inputs": {"osm": a.osm, "dem": bool(dem), "flood_jrc": bool(flood), "gtfs_stops": len(stops),
                         "flood_jrc_raster_summary": report_flood},
              "options": {}}

    for opt in spec["options"]:
        if only and opt["id"] not in only:
            continue
        oid = opt["id"]
        t1 = time.time()
        try:
            line, pnodes, ways, _ = route_option(opt, anchors, road, L, rtree)
        except nx.NetworkXNoPath as e:
            report["options"][oid] = {"error": f"no path: {e}"}
            continue
        Lkm = line.length / 1000
        rep_km = spec["reported_lengths_km"][opt["corridor"]]
        dev = (Lkm - rep_km) / rep_km
        forced_off = {k: line.distance(Point(anchors[k]["x"], anchors[k]["y"])) for k in opt.get("forced_stations", [])}
        # an anchor far from the line cannot be served by a station on it: report, do not force
        not_served = sorted(k for k, d in forced_off.items() if d > FORCED_MAX_OFFSET_M)
        forced_ch = [chainage_of(line, anchors[k]["x"], anchors[k]["y"]) for k in forced_off if k not in not_served]
        stations = place_stations(line, forced_ch, W, water)

        # segments, pinch points
        seg = segment_screens(line, ways, pnodes, L, edge_tags, btree, bgeoms)
        seg["option_id"] = oid
        st_ch = np.array([s[0] for s in stations])
        seg["near_station"] = seg["chainage_m"].apply(lambda c: bool(np.min(abs(st_ch - c)) <= 60))
        need = np.where(seg["near_station"], CLEAR_WIDTH_STATION_M[1], CLEAR_WIDTH_LINE_M[1])
        seg["pinch_width"] = seg["clear_width_m"] < need
        seg["pinch_width_low"] = seg["clear_width_m"] < np.where(seg["near_station"], CLEAR_WIDTH_STATION_M[0], CLEAR_WIDTH_LINE_M[0])
        seg["single_narrow"] = (seg["carriageway"] == "single") & (seg["lanes_tag"].fillna(2) <= 2)
        seg["min_side_setback_m"] = seg[["setback_left_m", "setback_right_m"]].min(axis=1)
        seg["pinch_side"] = seg["min_side_setback_m"] < np.where(seg["near_station"], SIDE_SETBACK_M[1], SIDE_SETBACK_M[0])
        seg["flag_width"] = seg["pinch_width"] | seg["single_narrow"] | seg["pinch_side"]

        # curves
        curv = curvature_flags(line)
        cdf = pd.DataFrame(curv, columns=["chainage_m", "radius_m", "x", "y"])
        cdf["flag"] = cdf["radius_m"] < CURVE_R_FLAG_M[1]
        tight50 = int((cdf["radius_m"] < CURVE_R_FLAG_M[0]).sum())

        # structure conflicts: rail crossings, river crossings, flyovers along/over the route
        crossings = []
        for g, t in rail:
            ip = line.intersection(g)
            for p in getattr(ip, "geoms", [ip]):
                if not p.is_empty and p.geom_type == "Point":
                    crossings.append(("rail crossing", line.project(p), p, t.get("name", t.get("railway"))))
        for g, kind, nm in L.water_lines:
            if kind in ("river", "canal") and line.intersects(g):
                ip = line.intersection(g)
                for p in getattr(ip, "geoms", [ip]):
                    if not p.is_empty and p.geom_type == "Point":
                        crossings.append((f"{kind} crossing", line.project(p), p, nm))
        for sp in merge_spans(seg, "bridge_or_flyover"):
            r0 = sp["rows"][0]
            crossings.append(("existing flyover/bridge on route", float(sp["start"]), Point(r0["x"], r0["y"]),
                              r0["road_name"]))

        # pinch-point list
        for sp in merge_spans(seg, "flag_width"):
            rows = pd.DataFrame(sp["rows"])
            r0 = rows.iloc[len(rows) // 2]
            lo, la = lonlat(r0["x"], r0["y"])
            pinch_rows.append({
                "option_id": oid, "type": "narrow cross-section", "chainage_from_m": sp["start"] - 50,
                "chainage_to_m": sp["end"] + 50, "lon": lo, "lat": la,
                "road": "; ".join(sorted(set(rows["road_name"]) - {""}))[:80],
                "min_clear_width_m": rows["clear_width_m"].min(), "min_side_setback_m": rows["min_side_setback_m"].min(),
                "lanes_tag_min": rows["lanes_tag"].min(),
                "why": "; ".join(k for k, c in (("facade-to-facade < base width", "pinch_width"),
                                                ("facade close on one side", "pinch_side"),
                                                ("single carriageway <=2 lanes", "single_narrow")) if rows[c].any()),
                "carriageway": "/".join(sorted(set(rows["carriageway"]))),
                "at_station": bool(rows["near_station"].any()),
                "severity": "high" if rows["pinch_width_low"].any() else "medium",
                "status": "inferred", "evidence": "OSM building footprints vs. route centerline (60 m rays); OSM lanes/oneway tags",
                "sc4_substitute": "web-only: OSM tags + footprint setbacks; no field photo (owner decision 6)"})
        for sp in merge_spans(cdf.rename(columns={}), "flag", gap=60):
            rows = pd.DataFrame(sp["rows"])
            r0 = rows.loc[rows["radius_m"].idxmin()]
            lo, la = lonlat(r0["x"], r0["y"])
            pinch_rows.append({
                "option_id": oid, "type": "tight curve", "chainage_from_m": sp["start"] - 40,
                "chainage_to_m": sp["end"] + 40, "lon": lo, "lat": la, "road": "",
                "min_radius_m": round(rows["radius_m"].min()),
                "severity": "high" if rows["radius_m"].min() < CURVE_R_FLAG_M[0] else "medium",
                "status": "inferred", "evidence": "Route follows road centerline; radius from 3-point circle at 40 m spacing",
                "sc4_substitute": "web-only"})
        for kind, ch, p, nm in crossings:
            lo, la = lonlat(p.x, p.y)
            pinch_rows.append({"option_id": oid, "type": kind, "chainage_from_m": round(ch), "chainage_to_m": round(ch),
                               "lon": lo, "lat": la, "road": nm or "", "severity": "medium", "status": "inferred",
                               "evidence": "OSM geometry intersection", "sc4_substitute": "web-only"})

        # grades
        gstats = {}
        if dem:
            s_, z, zs, g = grade_profile(line, dem)
            ag = np.abs(g)
            gstats = {"max_ground_grade_200m": round(float(np.nanmax(ag)), 4) if np.isfinite(ag).any() else None,
                      "len_over_5pct_m": int(np.nansum(ag > GRADE_FLAG[0]) * 25),
                      "len_over_8pct_m": int(np.nansum(ag > GRADE_FLAG[1]) * 25),
                      "z_min_m": round(float(np.nanmin(zs)), 1), "z_max_m": round(float(np.nanmax(zs)), 1)}
            for sp in merge_spans(pd.DataFrame({"chainage_m": s_, "f": ag > GRADE_FLAG[0]}).fillna(False), "f", gap=75):
                p = line.interpolate(sp["start"])
                lo, la = lonlat(p.x, p.y)
                pinch_rows.append({"option_id": oid, "type": "steep ground grade (>5% over 200 m, DSM)",
                                   "chainage_from_m": round(sp["start"]), "chainage_to_m": round(sp["end"]),
                                   "lon": lo, "lat": la, "road": "", "severity": "low", "status": "inferred",
                                   "evidence": "Copernicus GLO-30 DSM, 250 m rolling median; surface model includes buildings and trees",
                                   "sc4_substitute": "web-only"})

        # stations
        st_records = []
        for k, (ch, sc, dist, forced) in enumerate(stations):
            p = line.interpolate(ch)
            lo, la = lonlat(p.x, p.y)
            ratio = W.catchment_ratio(dist, p.x, p.y)
            # bus routes within 400 m walk, KTM within 800 m walk
            routes, ktm = set(), set()
            if stop_tree is not None:
                for j in stop_tree.query_ball_point([p.x, p.y], WALK_CUTOFF_M):
                    sn, _ = W.snap(stops[j]["x"], stops[j]["y"])
                    dd = dist.get(sn)
                    if dd is None:
                        continue
                    if stops[j]["agency"] == "BAS.MY" and dd <= BUS_WALK_M:
                        routes.update(stops[j]["routes"])
                    if stops[j]["agency"] == "KTMB":
                        ktm.add(stops[j]["name"])
            z = float(dem.sample([p.x], [p.y])[0]) if dem else None
            fd = float(flood.sample([p.x], [p.y])[0]) if flood else None
            near_w = float(water.distance(p)) if water is not None else None
            low = (z is not None and z <= LOW_LYING_M) and (near_w is not None and near_w <= NEAR_WATER_M)
            jrc = fd is not None and np.isfinite(fd) and fd > 0
            rec = {"option_id": oid, "corridor": opt["corridor"], "seq": k + 1,
                   "station_id": f"{oid}-S{k+1:02d}", "label_near": label_for(p.x, p.y),
                   "chainage_m": round(ch), "forced": forced, "lon": lo, "lat": la,
                   "floor_area_proxy_800m_m2": round(sc), "network_catchment_ratio": round(ratio, 3),
                   "bus_routes_400m_walk": len(routes), "ktm_800m_walk": "|".join(sorted(ktm)),
                   "dsm_elev_m": None if z is None or not np.isfinite(z) else round(z, 1),
                   "dist_to_water_m": None if near_w is None else round(near_w),
                   "flood_jrc_rp100_depth_m": None if fd is None or not np.isfinite(fd) else round(fd, 2),
                   "flood_flag": "JRC RP100" if jrc else ("low-lying near water (DEM proxy)" if low else ""),
                   "status": "concept"}
            st_records.append(rec)
            feats_st.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": [lo, la]},
                             "properties": {**rec, "source_ids": "SRC-024|SRC-038|SRC-039|SRC-041",
                                            "basis": "placed by exclusive 800 m network-walk catchment DP, 1.0-1.5 km spacing"}})
            if rec["flood_flag"]:
                flood_rows.append({"option_id": oid, "kind": "station", "id": rec["station_id"], "lon": lo, "lat": la,
                                   "flag": rec["flood_flag"], "dsm_elev_m": rec["dsm_elev_m"],
                                   "dist_to_water_m": rec["dist_to_water_m"], "jrc_depth_m": rec["flood_jrc_rp100_depth_m"],
                                   "status": "inferred",
                                   "sc5_substitute": "web-only: JRC global river-flood map + DEM proxy; no local observation"})
        # line flood share
        s_f = np.arange(0, line.length, 50.0)
        pts = [line.interpolate(v) for v in s_f]
        line_low = 0.0
        line_jrc = 0.0
        if dem and water is not None:
            zz = dem.sample([p.x for p in pts], [p.y for p in pts])
            ww = np.array([water.distance(p) for p in pts])
            lowf = (zz <= LOW_LYING_M) & (ww <= NEAR_WATER_M)
            line_low = float(np.mean(lowf))
        else:
            lowf = np.zeros(len(pts), bool)
        if flood:
            ff = flood.sample([p.x for p in pts], [p.y for p in pts])
            jrcf = np.nan_to_num(ff) > 0
            line_jrc = float(np.mean(jrcf))
        else:
            jrcf = np.zeros(len(pts), bool)
        fdf = pd.DataFrame({"chainage_m": s_f, "jrc": jrcf, "low": lowf})
        for col, lab in (("jrc", "JRC RP100 river-flood extent"), ("low", "low-lying near water (DEM proxy)")):
            for sp in merge_spans(fdf, col, gap=100):
                mid = line.interpolate((sp["start"] + sp["end"]) / 2)
                lo, la = lonlat(mid.x, mid.y)
                flood_rows.append({"option_id": oid, "kind": "line span", "id": f"{oid}@{round(sp['start'])}-{round(sp['end'])}m",
                                   "lon": lo, "lat": la, "flag": lab, "length_m": round(sp["end"] - sp["start"]) + 50,
                                   "status": "inferred",
                                   "sc5_substitute": "web-only: JRC global river-flood map + DEM proxy; no local observation"})

        # depot candidates
        depots = []
        for poly, kind, nm, lid in L.landuse:
            if kind not in DEPOT_LANDUSE and not kind.startswith("natural=") or kind == "natural=water":
                continue
            ha = poly.area / 1e4
            if ha < DEPOT_MIN_HA[0]:
                continue
            d = poly.distance(line)
            if d > DEPOT_MAX_DIST_M:
                continue
            bcov = sum(bgeoms[h].intersection(poly).area for h in btree.query(poly, predicate="intersects")) / poly.area
            if bcov > 0.05:
                continue
            ch = line.project(poly.centroid)
            depots.append({"option_id": oid, "landuse": kind, "name": nm, "osm_id": int(lid), "area_ha": round(ha, 1),
                           "dist_to_line_m": round(d), "chainage_m": round(ch),
                           "near_terminus": bool(ch > 0.75 * line.length),
                           "meets_base_8ha": ha >= DEPOT_MIN_HA[1], "meets_lrt_15ha": ha >= DEPOT_MIN_HA[2],
                           "building_cover": round(bcov, 3), "geom": poly})
        depots.sort(key=lambda r: (not r["meets_base_8ha"], not r["near_terminus"], r["dist_to_line_m"]))
        for r in depots[:5]:
            g = shapely.transform(r.pop("geom"), lambda c: np.column_stack(TO_WGS.transform(c[:, 0], c[:, 1])))
            feats_depot.append({"type": "Feature", "geometry": mapping(g.simplify(1e-5)),
                                "properties": {**r, "status": "inferred", "source_ids": "SRC-024",
                                               "note": "OSM landuse only; ownership (state/federal land) is NOT in OSM"}})
        for r in depots[5:]:
            r.pop("geom", None)

        # interchange walking access at Bukit Chagar (first station)
        s0 = line.interpolate(stations[0][0])
        dist0, d0 = W.reach(s0.x, s0.y, cutoff=3000)
        targets = dict(hubs)
        for k, (x, y, t, nid) in enumerate(rts_entrances):
            targets[f"RTS entrance node {nid} ({t.get('name', t.get('entrance', t.get('railway', '')))})"] = (x, y, nid)
        for nm, h in targets.items():
            if not h:
                ix_rows.append({"option_id": oid, "from": f"{oid}-S01", "to": nm, "status": "not found in OSM"})
                continue
            tn, td = W.snap(h[0], h[1])
            nd = dist0.get(tn)
            straight = math.hypot(h[0] - s0.x, h[1] - s0.y)
            ix_rows.append({"option_id": oid, "from": f"{oid}-S01", "to": nm,
                            "network_walk_m": None if nd is None else round(nd + d0 + td),
                            "straight_m": round(straight),
                            "detour_ratio": None if nd is None or straight < 1 else round((nd + d0 + td) / straight, 2),
                            "walk_min_at_3_6kmh": None if nd is None else round((nd + d0 + td) / 60, 1),
                            "status": "inferred"})

        # line feature
        gl = shapely.transform(line, lambda c: np.column_stack(TO_WGS.transform(c[:, 0], c[:, 1])))
        sp = np.diff(sorted(s[0] for s in stations))
        lab_all = [r["label_near"] for r in st_records]
        props = {
            "option_id": oid, "corridor": opt["corridor"], "name": opt["name"], "decision": opt["decision"],
            "status": "concept", "source_ids": "SRC-024|SRC-021|SRC-041|SRC-042",
            "length_km": round(Lkm, 2), "reported_length_km": rep_km, "length_deviation": round(dev, 3),
            "within_15pct": abs(dev) <= spec["length_tolerance"],
            "n_stations": len(stations), "mean_spacing_m": round(float(sp.mean())) if len(sp) else None,
            "rationale": opt["rationale"],
        }
        feats_line.append({"type": "Feature", "geometry": mapping(gl.simplify(2e-5)), "properties": props})
        segs_flag = seg["flag_width"].mean() if len(seg) else 0
        comp.append({
            **{k: props[k] for k in ("option_id", "corridor", "name", "decision", "length_km", "reported_length_km",
                                     "length_deviation", "within_15pct", "n_stations", "mean_spacing_m")},
            "unique_floor_area_proxy_km2": round(float(W.bw[list(set().union(*[set(W.buildings_in(s[2]).tolist()) for s in stations]))].sum()) / 1e6, 3),
            "median_catchment_ratio": round(float(np.median([r["network_catchment_ratio"] for r in st_records])), 3),
            "stations_ratio_below_035": int(sum(r["network_catchment_ratio"] < 0.35 for r in st_records)),
            "stations_with_ktm_800m": int(sum(bool(r["ktm_800m_walk"]) for r in st_records)),
            "median_bus_routes_400m": float(np.median([r["bus_routes_400m_walk"] for r in st_records])),
            "share_len_on_trunk_primary": round(float(seg["highway"].isin(["trunk", "primary", "motorway"]).mean()), 3),
            "share_len_dual_carriageway": round(float((seg["carriageway"] != "single").mean()), 3),
            "share_len_width_flag": round(float(segs_flag), 3),
            "n_pinch_width_spans": len(merge_spans(seg, "flag_width")),
            "n_tight_curves_lt100m": len(merge_spans(cdf, "flag", gap=60)), "n_curve_points_lt50m": tight50,
            "n_rail_or_river_crossings": sum(1 for c in crossings if "crossing" in c[0]),
            "n_existing_flyover_spans_on_route": sum(1 for c in crossings if c[0].startswith("existing flyover")),
            "anchors_not_served_gt500m": "|".join(anchors[k]["label"] for k in not_served),
            **gstats,
            "share_line_low_lying_near_water": round(line_low, 3), "share_line_jrc_rp100": round(line_jrc, 3),
            "stations_flood_flag": int(sum(bool(r["flood_flag"]) for r in st_records)),
            "depot_candidates_ge5ha_1500m": len(depots), "depot_candidates_ge8ha": int(sum(r["meets_base_8ha"] for r in depots)),
            "station_labels": " | ".join(lab_all),
        })
        seg_all.append(seg.drop(columns=["x", "y"]))
        report["options"][oid] = {"seconds": round(time.time() - t1, 1), "length_km": round(Lkm, 2),
                                  "n_stations": len(stations),
                                  "forced_anchor_offset_from_line_m": {k: round(v) for k, v in forced_off.items()},
                                  "anchors_not_served_gt500m": not_served}
        print(oid, f"{Lkm:.2f} km", f"dev {dev:+.1%}", len(stations), "stations", f"{time.time()-t1:.0f}s")

    def fc(feats):
        return {"type": "FeatureCollection",
                "license": "Derived from OpenStreetMap (c) OpenStreetMap contributors, ODbL 1.0",
                "status_note": "All lines and stations are status=concept: hypotheses drawn by this project. Not official.",
                "features": feats}
    (cdir / "alignments.geojson").write_text(json.dumps(fc(feats_line), indent=1))
    (cdir / "stations.geojson").write_text(json.dumps(fc(feats_st), indent=1))
    (cdir / "depot-candidates.geojson").write_text(json.dumps(fc(feats_depot)))
    pd.DataFrame(comp).to_csv(out / "option_comparison.csv", index=False)
    pd.DataFrame(pinch_rows).to_csv(out / "pinch_points.csv", index=False)
    pd.DataFrame(flood_rows).to_csv(out / "flood_spots.csv", index=False)
    pd.DataFrame(ix_rows).to_csv(out / "interchange_access.csv", index=False)
    pd.DataFrame([r for f in feats_st for r in [f["properties"]]]).to_csv(out / "stations.csv", index=False)
    if seg_all:
        pd.concat(seg_all).to_csv(out / "segments.csv", index=False)
    report["seconds_total"] = round(time.time() - t0, 1)
    (out / "run_report.json").write_text(json.dumps(report, indent=2, default=str))
    try:
        draw_map(feats_line, feats_st, feats_depot, L, out / "options-map.png")
    except Exception as e:  # noqa: BLE001
        print("map failed:", e)


def draw_map(lines, stations, depots, L, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(13, 10), dpi=110)
    for w in L.ways:
        if w["tags"].get("highway") in ("motorway", "trunk", "primary", "secondary"):
            xy = np.array([TO_WGS.transform(*L.node_xy[n]) for n in w["nodes"]])
            ax.plot(xy[:, 0], xy[:, 1], color="#bbbbbb", lw=0.5, zorder=1)
    for g in L.coastline:
        xy = np.array(TO_WGS.transform(*np.array(g.coords).T)).T
        ax.plot(xy[:, 0], xy[:, 1], color="#6fa8dc", lw=0.6, zorder=1)
    colors = {"T1": "#d62728", "T2": "#ff7f0e", "T3": "#8c564b", "IP1": "#1f77b4", "IP2": "#17becf", "IP3": "#2ca02c", "IP4": "#9467bd"}
    for f in lines:
        p = f["properties"]
        c = np.array(f["geometry"]["coordinates"])
        rej = p["decision"] == "rejected"
        ax.plot(c[:, 0], c[:, 1], color=colors.get(p["option_id"], "#777777"), lw=1.2 if rej else 2.4,
                ls=":" if rej else "-", zorder=3, label=f'{p["option_id"]} {p["name"]} ({p["length_km"]} km){" [rejected]" if rej else ""}')
    for f in stations:
        p = f["properties"]
        if p["option_id"] in colors:
            ax.scatter(*f["geometry"]["coordinates"], s=14, color=colors[p["option_id"]], edgecolor="k", lw=0.4, zorder=4)
    for f in depots:
        g = shapely.geometry.shape(f["geometry"])
        for gg in getattr(g, "geoms", [g]):
            ax.fill(*gg.exterior.xy, color="#999900", alpha=0.35, zorder=2)
    ax.set_aspect("equal")
    ax.set_title("Stage 2 alignment hypotheses - ALL STATUS = CONCEPT (not official E-ART alignments)\n"
                 "Data (c) OpenStreetMap contributors, ODbL. Olive = depot-candidate land (OSM landuse; ownership unknown).",
                 fontsize=10)
    ax.legend(fontsize=7, loc="lower right")
    fig.tight_layout()
    fig.savefig(path)


if __name__ == "__main__":
    main()
