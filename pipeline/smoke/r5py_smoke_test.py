"""Stage 1 smoke test: prove that OSM + data.gov.my GTFS -> r5py works for a
small Johor Bahru test area, and check the result against pre-registered
thresholds (docs/validation-plan.md, test S1-S6).

This is a pipeline test, NOT an access result. Nothing here is a finding about
the Tebrau or Iskandar Puteri corridors.

Usage:
    python pipeline/smoke/r5py_smoke_test.py --osm data/raw/osm/jb-smoke.osm.pbf \
        --gtfs data/raw/gtfs/<date>/mybas-johor.zip --out results/stage1
"""
from __future__ import annotations

import argparse
import datetime as dt
import io
import json
import time
import zipfile
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import box

# Pre-registered thresholds (set before any run; see docs/validation-plan.md)
warnings.filterwarnings("ignore", "GeoSeries.notna", UserWarning)

THRESH = {
    "S3_min_origin_snap_share": 0.80,      # share of land grid cells r5 can route from
    "S4_detour_median_range": (1.10, 1.60),  # network walk distance / straight line, 0.5-2 km pairs
    "S5_transit_used_min_share": 0.05,     # share of pairs where transit beats walking by >=2 min
    "S5_transit_slower_max_share": 0.01,   # transit+walk must never be slower than walk-only (tolerance 1 min)
    "S6_max_runtime_minutes": 30,
}
WALK_SPEED_KMH = 3.6  # r5py default; stated so the detour test is reproducible
BBOX = (103.70, 1.44, 103.82, 1.56)  # lon/lat: JB city center, Bukit Chagar, lower Tebrau corridor
CRS_M = "EPSG:32648"  # UTM 48N


def pick_date(gtfs_paths: list[str]) -> tuple[dt.date, dict]:
    """Choose a mid-week date the feed actually covers. Flag if the feed has expired."""
    starts, ends = [], []
    for p in gtfs_paths:
        with zipfile.ZipFile(p) as z:
            if "calendar.txt" in z.namelist():
                cal = pd.read_csv(z.open("calendar.txt"), dtype=str)
                starts.append(cal["start_date"].min())
                ends.append(cal["end_date"].max())
    today = dt.date.today()
    info = {"today": today.isoformat()}
    if not starts:
        info["note"] = "no calendar.txt; using today"
        return today, info
    s = dt.datetime.strptime(min(starts), "%Y%m%d").date()
    e = dt.datetime.strptime(min(ends), "%Y%m%d").date()  # conservative: feed with earliest end
    info.update(service_start=s.isoformat(), service_end=e.isoformat())
    cand = today if s <= today <= e else e - dt.timedelta(days=7)
    while cand.weekday() != 2:  # Wednesday
        cand -= dt.timedelta(days=1)
    if cand < s:
        cand = s
    info["feed_expired"] = today > e
    info["analysis_date"] = cand.isoformat()
    return cand, info


