"""Fetch one GTFS-Realtime vehicle-position snapshot from data.gov.my.

Stage 1 only proves access and decoding. Stage 5 needs a multi-week
collection (see docs/validation-plan.md, V3).

Usage:
    python pipeline/fetch/fetch_vehicle_positions.py --out results/stage1/vehicle_positions_snapshot.csv
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path

import pandas as pd
import requests
from google.transit import gtfs_realtime_pb2

URL = "https://api.data.gov.my/gtfs-realtime/vehicle-position/mybas-johor"
UA = {"User-Agent": "jb-metro-research/0.1 (transport planning prototype; GitHub Actions)"}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="results/stage1/vehicle_positions_snapshot.csv")
    ap.add_argument("--summary", default="results/stage1/vehicle_positions_summary.json")
    args = ap.parse_args()
    fetched = dt.datetime.now(dt.timezone.utc)
    summary: dict = {"url": URL, "fetched_utc": fetched.isoformat()}
    rows = []
    try:
        r = requests.get(URL, headers=UA, timeout=60)
        summary["http_status"] = r.status_code
        summary["bytes"] = len(r.content)
        feed = gtfs_realtime_pb2.FeedMessage()
        feed.ParseFromString(r.content)
        summary["header_timestamp"] = feed.header.timestamp
        for ent in feed.entity:
            if not ent.HasField("vehicle"):
                continue
            v = ent.vehicle
            rows.append(
                {
                    "entity_id": ent.id,
                    "trip_id": v.trip.trip_id,
                    "route_id": v.trip.route_id,
                    "vehicle_id": v.vehicle.id,
                    "lat": v.position.latitude,
                    "lon": v.position.longitude,
                    "speed_mps": v.position.speed if v.position.HasField("speed") else None,
                    "timestamp": v.timestamp,
                }
            )
    except Exception as e:
        summary["error"] = repr(e)
    df = pd.DataFrame(rows)
    summary["vehicles"] = len(df)
    if len(df):
        newest = int(df["timestamp"].max())
        summary["newest_vehicle_ts_utc"] = dt.datetime.fromtimestamp(newest, dt.timezone.utc).isoformat()
        summary["newest_age_seconds"] = int(fetched.timestamp() - newest)
        summary["routes_seen"] = int(df["route_id"].nunique())
        summary["with_trip_id_share"] = float((df["trip_id"] != "").mean())
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    # Positions of in-service buses only (no personal data); kept for audit.
    df.to_csv(args.out, index=False)
    Path(args.summary).write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
