"""Collect BAS.MY Johor Bahru vehicle positions for a fixed window.

Polls the public data.gov.my GTFS-Realtime feed every --interval seconds for
--minutes minutes, de-duplicates by (vehicle_id, timestamp), and writes one
Parquet file plus a JSON summary. Used by .github/workflows/vp-collector.yml;
the data feeds validation test V3a (docs/validation-plan.md).

Data note: vehicle_id in this feed is the bus registration shown on the public
bus. No passenger or driver data is present in the feed.

Usage:
    python pipeline/fetch/collect_vehicle_positions.py --minutes 60 --interval 30 --out vp.parquet
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import time
from pathlib import Path

import pandas as pd
import requests
from google.transit import gtfs_realtime_pb2

URL = "https://api.data.gov.my/gtfs-realtime/vehicle-position/mybas-johor"
UA = {"User-Agent": "jb-metro-research/0.1 (transport planning prototype; GitHub Actions)"}


def snapshot(fetched: float) -> list[dict]:
    r = requests.get(URL, headers=UA, timeout=30)
    r.raise_for_status()
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.ParseFromString(r.content)
    rows = []
    for ent in feed.entity:
        if not ent.HasField("vehicle"):
            continue
        v = ent.vehicle
        rows.append({
            "trip_id": v.trip.trip_id, "route_id": v.trip.route_id,
            "vehicle_id": v.vehicle.id, "lat": v.position.latitude, "lon": v.position.longitude,
            "bearing": v.position.bearing if v.position.HasField("bearing") else None,
            "speed_mps": v.position.speed if v.position.HasField("speed") else None,
            "timestamp": int(v.timestamp), "fetched_utc_s": int(fetched),
            "feed_header_ts": int(feed.header.timestamp),
        })
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--minutes", type=float, default=60)
    ap.add_argument("--interval", type=float, default=30)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    start = time.time()
    end = start + args.minutes * 60
    rows, polls, errors = [], 0, []
    while True:
        t = time.time()
        polls += 1
        try:
            rows += snapshot(t)
        except Exception as e:  # keep collecting; record every failure
            errors.append({"at_utc_s": int(t), "error": repr(e)[:200]})
        if time.time() + args.interval > end:
            break
        time.sleep(max(0, args.interval - (time.time() - t)))
    df = pd.DataFrame(rows)
    if len(df):
        df = df.drop_duplicates(subset=["vehicle_id", "timestamp"]).sort_values(["vehicle_id", "timestamp"])
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(args.out, index=False)
    summary = {
        "url": URL,
        "window_start_utc": dt.datetime.fromtimestamp(start, dt.timezone.utc).isoformat(timespec="seconds"),
        "window_end_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "polls": polls, "poll_errors": len(errors), "errors": errors[:20],
        "unique_positions": int(len(df)),
        "vehicles": int(df["vehicle_id"].nunique()) if len(df) else 0,
        "trips": int(df["trip_id"].nunique()) if len(df) else 0,
        "routes": int(df["route_id"].nunique()) if len(df) else 0,
    }
    Path(args.out).with_suffix(".json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
    if polls and len(errors) == polls:
        raise SystemExit("every poll failed")


if __name__ == "__main__":
    main()
