"""Integration test: builds the JB explorer data from the committed OSM study clip (about 1-3 minutes)."""
import json
import subprocess
import sys

from conftest import HERE

REPO = HERE.parents[2]


def run_cli(args):
    subprocess.run([sys.executable, str(REPO / "pipeline/explorer/build_line.py"), *map(str, args)], cwd=REPO, check=True)


def test_jb_build(tmp_path):
    run_cli(["--config", "pipeline/explorer/jb.json", "--out", tmp_path / "site", "--report", tmp_path / "rep"])
    rep = json.loads((tmp_path / "rep/jb_track_report.json").read_text(encoding="utf-8"))
    for lid in ("T1", "IP2"):
        assert rep[lid]["curves_below_r100"] == 0
        assert rep[lid]["max_station_error_m"] < 1.0
    net = json.loads((tmp_path / "site/network.geojson").read_text(encoding="utf-8"))
    st = lambda lid: [f["properties"] for f in net["features"] if f["properties"]["kind"] == "station" and f["properties"]["line_id"] == lid]
    assert len(st("T1")) == 19 and len(st("IP2")) == 15
    assert max(st("T1"), key=lambda p: p["seq"])["name"] == "Ulu Tiram"
    for lid in ("T1", "IP2"):
        names = [p["name"] for p in st(lid)]
        assert len(names) == len(set(names)) and all(names)
    assert {f["properties"]["status"] for f in net["features"] if f["properties"]["kind"] in ("line", "station") and f["properties"]["line_id"] in ("T1", "IP2")} == {"concept"}
    assert not any(f["properties"]["kind"] in ("road_route", "crossing") for f in net["features"])
    # every landmark photo key must exist in the Commons title list (Task 6)
    titles = json.loads((REPO / "pipeline/explorer/jb_photos.json").read_text(encoding="utf-8")) if (REPO / "pipeline/explorer/jb_photos.json").exists() else None
    lms = [f["properties"] for f in net["features"] if f["properties"]["kind"] == "landmark"]
    assert len(lms) == 21
    if titles is not None:
        assert all(p["photo"] in titles for p in lms if p["photo"])