def grid(cell_m: int = 500) -> gpd.GeoDataFrame:
    g = gpd.GeoSeries([box(*BBOX)], crs="EPSG:4326").to_crs(CRS_M)
    minx, miny, maxx, maxy = g.total_bounds
    xs = np.arange(minx + cell_m / 2, maxx, cell_m)
    ys = np.arange(miny + cell_m / 2, maxy, cell_m)
    pts = gpd.GeoDataFrame(
        geometry=gpd.points_from_xy(*[a.ravel() for a in np.meshgrid(xs, ys)]), crs=CRS_M
    )
    pts["id"] = range(len(pts))
    return pts.to_crs("EPSG:4326")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--osm", required=True)
    ap.add_argument("--gtfs", nargs="+", required=True)
    ap.add_argument("--out", default="results/stage1")
    ap.add_argument("--cell", type=int, default=500)
    args = ap.parse_args()
    t0 = time.time()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    report: dict = {"thresholds": {k: list(v) if isinstance(v, tuple) else v for k, v in THRESH.items()},
                    "bbox_lonlat": BBOX, "cell_m": args.cell, "tests": {}}

    import r5py  # imported late so the date logic can be tested without Java

    report["r5py_version"] = r5py.__version__
    date, dinfo = pick_date(args.gtfs)
    report["calendar"] = dinfo
    departure = dt.datetime.combine(date, dt.time(7, 30))

    # S1: transport network builds from OSM + GTFS
    try:
        tn = r5py.TransportNetwork(args.osm, args.gtfs)
        report["tests"]["S1_network_builds"] = {"pass": True}
    except Exception as e:
        report["tests"]["S1_network_builds"] = {"pass": False, "error": repr(e)[:500]}
        (out / "smoke_report.json").write_text(json.dumps(report, indent=2))
        raise

    pts = grid(args.cell)
    # Keep cells r5 can snap to the street network (drops sea and large voids)
    snapped = tn.snap_to_network(pts.geometry, radius=250)
    pts["snapped"] = (~snapped.is_empty & snapped.notna()).values
    land = pts[pts["snapped"]].copy()
    land["geometry"] = snapped[pts["snapped"]].values
    share = len(land) / len(pts)
    # Note: the bbox includes the Johor Strait, so S3 is judged on the share of
    # cells r5 could snap among cells that are not open water (approximated as
    # cells snapped within 250 m vs. a 1 km radius).
    snapped_wide = tn.snap_to_network(pts.geometry, radius=1000)
    near_land = (~snapped_wide.is_empty & snapped_wide.notna()).sum()
    s3 = len(land) / max(near_land, 1)
    report["tests"]["S3_origin_snapping"] = {
        "cells_total": len(pts), "cells_near_network_1km": int(near_land),
        "cells_snapped_250m": len(land), "share_raw": round(share, 3),
        "share_of_near_network": round(s3, 3), "pass": bool(s3 >= THRESH["S3_min_origin_snap_share"])}

    common = dict(origins=land, destinations=land, departure=departure,
                  departure_time_window=dt.timedelta(minutes=60), max_time=dt.timedelta(minutes=60))
    walk = r5py.TravelTimeMatrix(tn, transport_modes=[r5py.TransportMode.WALK], **common)
    pt = r5py.TravelTimeMatrix(tn, transport_modes=[r5py.TransportMode.TRANSIT, r5py.TransportMode.WALK], **common)

    m = walk.merge(pt, on=["from_id", "to_id"], suffixes=("_walk", "_pt"))
    xy = land.to_crs(CRS_M).set_index("id").geometry
    fx, tx = xy.loc[m["from_id"]].values, xy.loc[m["to_id"]].values
    m["euclid_m"] = [a.distance(b) for a, b in zip(fx, tx)]
    m = m[m["from_id"] != m["to_id"]]
    m.to_parquet(out / "smoke_ttm.parquet", index=False)

    # S2: matrix computed with non-trivial coverage
    report["tests"]["S2_matrix_computed"] = {
        "pairs": len(m), "walk_non_null": int(m["travel_time_walk"].notna().sum()),
        "pt_non_null": int(m["travel_time_pt"].notna().sum()),
        "pass": bool(m["travel_time_pt"].notna().sum() > 0)}

    # S4: walking detour ratio on the street network (not radius circles)
    band = m[(m["euclid_m"].between(500, 2000)) & m["travel_time_walk"].notna()]
    detour = (band["travel_time_walk"] / 60 * WALK_SPEED_KMH * 1000) / band["euclid_m"]
    lo, hi = THRESH["S4_detour_median_range"]
    med = float(detour.median()) if len(detour) else float("nan")
    report["tests"]["S4_walk_detour"] = {"pairs": len(band), "median": round(med, 3),
                                         "p10": round(float(detour.quantile(.1)), 3) if len(detour) else None,
                                         "p90": round(float(detour.quantile(.9)), 3) if len(detour) else None,
                                         "pass": bool(lo <= med <= hi),
                                         "note": "includes snapping access legs; r5 rounds to whole minutes"}

    # S5: transit is used and never makes trips slower
    both = m.dropna(subset=["travel_time_walk", "travel_time_pt"])
    faster = (both["travel_time_pt"] <= both["travel_time_walk"] - 2).mean() if len(both) else 0
    slower = (both["travel_time_pt"] > both["travel_time_walk"] + 1).mean() if len(both) else 1
    only_pt = int((m["travel_time_walk"].isna() & m["travel_time_pt"].notna()).sum())
    report["tests"]["S5_transit_logic"] = {
        "pairs_both": len(both), "share_transit_faster_2min": round(float(faster), 4),
        "share_transit_slower_1min": round(float(slower), 4),
        "pairs_reachable_only_with_transit_60min": only_pt,
        "pass": bool(faster >= THRESH["S5_transit_used_min_share"] and slower <= THRESH["S5_transit_slower_max_share"])}

    runtime = (time.time() - t0) / 60
    report["tests"]["S6_runtime"] = {"minutes": round(runtime, 2), "pass": bool(runtime <= THRESH["S6_max_runtime_minutes"])}
    report["all_pass"] = bool(all(t["pass"] for t in report["tests"].values()))
    report["finished_utc"] = dt.datetime.now(dt.timezone.utc).isoformat()
    (out / "smoke_report.json").write_text(json.dumps(report, indent=2, default=str))
    print(json.dumps(report, indent=2, default=str))


if __name__ == "__main__":
    main()
