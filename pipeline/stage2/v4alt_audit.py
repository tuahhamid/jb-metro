"""V4-alt: OSM pedestrian-network audit around Bukit Chagar (substitute for site check SC-1).

Registered criteria (docs/validation-plan.md, V4-alt):
  (a) every station entrance mapped in OSM connects to the walk network;
  (b) >=90% of signalized or zebra crossings on the main desire lines are mapped;
  (c) every grade change on those routes is tagged (steps, ramp, or elevator).

Operationalization (recorded 2026-11-04, before this script's first result; see the
validation-plan change log). Ground truth does not exist, so:
  (b) a "road crossing" is any point where the shortest walk path on a desire line
      crosses a road of class tertiary or above at the same level (not a bridge/tunnel).
      It counts as mapped if the path uses a footway=crossing way there, or an OSM node
      tagged highway=crossing / highway=traffic_signals / crossing=* lies within 15 m,
      or the path passes the road on a footbridge/underpass. The path walking ALONG a
      carriageway (no separate footway) is reported as a separate gap measure.
  (c) a grade change is a transition on the path between a ground-level edge and a
      pedestrian edge (footway/steps/path/corridor/pedestrian) that is a bridge, tunnel,
      or has layer != 0. It is tagged if the transition edge or
      node is highway=steps, highway=elevator, has incline=*, or ramp=*/ramp:*=*.
This checks that the network R5 uses is plausible. It does NOT validate walking times.
Data: (c) OpenStreetMap contributors, ODbL.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import networkx as nx
import numpy as np
from shapely.geometry import LineString, Point

from osm_layers import NO_WALK, TO_UTM, TO_WGS, read_osm

RADIUS = 800
ROADS = {"trunk", "trunk_link", "primary", "primary_link", "secondary", "secondary_link", "tertiary",
         "tertiary_link", "motorway", "motorway_link"}
PED = {"footway", "pedestrian", "steps", "path", "corridor", "living_street", "elevator"}
DESIRE = {  # name regex, tag filter, fallback lon/lat
    "JB Sentral (KTM station)": (r"^Johor Bahru Sentral$", ("railway", "station"), (103.76463, 1.46297)),
    "JB Sentral Bus Terminal": (r"^JB Sentral Bus Terminal$", ("amenity", "bus_station"), (103.76483, 1.46328)),
    "Bukit Chagar bus stop (Jalan Tun Abdul Razak)": (r"^Bukit Chagar$", ("highway", "bus_stop"), (103.76075, 1.46908)),
    "City center: City Square mall (Jalan Wong Ah Fook)": (r"^(Johor Bahru )?City Square", ("shop", "mall"), (103.7637, 1.4605)),
    "Bukit Chagar ICQ building": (r"Bukit Chagar Immigration", ("building", None), (103.7615, 1.4655)),
}


def find(L, rx, tag, fb):
    import re
    r = re.compile(rx, re.I)
    fx, fy = TO_UTM.transform(*fb)
    hits = [(x, y, t, oid) for x, y, t, oid in L.points + L.named_areas
            if r.search(t.get("name", "")) and (tag[0] in t) and (tag[1] is None or t.get(tag[0]) == tag[1])]
    if hits:
        h = min(hits, key=lambda f: math.hypot(f[0] - fx, f[1] - fy))
        if math.hypot(h[0] - fx, h[1] - fy) < 1000:
            return h[0], h[1], int(h[3]), "osm"
    return fx, fy, None, "fallback_coordinate"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--osm", required=True)
    ap.add_argument("--out", default="results/stage2/v4alt_bukit_chagar.json")
    a = ap.parse_args()
    L = read_osm(a.osm)
    cx, cy, cid, how = find(L, r"^Bukit Chagar$", ("railway", "station"), (103.76219, 1.46624))
    C = Point(cx, cy)

    G = nx.Graph()
    wtags = {}
    for w in L.ways:
        t = w["tags"]
        hw = t.get("highway", "")
        walkable = (hw not in NO_WALK and t.get("foot") not in ("no", "private")
                    and t.get("access") not in ("private", "no")) or t.get("foot") in ("yes", "designated")
        wtags[w["id"]] = t
        if not walkable:
            continue
        for u, v in zip(w["nodes"][:-1], w["nodes"][1:]):
            (xa, ya), (xb, yb) = L.node_xy[u], L.node_xy[v]
            G.add_edge(u, v, length=math.hypot(xb - xa, yb - ya), way=w["id"])
    G = G.subgraph(max(nx.connected_components(G), key=len)).copy()
    node_ids = np.array(list(G.nodes))
    node_xy = np.array([L.node_xy[n] for n in node_ids])
    from scipy.spatial import cKDTree
    tree = cKDTree(node_xy)

    # inventory within 800 m (straight-line circle; this is an inventory, not a catchment)
    inv = {"footway_like_ways": 0, "footway_like_km": 0.0, "sidewalk_tagged_road_ways": 0, "steps_ways": 0,
           "escalator_ways_conveying": 0, "width_tagged_ped_ways": 0, "crossing_nodes": 0,
           "traffic_signal_nodes": 0, "elevator_nodes": 0, "footbridges_or_layered_ped_ways": 0}
    for w in L.ways:
        t = w["tags"]
        xy = [L.node_xy[n] for n in w["nodes"]]
        if min(math.hypot(x - cx, y - cy) for x, y in xy) > RADIUS:
            continue
        hw = t.get("highway", "")
        if hw in PED:
            inv["footway_like_ways"] += 1
            inv["footway_like_km"] += LineString(xy).length / 1000
            if "width" in t:
                inv["width_tagged_ped_ways"] += 1
            if t.get("bridge") not in (None, "no") or t.get("layer", "0") not in ("0",):
                inv["footbridges_or_layered_ped_ways"] += 1
        if hw == "steps":
            inv["steps_ways"] += 1
        if "conveying" in t:
            inv["escalator_ways_conveying"] += 1
        if hw in ROADS | {"residential", "unclassified", "service"} and any(k.startswith("sidewalk") for k in t):
            inv["sidewalk_tagged_road_ways"] += 1
    xing = []
    for x, y, t, oid in L.ped_nodes:
        if math.hypot(x - cx, y - cy) > RADIUS:
            continue
        if t.get("highway") == "crossing" or "crossing" in t:
            inv["crossing_nodes"] += 1
            xing.append((x, y))
        if t.get("highway") == "traffic_signals":
            inv["traffic_signal_nodes"] += 1
            xing.append((x, y))
        if t.get("highway") == "elevator" or "elevator" in t:
            inv["elevator_nodes"] += 1
    inv["footway_like_km"] = round(inv["footway_like_km"], 2)
    xtree = cKDTree(np.array(xing)) if xing else None

    # (a) entrances
    ents = []
    for x, y, t, oid in L.ped_nodes:
        if ("entrance" in t or t.get("railway") in ("subway_entrance", "train_station_entrance")) \
                and math.hypot(x - cx, y - cy) <= 250:
            ents.append({"osm_node": int(oid), "tags": {k: v for k, v in t.items() if k in ("entrance", "railway", "name", "level")},
                         "lonlat": TO_WGS.transform(x, y), "on_walk_network": int(oid) in G,
                         "dist_to_walk_network_m": round(float(tree.query([x, y])[0]), 1)})
    crit_a = {"entrances_found_within_250m": len(ents),
              "connected": sum(e["on_walk_network"] for e in ents),
              "result": ("NOT EVALUABLE (no entrance mapped)" if not ents else
                         ("PASS" if all(e["on_walk_network"] for e in ents) else "FAIL")),
              "entrances": ents}

    # desire lines
    road_lines = []
    for w in L.ways:
        t = w["tags"]
        if t.get("highway") in ROADS:
            xy = [L.node_xy[n] for n in w["nodes"]]
            ls = LineString(xy)
            if ls.distance(C) <= RADIUS + 500:
                level = t.get("bridge") not in (None, "no") or t.get("tunnel") not in (None, "no") or t.get("layer", "0") != "0"
                road_lines.append((ls, w["id"], t.get("name", t.get("highway")), level))
    _, i0 = tree.query([cx, cy])
    src = int(node_ids[i0])
    lines_out = []
    tot_x, tot_mapped, tot_gc, tot_gc_tagged = 0, 0, 0, 0
    for nm, (rx, tag, fb) in DESIRE.items():
        tx, ty, tid, thow = find(L, rx, tag, fb)
        _, j = tree.query([tx, ty])
        dst = int(node_ids[j])
        try:
            path = nx.shortest_path(G, src, dst, weight="length")
        except nx.NetworkXNoPath:
            lines_out.append({"to": nm, "error": "no path"})
            continue
        pxy = [L.node_xy[n] for n in path]
        pl = LineString(pxy) if len(pxy) > 1 else None
        plen = sum(G[u][v]["length"] for u, v in zip(path[:-1], path[1:]))
        on_ped = on_road = 0.0
        path_ways = set()
        gc, gc_tagged = 0, 0
        prev_layered = None
        for u, v in zip(path[:-1], path[1:]):
            e = G[u][v]
            t = wtags.get(e["way"], {})
            path_ways.add(e["way"])
            hw = t.get("highway", "")
            if hw in PED or (hw in ("service",) and t.get("service") == "alley"):
                on_ped += e["length"]
            elif hw in ROADS and not any(k.startswith("sidewalk") for k in t):
                on_road += e["length"]
            # only pedestrian structures (footbridges, underpasses, station decks) count as grade changes;
            # walking along a road that crosses a river on a bridge is not one
            layered = hw in PED and (t.get("bridge") not in (None, "no") or t.get("tunnel") not in (None, "no")
                                     or t.get("layer", "0") != "0")
            if prev_layered is not None and layered != prev_layered:
                gc += 1
                ramp = hw in ("steps", "elevator") or "incline" in t or any(k.startswith("ramp") for k in t)
                gc_tagged += int(ramp)
            prev_layered = layered
        # crossings
        crossings = []
        if pl is not None:
            for ls, wid, rn, level in road_lines:
                if wid in path_ways or level:
                    continue
                ip = pl.intersection(ls)
                for p in getattr(ip, "geoms", [ip]):
                    if p.is_empty or p.geom_type != "Point":
                        continue
                    mapped = bool(xtree is not None and xtree.query_ball_point([p.x, p.y], 15))
                    crossings.append({"road": rn, "lonlat": [round(c, 6) for c in TO_WGS.transform(p.x, p.y)],
                                      "mapped_crossing_within_15m": mapped})
        nx_ = len(crossings)
        nm_ = sum(c["mapped_crossing_within_15m"] for c in crossings)
        tot_x += nx_
        tot_mapped += nm_
        tot_gc += gc
        tot_gc_tagged += gc_tagged
        lines_out.append({"to": nm, "target_resolved_by": thow, "target_osm_id": tid,
                          "walk_m": round(plen), "straight_m": round(math.hypot(tx - cx, ty - cy)),
                          "detour_ratio": round(plen / max(math.hypot(tx - cx, ty - cy), 1), 2),
                          "share_on_dedicated_pedestrian_ways": round(on_ped / plen, 3) if plen else None,
                          "share_along_carriageway_without_sidewalk_tag": round(on_road / plen, 3) if plen else None,
                          "road_crossings": nx_, "mapped_crossings": nm_,
                          "grade_changes": gc, "grade_changes_tagged": gc_tagged,
                          "crossing_detail": crossings,
                          "path_lonlat": [[round(c, 6) for c in TO_WGS.transform(*xy)] for xy in pxy]})
    share = tot_mapped / tot_x if tot_x else None
    crit_b = {"road_crossings_on_desire_lines": tot_x, "mapped": tot_mapped,
              "share_mapped": None if share is None else round(share, 3), "threshold": 0.90,
              "result": "NOT EVALUABLE (no crossings found)" if share is None else ("PASS" if share >= 0.90 else "FAIL")}
    crit_c = {"grade_changes_on_desire_lines": tot_gc, "tagged": tot_gc_tagged,
              "result": "PASS (no grade change detected)" if tot_gc == 0 else ("PASS" if tot_gc_tagged == tot_gc else "FAIL")}
    overall = "PASS" if all(str(c["result"]).startswith("PASS") for c in (crit_a, crit_b, crit_c)) else \
        ("FAIL" if any(c["result"] == "FAIL" for c in (crit_a, crit_b, crit_c)) else "INCOMPLETE")
    out = {"test": "V4-alt", "center": {"name": "Bukit Chagar RTS station", "osm_id": cid, "resolved_by": how,
                                        "lonlat": TO_WGS.transform(cx, cy)},
           "radius_m": RADIUS, "inventory_800m": inv,
           "criterion_a_entrances": crit_a, "criterion_b_crossings": crit_b, "criterion_c_grade_changes": crit_c,
           "overall": overall,
           "caveat": "Checks that the OSM network R5 uses is plausible near Bukit Chagar. It does not validate walking "
                     "times and is weaker than V4 (timed walks), which is NOT RUN (no fieldwork, owner decision 6). "
                     "The RTS station is under construction; OSM reflects mapping as of the extract date.",
           "desire_lines": lines_out}
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(out, indent=1, default=float))
    print(json.dumps({k: v for k, v in out.items() if k not in ("desire_lines",)}, indent=1, default=float)[:3000])
    for d in lines_out:
        print({k: v for k, v in d.items() if k not in ("path_lonlat", "crossing_detail")})


if __name__ == "__main__":
    main()
