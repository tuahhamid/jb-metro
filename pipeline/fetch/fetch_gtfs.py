"""Fetch GTFS static feeds from the data.gov.my API and record a manifest.

Runs in GitHub Actions (the Claude session's network policy blocks data.gov.my).
Plain HTTP GET with a project user agent; no authentication, no circumvention.

Usage:
    python pipeline/fetch/fetch_gtfs.py --out data/raw/gtfs --manifest data/manifests/gtfs.json
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import io
import json
import zipfile
from pathlib import Path

import pandas as pd
import requests

FEEDS = {
    # Official endpoints listed at https://developer.data.gov.my/realtime-api/gtfs-static
    "mybas-johor": "https://api.data.gov.my/gtfs-static/mybas-johor",
    "ktmb": "https://api.data.gov.my/gtfs-static/ktmb",
}
UA = {"User-Agent": "jb-metro-research/0.1 (transport planning prototype; GitHub Actions)"}


def service_range(zbytes: bytes) -> dict:
    """Return min/max service dates and basic counts from a GTFS zip."""
    out: dict = {}
    with zipfile.ZipFile(io.BytesIO(zbytes)) as z:
        names = set(z.namelist())
        out["files"] = sorted(names)
        dates = []
        if "calendar.txt" in names:
            cal = pd.read_csv(z.open("calendar.txt"), dtype=str)
            if len(cal):
                dates += [cal["start_date"].min(), cal["end_date"].max()]
        if "calendar_dates.txt" in names:
            cd = pd.read_csv(z.open("calendar_dates.txt"), dtype=str)
            if len(cd):
                added = cd[cd["exception_type"].astype(str) == "1"]["date"]
                if len(added):
                    dates += [added.min(), added.max()]
        out["service_start"] = min(dates) if dates else None
        out["service_end"] = max(dates) if dates else None
        for f in ("agency.txt", "routes.txt", "stops.txt", "trips.txt"):
            if f in names:
                df = pd.read_csv(z.open(f), dtype=str)
                out[f.replace(".txt", "_count")] = len(df)
                if f == "agency.txt":
                    out["agencies"] = df.get("agency_name", pd.Series(dtype=str)).tolist()
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/raw/gtfs")
    ap.add_argument("--manifest", default="data/manifests/gtfs.json")
    args = ap.parse_args()
    today = dt.date.today().isoformat()
    outdir = Path(args.out) / today
    outdir.mkdir(parents=True, exist_ok=True)
    manifest = {"fetched_utc": dt.datetime.now(dt.timezone.utc).isoformat(), "feeds": {}}
    for name, url in FEEDS.items():
        rec: dict = {"url": url}
        try:
            r = requests.get(url, headers=UA, timeout=120)
            rec["http_status"] = r.status_code
            rec["content_type"] = r.headers.get("content-type")
            if r.ok and r.content[:2] == b"PK":
                path = outdir / f"{name}.zip"
                path.write_bytes(r.content)
                rec["path"] = str(path)
                rec["bytes"] = len(r.content)
                rec["sha256"] = hashlib.sha256(r.content).hexdigest()
                rec.update(service_range(r.content))
                end = rec.get("service_end")
                rec["expired_on_fetch_date"] = bool(end and end < today.replace("-", ""))
            else:
                rec["error"] = "non-zip or non-200 response"
        except Exception as e:  # record, never hide
            rec["error"] = repr(e)
        manifest["feeds"][name] = rec
        print(name, json.dumps({k: v for k, v in rec.items() if k != "files"}))
    Path(args.manifest).parent.mkdir(parents=True, exist_ok=True)
    Path(args.manifest).write_text(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
