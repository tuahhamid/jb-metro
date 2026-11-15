"""Build explorer data for one line set (for example JB) from Stage 2 concept routes.

    python pipeline/explorer/build_line.py --config pipeline/explorer/jb.json --out site/data/jb --report results/explorer

Order: read OSM + Stage 2 GeoJSON -> per line keep/drop stations, bypass, extend, place
new stations -> track geometry -> names -> massing -> write outputs and report.
Stage 2 files are read only. All E-ART geometry is status=concept.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path

import numpy as np
import shapely
from shapely import affinity
from shapely.geometry import LineString, Point, box, mapping
from shapely.strtree import STRtree

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path[:0] = [str(HERE), str(REPO / "pipeline" / "stage2")]

from extend import bypass, even_stations, route_on_roads, splice  # noqa: E402
from names import name_stations  # noqa: E402
from osm_layers import TO_UTM, TO_WGS, read_osm  # noqa: E402
from track import StationIn, TrackRules, build_track, track_report  # noqa: E402

RULES = TrackRules()
PLACE_KINDS = ("neighbourhood", "suburb", "quarter")
NAMING_ROADS = ("trunk", "primary", "secondary", "tertiary")
RTS_BBOX = box(103.755, 1.440, 103.790, 1.475)
MASSING = {
    "viaduct": {"width": 9.0, "base": 11.0, "top": 13.5},
    "station": {"l": 100.0, "w": 24.0, "base": 9.0, "top": 21.0},
    "roof": {"l": 112.0, "w": 30.0, "base": 21.0, "top": 22.5},
    "rts_viaduct": {"width": 10.0, "base": 14.0, "top": 17.0},
}


def to_utm(lon, lat):
    return TO_UTM.transform(lon, lat)


def to_wgs(g):
    return shapely.transform(g, lambda c: np.column_stack(TO_WGS.transform(c[:, 0], c[:, 1])))


def wgs_geom(g):
    return mapping(to_wgs(g))


def round_coords(obj, nd=6):
    if isinstance(obj, (list, tuple)):
        return [round_coords(o, nd) for o in obj]
    return round(obj, nd) if isinstance(obj, float) else obj


def feature(geom, **props):
    g = wgs_geom(geom) if not isinstance(geom, dict) else geom
    g = {"type": g["type"], "coordinates": round_coords(g["coordinates"])}
    return {"type": "Feature", "geometry": g, "properties": props}


def write_fc(path: Path, feats: list):
    path.write_text(json.dumps({"type": "FeatureCollection", "features": feats}, ensure_ascii=False,
                               separators=(",", ":")), encoding="utf-8")


def osm_places(L):
    out = []
    for x, y, tags, _ in L.points:
        if tags.get("place") in PLACE_KINDS and tags.get("name"):
            out.append((tags["name"], x, y))
    for x, y, tags, _ in L.named_areas:
        if tags.get("place") in PLACE_KINDS and tags.get("name"):
            out.append((tags["name"], x, y))
    return out


def osm_roads(L):
    out = []
    for w in L.ways:
        t = w["tags"]
        if t.get("highway") in NAMING_ROADS and t.get("name"):
            pts = [L.node_xy[n] for n in w["nodes"] if n in L.node_xy]
            if len(pts) >= 2:
                out.append((t["name"], LineString(pts)))
    return out


def line_route(cfg, L, alignments, stage2_stations):
    """Return (road_xy, stations) for one line. stations: list of dicts key, seq, x, y."""
    opt = cfg["stage2_option"]
    road = np.array([to_utm(*c) for c in alignments[opt]["geometry"]["coordinates"]], float)
    src = sorted((p for p in stage2_stations if p["option_id"] == opt), key=lambda p: p["seq"])
    by_seq = {p["seq"]: np.array(to_utm(p["lon"], p["lat"])) for p in src}
    seqs = [p["seq"] for p in src]
    if "keep_seq" in cfg:
        seqs = [s for s in seqs if s in cfg["keep_seq"]]
    if "drop_seq" in cfg:
        seqs = [s for s in seqs if s not in cfg["drop_seq"]]
    pts = [tuple(by_seq[s]) for s in seqs]
    if "bypass" in cfg:
        road = bypass(road, tuple(by_seq[cfg["bypass"]["from_seq"]]), tuple(by_seq[cfg["bypass"]["to_seq"]]))
    if "extend_to" in cfg:
        e = cfg["extend_to"]
        end = np.array(to_utm(e["lon"], e["lat"]))
        cut = pts[-1]
        ext = route_on_roads(L, cut, tuple(end))
        road = splice(road, cut, np.vstack([ext, end]))
        pts += even_stations(road, cut, tuple(end))
    stations = [{"key": f"{cfg['id']}-{i:02d}", "seq": i, "x": float(x), "y": float(y)}
                for i, (x, y) in enumerate(pts, start=1)]
    return road, stations


def station_box(x, y, ux, uy, length, width):
    ang = math.degrees(math.atan2(uy, ux))
    return affinity.rotate(box(x - length / 2, y - width / 2, x + length / 2, y + width / 2), ang, origin=Point(x, y))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--report", required=True)
    a = ap.parse_args(argv)
    cfg = json.loads((REPO / a.config).read_text(encoding="utf-8"))
    out, rep_dir = Path(a.out), Path(a.report)
    out.mkdir(parents=True, exist_ok=True)
    rep_dir.mkdir(parents=True, exist_ok=True)

    print("reading OSM ...", flush=True)
    L = read_osm(str(REPO / cfg["osm"]))
    alignments = {f["properties"]["option_id"]: f for f in
                  json.loads((REPO / "data/concept/alignments.geojson").read_text(encoding="utf-8"))["features"]}
    stage2_st = [f["properties"] for f in
                 json.loads((REPO / "data/concept/stations.geojson").read_text(encoding="utf-8"))["features"]]
    landmarks = json.loads((REPO / cfg["landmarks"]).read_text(encoding="utf-8"))
    lm_xy = [(m["name"], *to_utm(m["lon"], m["lat"])) for m in landmarks]
    places, roads = osm_places(L), osm_roads(L)
    bld_tree = STRtree([b[0] for b in L.buildings])

    net, mass, dbg, report, csv_rows = [], [], [], {}, []
    shared = cfg.get("shared_first_station")
    for lc in cfg["lines"]:
        lid = lc["id"]
        print(f"{lid}: route + track ...", flush=True)
        road, stations = line_route(lc, L, alignments, stage2_st)
        res = build_track(road, [StationIn(s["key"], s["x"], s["y"]) for s in stations], RULES)
        g = LineString(res.xy)
        near = [L.buildings[i] for i in bld_tree.query(g.buffer(5))]
        rep = track_report(res, road, near, RULES)
        rep["stations"] = len(stations)
        report[lid] = rep
        names, rules = name_stations(stations, lm_xy, places, roads, res.xy, cfg.get("name_overrides", {}),
                                     return_rules=True)

        net.append(feature(g, kind="line", line_id=lid, name=lc["name"], status=lc["status"]))
        mass.append(feature(g.buffer(MASSING["viaduct"]["width"] / 2, cap_style=2), kind="viaduct", line_id=lid,
                            base=MASSING["viaduct"]["base"], top=MASSING["viaduct"]["top"]))
        for s in stations:
            x, y, ux, uy = res.stations[s["key"]]
            lon, lat = TO_WGS.transform(x, y)
            nm = names[s["key"]]
            net.append(feature(Point(x, y), kind="station", line_id=lid, station_id=s["key"], seq=s["seq"],
                               name=nm, status=lc["status"], ux=round(ux, 5), uy=round(uy, 5)))
            csv_rows.append([s["key"], lid, s["seq"], nm, rules[s["key"]], round(lon, 6), round(lat, 6)])
            if s["seq"] == 1 and nm == shared and lc is not cfg["lines"][0]:
                continue  # shared first station: massing drawn once
            for kind in ("station", "roof"):
                m = MASSING[kind]
                mass.append(feature(station_box(x, y, ux, uy, m["l"], m["w"]), kind=kind, line_id=lid,
                                    base=m["base"], top=m["top"]))
        dbg.append(feature(LineString(road), kind="road_route", line_id=lid))
        for poly, _, oid in near:
            if oid in rep["buildings_crossed"]:
                dbg.append(feature(poly.representative_point(), kind="crossing", line_id=lid, osm_id=oid))
        rep["buildings_crossed"] = len(rep["buildings_crossed"])
        print(f"{lid}: {rep['length_km_after']} km, {rep['curves']} curves, {rep['curves_r100']} at R100, "
              f"{rep['buildings_crossed']} buildings crossed", flush=True)

    for ls, tags in L.rail_lines:
        wgs = to_wgs(ls)
        if tags.get("railway") == "construction" and wgs.intersects(RTS_BBOX):
            net.append(feature(ls.simplify(2.0), kind="context_rail", line_id="RTS", name="RTS Link",
                               status="under construction"))
            m = MASSING["rts_viaduct"]
            mass.append(feature(ls.buffer(m["width"] / 2, cap_style=2), kind="rts_viaduct", line_id="RTS",
                                base=m["base"], top=m["top"]))
        elif tags.get("railway") == "rail":
            net.append(feature(ls.simplify(2.0), kind="context_rail", line_id="KTM",
                               name=tags.get("name", "KTM"), status="existing"))
    for m in landmarks:
        net.append(feature({"type": "Point", "coordinates": [m["lon"], m["lat"]]}, kind="landmark",
                           landmark_id=m["id"], name=m["name"], photo=m["photo"], line_id=None))

    write_fc(out / "network.geojson", net)
    write_fc(out / "massing.geojson", mass)
    write_fc(out / "debug.geojson", dbg)
    (rep_dir / f"{cfg['line_set']}_track_report.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    with open(rep_dir / f"{cfg['line_set']}_station_names.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["station_id", "line_id", "seq", "name", "rule_used", "lon", "lat"])
        w.writerows(csv_rows)
    print("done", flush=True)


if __name__ == "__main__":
    main()
