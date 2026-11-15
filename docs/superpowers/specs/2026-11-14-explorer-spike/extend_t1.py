"""Spike: cut T1 after station 13 (AEON Tebrau City) and extend along the main road to Ulu Tiram.
New stations every ~1.2 km (1.0-1.5 km band), named after the nearest unused OSM place within 700 m."""
import sys, json, math
import numpy as np, networkx as nx, osmium
from shapely.geometry import LineString, Point
from pyproj import Transformer
sys.stdout.reconfigure(encoding="utf-8")
repo, out = sys.argv[1], sys.argv[2]
FW = Transformer.from_crs(4326, 3375, always_xy=True); BW = Transformer.from_crs(3375, 4326, always_xy=True)
END = (103.82088, 1.59936)  # OSM place=town "Ulu Tiram"
BB = (103.78, 1.53, 103.85, 1.615)
W = {"motorway": 3.0, "trunk": 0.4, "trunk_link": 2.0, "primary": 0.5, "primary_link": 2.0, "secondary": 1.0, "tertiary": 1.3}

G = nx.Graph(); xy = {}; places = []; roadname = {}
for o in osmium.FileProcessor(f"{repo}/data/raw/osm/jb-study.osm.pbf").with_locations():
    if isinstance(o, osmium.osm.Node) and "place" in o.tags and "name" in o.tags:
        if BB[0] < o.location.lon < BB[2] and BB[1] < o.location.lat < BB[3]:
            places.append((o.tags["name"], np.array(FW.transform(o.location.lon, o.location.lat))))
    if isinstance(o, osmium.osm.Way) and o.tags.get("highway") in W:
        try: nodes = [(n.ref, n.lon, n.lat) for n in o.nodes]
        except Exception: continue
        if not any(BB[0] < x < BB[2] and BB[1] < y < BB[3] for _, x, y in nodes): continue
        f = W[o.tags["highway"]]
        for (a, ax, ay), (b, bx, by) in zip(nodes, nodes[1:]):
            pa, pb = np.array(FW.transform(ax, ay)), np.array(FW.transform(bx, by))
            xy[a], xy[b] = pa, pb
            G.add_edge(a, b, w=np.hypot(*(pb - pa)) * f)
            roadname[(a, b)] = roadname[(b, a)] = o.tags.get("ref") or o.tags.get("name", "")
st = sorted([f["properties"] for f in json.load(open(f"{repo}/data/concept/stations.geojson"))["features"] if f["properties"]["option_id"] == "T1"], key=lambda p: p["seq"])
s13 = st[12]; assert s13["seq"] == 13
c13 = np.array(FW.transform(s13["lon"], s13["lat"])); cend = np.array(FW.transform(*END))
ids = list(xy); arr = np.array([xy[i] for i in ids])
near = lambda c: ids[int(np.argmin(np.hypot(*(arr - c).T)))]
path = nx.shortest_path(G, near(c13), near(cend), weight="w")
ext = np.array([xy[i] for i in path])
refs = [roadname.get((a, b), "") for a, b in zip(path, path[1:])]
from collections import Counter
print("roads used:", Counter(refs).most_common(5))

al = {f["properties"]["option_id"]: f for f in json.load(open(f"{repo}/data/concept/alignments.geojson"))["features"]}
raw = np.array([FW.transform(*c) for c in al["T1"]["geometry"]["coordinates"]])
rl = LineString(raw); d13 = rl.project(Point(c13))
head = [c for c in raw if rl.project(Point(c)) < d13] + [rl.interpolate(d13).coords[0]]
newraw = np.vstack([np.array(head), ext[1:], cend])
nl = LineString(newraw)
L_ext = nl.length - nl.project(Point(c13))
n = max(1, round(L_ext / 1200)); step = L_ext / n
print(f"extension {L_ext/1000:.2f} km, {n} new stations at {step:.0f} m spacing")
used = {p["label_near"] for p in st[:13]}
new_st = []
for k in range(1, n + 1):
    d = nl.project(Point(c13)) + k * step
    c = np.array(nl.interpolate(min(d, nl.length)).coords[0])
    if k == n: c = cend
    cands = sorted(((np.hypot(*(pc - c)), nm) for nm, pc in places if nm not in used), key=lambda t: t[0])
    name = cands[0][1] if cands and cands[0][0] < 700 else f"Jalan Kota Tinggi km {round((d - nl.project(Point(c13)))/1000 + 0, 1)}"
    if k == n: name = "Ulu Tiram"
    used.add(name)
    lon, lat = BW.transform(*c)
    new_st.append({"option_id": "T1", "seq": 13 + k, "label_near": name, "lon": lon, "lat": lat})
stations = st[:13] + new_st
json.dump({"coords": [list(BW.transform(*q)) for q in newraw], "stations": stations}, open(f"{out}/t1_override.json", "w"), ensure_ascii=False)
for p in stations[11:]: print(p["seq"], p["label_near"])
print("new T1 road length km", round(nl.length / 1000, 2))
