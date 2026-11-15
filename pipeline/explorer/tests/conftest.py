"""Shared test helpers for the explorer pipeline. Tests import them with `from conftest import ...`."""
import sys
from pathlib import Path

import numpy as np
from shapely.geometry import LineString, Point

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parent), str(HERE.parent.parent / "stage2")]


def path_length(xy) -> float:
    xy = np.asarray(xy, float)
    return float(np.hypot(*np.diff(xy, axis=0).T).sum())


def _resample(xy, step):
    ln = LineString(xy)
    n = max(int(ln.length // step), 2)
    return np.array([ln.interpolate(i * ln.length / n).coords[0] for i in range(n + 1)])


def min_radius(xy, chord=30.0) -> float:
    """Smallest 3-point circle radius along the line, sampled at `chord` spacing."""
    P = _resample(xy, chord)
    best = float("inf")
    for a, b, c in zip(P[:-2], P[1:-1], P[2:]):
        ab, bc, ca = np.hypot(*(b - a)), np.hypot(*(c - b)), np.hypot(*(a - c))
        area2 = abs((b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]))
        if area2 < 1e-6:
            continue
        best = min(best, ab * bc * ca / (2 * area2))
    return best


def dist_to_line(xy, pt) -> float:
    return float(LineString(xy).distance(Point(pt)))


def straightness_dev(xy, center, half=80.0) -> float:
    """Max distance of the track within +-half of `center` from the chord between its ends."""
    ln = LineString(xy)
    d = ln.project(Point(center))
    lo, hi = max(d - half, 0.0), min(d + half, ln.length)
    chord = LineString([ln.interpolate(lo), ln.interpolate(hi)])
    return max(chord.distance(ln.interpolate(x)) for x in np.linspace(lo, hi, 33))


class _Layers:
    def __init__(self, node_xy, ways):
        self.node_xy, self.ways = node_xy, ways


def fake_layers(node_xy: dict, ways: list):
    """Stage 2 `Layers` stand-in. ways: list of (node ids, highway class)."""
    return _Layers(node_xy, [{"id": i, "nodes": list(n), "tags": {"highway": h}} for i, (n, h) in enumerate(ways)])
