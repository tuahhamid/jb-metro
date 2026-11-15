"""Build mock data (GeoJSON) for the map mockup: T1/IP2 lines, stations, 3D concept extrusions, RTS geometry."""
import sys, json, osmium
from shapely.geometry import LineString, Point, shape, mapping, box
from shapely.ops import transform
from shapely import affinity
from pyproj import Transformer
sys.stdout.reconfigure(encoding="utf-8")
repo = sys.argv[1]; out = sys.argv[2]
fw = Transformer.from_crs(4326, 3375, always_xy=True).transform  # Kertau RSO Malaya (m)
bw = Transformer.from_crs(3375, 4326, always_xy=True).transform

al = json.load(open(f"{repo}/data/concept/alignments.geojson"))
st = json.load(open(f"{repo}/data/concept/stations.geojson"))
feats = []
lines = {}
for f in al["features"]:
    oid = f["properties"]["option_id"]
    if oid in ("T1", "IP2"):
        lines[oid] = shape(f["geometry"])
        feats.append({"type": "Feature", "geometry": f["geometry"], "properties": {"kind": "line", "line": oid}})

stations = []
for f in st["features"]:
    p = f["properties"]
    if p["option_id"] not in ("T1", "IP2"): continue
    if p["option_id"] == "IP2" and p["seq"] == 1: continue  # shared Bukit Chagar
    stations.append({"line": p["option_id"], "seq": p["seq"], "name": p["label_near"] or f"Station {p['seq']}", "lon": p["lon"], "lat": p["lat"]})

ext = []
for oid, ln in lines.items():
    lm = transform(fw, ln)
    via = lm.buffer(4.5, cap_style=2)
    ext.append({"type": "Feature", "geometry": mapping(transform(bw, via)), "properties": {"kind": "viaduct", "line": oid, "base": 11, "top": 13.5}})
    for s in [s for s in stations if s["line"] == oid or (oid == "IP2" and False)]:
        pt = transform(fw, Point(s["lon"], s["lat"]))
        d = lm.project(pt)
        a, b = lm.interpolate(max(d - 5, 0)), lm.interpolate(min(d + 5, lm.length))
        import math
        ang = math.degrees(math.atan2(b.y - a.y, b.x - a.x))
        r = affinity.rotate(box(pt.x - 60, pt.y - 13, pt.x + 60, pt.y + 13), ang, origin=pt)
        ext.append({"type": "Feature", "geometry": mapping(transform(bw, r)), "properties": {"kind": "station", "line": oid, "base": 9, "top": 22}})
        roof = affinity.rotate(box(pt.x - 66, pt.y - 16, pt.x + 66, pt.y + 16), ang, origin=pt)
        ext.append({"type": "Feature", "geometry": mapping(transform(bw, roof)), "properties": {"kind": "roof", "line": oid, "base": 22, "top": 23.5}})

# RTS Link and KTM rail from OSM near Bukit Chagar
rail = []
fp = osmium.FileProcessor(f"{repo}/data/raw/osm/jb-study.osm.pbf").with_locations().with_filter(osmium.filter.KeyFilter("railway"))
bb = box(103.755, 1.440, 103.790, 1.475)
for o in fp:
    if not isinstance(o, osmium.osm.Way): continue
    t = o.tags
    if t.get("railway") not in ("rail", "construction", "light_rail", "subway", "proposed"): continue
    try:
        coords = [(n.lon, n.lat) for n in o.nodes]
    except Exception:
        continue
    if len(coords) < 2: continue
    g = LineString(coords)
    if not g.intersects(bb): continue
    name = t.get("name", ""); kind = t.get("railway")
    is_rts = "RTS" in name.upper() or "rts" in t.get("construction", "").lower() or (kind in ("construction", "light_rail") )
    rail.append({"type": "Feature", "geometry": mapping(g), "properties": {"kind": "rts" if is_rts else "rail", "name": name, "railway": kind}})
print("rail ways:", len(rail), sorted({(r['properties']['railway'], r['properties']['name']) for r in rail}))

# RTS viaduct extrusion
for r in rail:
    if r["properties"]["kind"] == "rts":
        g = transform(fw, shape(r["geometry"])).buffer(5, cap_style=2)
        ext.append({"type": "Feature", "geometry": mapping(transform(bw, g)), "properties": {"kind": "rtsviaduct", "base": 14, "top": 17}})

json.dump({"type": "FeatureCollection", "features": feats + rail}, open(f"{out}/lines.geojson", "w"))
json.dump({"type": "FeatureCollection", "features": ext}, open(f"{out}/extrusions.geojson", "w"))
json.dump(stations, open(f"{out}/stations.json", "w"), ensure_ascii=False)
print("stations", len(stations), "extrusions", len(ext))
