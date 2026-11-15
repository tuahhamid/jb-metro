import numpy as np
from shapely.geometry import box

from conftest import dist_to_line, min_radius, path_length, straightness_dev
from track import StationIn, build_track, remove_loops, resample, track_report


def test_straight_road_gives_no_curves():
    road = np.array([[0, 0], [5000, 0]], float)
    r = build_track(road, [StationIn("a", 0, 0), StationIn("b", 2500, 0), StationIn("c", 5000, 0)])
    assert r.radii == [] and r.flags == []


def test_right_angle_becomes_one_r150_arc():
    road = np.array([[0, 0], [2000, 0], [2000, 2000]], float)
    r = build_track(road, [StationIn("a", 0, 0), StationIn("b", 2000, 2000)])
    assert r.radii == [150.0]
    assert min_radius(r.xy, chord=30) >= 149.0


def test_station_has_80m_clear_straight_each_side():
    road = np.array([[0, 0], [1500, 0], [1500, 1500], [3000, 1500]], float)
    st = [StationIn("a", 0, 0), StationIn("m", 1500, 750), StationIn("z", 3000, 1500)]
    r = build_track(road, st)
    assert straightness_dev(r.xy, (1500, 750), half=80) < 0.5
    assert dist_to_line(r.xy, (1500, 750)) < 0.5


def test_cloverleaf_loop_is_removed():
    t = np.linspace(0, 2 * np.pi, 60)
    loop = np.c_[1000 + 60 * np.sin(t), 60 - 60 * np.cos(t)]
    road = np.vstack([[[0, 0]], loop, [[2000, 0]]])
    out = remove_loops(resample(road, 10), 800, 1.6, 60)
    assert path_length(out) < 2050


def test_close_stations_on_reversal_rotate_and_do_not_hang():
    road = np.array([[0, 0], [-150, 180], [-130, 310], [25, 507], [76, 763], [-1185, 415]], float)
    r = build_track(road, [StationIn("s1", 0, 0), StationIn("s4", -1185, 415)])
    assert all(rad >= 100.0 for rad in r.radii)


def test_report_counts_buildings_crossed():
    road = np.array([[0, 0], [1000, 0]], float)
    r = build_track(road, [StationIn("a", 0, 0), StationIn("b", 1000, 0)])
    rep = track_report(r, road, [(box(400, -5, 420, 5), None, 77), (box(400, 50, 420, 60), None, 78)])
    assert rep["buildings_crossed"] == [77] and rep["curves_below_r100"] == 0
