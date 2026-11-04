"""Test the reported 14.78 km Iskandar Puteri line length against road geometry.

Shortest path BY LENGTH ONLY (no preference weights) on the OSM road graph from the
Bukit Chagar RTS station to candidate Iskandar Puteri centers. If the shortest road
route to a center is far longer than 14.78 km, a single Bukit Chagar line that follows
road reserves cannot reach that center within the reported length (A-036, inferred).
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import networkx as nx
import numpy as np
from scipy.spatial import cKDTree

sys.path.insert(0, str(Path(__file__).parent))
from osm_layers import ROAD_CLASSES, TO_UTM, read_osm  # noqa: E402

ORIGIN = ("Bukit Chagar RTS (OSM node 13377979326)", (103.76219, 1.46624))
TARGETS = {  # OSM feature locations (see options.json anchors)
    "Kota Iskandar": (103.65261, 1.42271), "Puteri Harbour": (103.65906, 1.41706),
    "Medini (Mall of Medini)": (103.63298, 1.4281), "EduCity": (103.61303, 1.43239),
    "Bukit Indah": (103.65956, 1.48007), "Perling (Perling Mall)": (103.68115, 1.49657),
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--osm", required=True)
    ap.add_argument("--out", default="results/stage2/ip_shortest_road_km.json")
    a = ap.parse_args()
    L = read_osm(a.osm)
    graphs = {"tertiary_and_above": nx.Graph(), "all_drivable": nx.Graph()}
    drive = ROAD_CLASSES | {"residential", "unclassified", "living_street"}
    for w in L.ways:
        hw = w["tags"].get("highway", "")
        if hw not in drive:
            continue
        for u, v in zip(w["nodes"][:-1], w["nodes"][1:]):
            d = math.dist(L.node_xy[u], L.node_xy[v])
            nm = w["tags"].get("name", hw)
            graphs["all_drivable"].add_edge(u, v, length=d, name=nm)
            if hw in ROAD_CLASSES:
                graphs["tertiary_and_above"].add_edge(u, v, length=d, name=nm)
    res = {}
    ox, oy = TO_UTM.transform(*ORIGIN[1])
    for gname, G in graphs.items():
        G = G.subgraph(max(nx.connected_components(G), key=len))
        ids = np.array(list(G.nodes))
        tree = cKDTree(np.array([L.node_xy[i] for i in ids]))
        s = int(ids[tree.query([ox, oy])[1]])
        dist, paths = nx.single_source_dijkstra(G, s, weight="length")
        for lab, ll in TARGETS.items():
            tx, ty = TO_UTM.transform(*ll)
            t = int(ids[tree.query([tx, ty])[1]])
            r = res.setdefault(lab, {"straight_km": round(math.hypot(tx - ox, ty - oy) / 1000, 2)})
            r[f"{gname}_km"] = round(dist[t] / 1000, 2)
            if gname == "tertiary_and_above":
                names = []
                for u, v in zip(paths[t][:-1], paths[t][1:]):
                    n = G[u][v]["name"]
                    if not names or names[-1] != n:
                        names.append(n)
                r["roads_tertiary_and_above"] = " > ".join(names)
    out = {"from": ORIGIN[0], "reported_IP_length_km": 14.78, "tolerance": 0.15,
           "method": "shortest path by length only on the OSM road graph; no preference weights",
           "status": "inferred", "results": res}
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
