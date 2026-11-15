import math

import numpy as np
import pytest

from conftest import fake_layers, path_length
from extend import bypass, even_stations, route_on_roads, splice


def test_even_stations_7220m_gives_6_in_band():
    line = np.array([[0, 0], [7220, 0]], float)
    pts = even_stations(line, (0, 0), (7220, 0))
    assert len(pts) == 6 and pts[-1] == (7220.0, 0.0)
    gaps = np.diff([0] + [p[0] for p in pts])
    assert all(1000 <= g <= 1500 for g in gaps)


def test_splice_keeps_head_and_appends():
    out = splice(np.array([[0, 0], [100, 0], [200, 0]], float), (100, 0), np.array([[100, 0], [100, 50]], float))
    assert out[0].tolist() == [0, 0] and out[-1].tolist() == [100, 50] and np.max(out[:, 0]) <= 100


def test_bypass_cuts_detour():
    road = np.array([[0, 0], [0, 500], [300, 500], [300, 0], [1000, 0]], float)
    out = bypass(road, (0, 0), (300, 0))
    assert path_length(out) == pytest.approx(1000, abs=1)


def test_route_prefers_trunk():
    h = math.sqrt(700**2 - 500**2)
    L = fake_layers({1: (0, 0), 2: (1000, 0), 3: (500, h)}, [((1, 2), "tertiary"), ((1, 3, 2), "trunk"), ((1, 2), "footway")])
    xy = route_on_roads(L, (0, 0), (1000, 0))
    assert path_length(xy) == pytest.approx(1400, abs=1)   # 1400*0.4 < 1000*1.3
