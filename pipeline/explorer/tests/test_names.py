import numpy as np
from shapely.geometry import LineString

from names import name_stations

line = np.array([[0, 0], [2000, 0]], float)
line_0_to_9000 = np.array([[0, 0], [9000, 0]], float)


def test_two_stations_near_one_place_get_different_names():
    st = [dict(key="T1-06", x=0, y=0), dict(key="T1-07", x=1000, y=0)]
    places = [("Kampung Stulang Baru", 500, 0), ("Taman Sri Amar", 1400, 0)]
    n = name_stations(st, [], places, [], line, {})
    assert n["T1-06"] == "Kampung Stulang Baru" and n["T1-07"] == "Taman Sri Amar"


def test_landmark_beats_place():
    n = name_stations([dict(key="k", x=0, y=0)], [("KSL City", 100, 0)], [("Taman X", 50, 0)], [], line, {})
    assert n["k"] == "KSL City"


def test_road_fallback_uses_km():
    n = name_stations([dict(key="k", x=3600, y=0)], [], [], [("Jalan Kota Tinggi", LineString([(0, 5), (9000, 5)]))], line_0_to_9000, {})
    assert n["k"] == "Jalan Kota Tinggi km 3.6"


def test_override_wins():
    n = name_stations([dict(key="k", x=0, y=0)], [("A", 0, 0)], [], [], line, {"k": "Bukit Chagar"})
    assert n["k"] == "Bukit Chagar"


def test_override_name_is_not_reused_and_rules_are_reported():
    st = [dict(key="a", x=0, y=0), dict(key="b", x=200, y=0)]
    names, rules = name_stations(st, [("Bukit Chagar", 150, 0)], [], [], line, {"a": "Bukit Chagar"}, return_rules=True)
    assert names["b"] != "Bukit Chagar" and rules == {"a": "override", "b": "road"}
