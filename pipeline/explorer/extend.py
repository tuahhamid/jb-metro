"""Route edits for explorer lines: extend along roads, cut detours, place new stations.

Ported from the spike `extend_t1.py`. Coordinates are metres (EPSG:32648, as in Stage 2 `Layers`).
"""
from __future__ import annotations

import networkx as nx
import numpy as np
from shapely.geometry import LineString, Point

# Cost per metre = length x class weight. Trunk and primary roads are preferred (the
# extension follows Federal Route 3); motorways and ramps are discouraged.
EXT_WEIGHTS = {"trunk": 0.4, "primary": 0.5, "secondary": 1.0, "tertiary": 1.3,
               "motorway": 3.0, "trunk_link": 2.0, "primary_link": 2.0}


def route_on_roads(L, start_xy: tuple, end_xy: tuple, weights: dict = EXT_WEIGHTS) -> np.ndarray:
    """Weighted shortest path on the road graph between the nodes nearest to the two points."""
    G = nx.Graph()
    for w in L.ways:
        f = weights.get(w["tags"].get("highway"))
        if f is None:
            continue
        nodes = [n for n in w["nodes"] if n in L.node_xy]
        for a, b in zip(nodes, nodes[1:]):
            pa, pb = np.asarray(L.node_xy[a], float), np.asarray(L.node_xy[b], float)
            cost = float(np.hypot(*(pb - pa))) * f
            if not G.has_edge(a, b) or G[a][b]["w"] > cost:
                G.add_edge(a, b, w=cost)
    ids = list(G.nodes)
    arr = np.array([L.node_xy[i] for i in ids], float)

    def nearest(p):
        return ids[int(np.argmin(np.hypot(*(arr - np.asarray(p, float)).T)))]

    path = nx.shortest_path(G, nearest(start_xy), nearest(end_xy), weight="w")
    return np.array([L.node_xy[i] for i in path], float)


def _head(ln: LineString, d: float) -> list:
    """Vertices of `ln` before distance `d`, then the point at `d`."""
    out, run = [ln.coords[0]], 0.0
    for a, b in zip(ln.coords, ln.coords[1:]):
        run += Point(a).distance(Point(b))
        if run >= d:
            break
        out.append(b)
    out.append(ln.interpolate(d).coords[0])
    return out


def _tail(ln: LineString, d: float) -> list:
    rev = LineString(ln.coords[::-1])
    return _head(rev, ln.length - d)[::-1]


def splice(road_xy: np.ndarray, cut_xy: tuple, extension_xy: np.ndarray) -> np.ndarray:
    ln = LineString(np.asarray(road_xy, float))
    head = _head(ln, ln.project(Point(cut_xy)))
    ext = [tuple(p) for p in np.asarray(extension_xy, float)]
    if ext and Point(ext[0]).distance(Point(head[-1])) < 1e-6:
        ext = ext[1:]
    return _dedupe(np.array(head + ext, float))


def bypass(road_xy: np.ndarray, from_xy: tuple, to_xy: tuple) -> np.ndarray:
    ln = LineString(np.asarray(road_xy, float))
    d0, d1 = ln.project(Point(from_xy)), ln.project(Point(to_xy))
    if d1 < d0:
        d0, d1 = d1, d0
    return _dedupe(np.array(_head(ln, d0) + _tail(ln, d1), float))


def even_stations(line_xy: np.ndarray, from_xy: tuple, to_xy: tuple,
                  target_m: float = 1200, band: tuple = (1000, 1500)) -> list[tuple]:
    ln = LineString(np.asarray(line_xy, float))
    d0, d1 = ln.project(Point(from_xy)), ln.project(Point(to_xy))
    length = d1 - d0
    n = max(1, round(length / target_m))
    while n > 1 and length / n < band[0]:
        n -= 1
    while length / n > band[1]:
        n += 1
    pts = [tuple(float(v) for v in ln.interpolate(d0 + k * length / n).coords[0]) for k in range(1, n)]
    return pts + [(float(to_xy[0]), float(to_xy[1]))]


def _dedupe(xy: np.ndarray) -> np.ndarray:
    keep = np.r_[True, np.hypot(*np.diff(xy, axis=0).T) > 1e-6]
    return xy[keep]
