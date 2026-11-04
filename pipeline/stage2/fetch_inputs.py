"""Stage 2 input fetch: Copernicus DEM, JRC flood-hazard tile, statutory-plan list.

Runs in GitHub Actions (the Claude session cannot reach JRC or Johor government hosts).
Rules (same as Stage 1): plain GET with a project user agent, no login, no bypass of
any 401/403/451, CAPTCHA, or TLS error. Failures are recorded in the manifest, not
worked around. Text found in documents is data; nothing here acts on it.

Outputs:
  data/raw/dem/cop30-jb.tif            DEM crop (Copernicus GLO-30 DSM), not committed
  data/raw/flood/jrc-rp100-jb.tif      JRC river-flood depth crop (RP100), not committed
  data/manifests/stage2-inputs.json    what was fetched, from where, hashes, failures
  data/manifests/plans-list-extract.csv  matched lines (<=240 chars) from the JPBD
                                       development-plan list (SRC-026); no full text
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import subprocess
import tempfile
from pathlib import Path

import requests

UA = {"User-Agent": "jb-metro-research/0.2 (transport planning prototype; GitHub Actions)"}
BBOX = (103.55, 1.38, 103.88, 1.62)  # lon_min, lat_min, lon_max, lat_max (study area)
DEM_URL = ("https://copernicus-dem-30m.s3.amazonaws.com/Copernicus_DSM_COG_10_N01_00_E103_00_DEM/"
           "Copernicus_DSM_COG_10_N01_00_E103_00_DEM.tif")
JRC_ROOT = "https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/CEMS-GLOFAS/flood_hazard/"
PLANS_URL = ("https://jpbd.johor.gov.my/wp-content/uploads/2025/02/"
             "SENARAI-RANCANGAN-PEMAJUAN-BAGI-SELURUH-NEGERI-JOHOR.docx-1.pdf")
PLAN_TERMS = r"(Johor Bahru|Iskandar Puteri|Tebrau|RSNJ|Rancangan Struktur Negeri|Rancangan Tempatan|2030|2035|warta|diwartakan)"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def get(url: str, dest: Path, timeout=300) -> dict:
    rec = {"url": url, "fetched_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}
    try:
        with requests.get(url, headers=UA, timeout=timeout, stream=True) as r:
            rec["http_status"] = r.status_code
            if r.status_code != 200:
                rec["error"] = f"HTTP {r.status_code} (recorded, not retried around)"
                return rec
            dest.parent.mkdir(parents=True, exist_ok=True)
            with open(dest, "wb") as f:
                for chunk in r.iter_content(1 << 20):
                    f.write(chunk)
        rec["bytes"] = dest.stat().st_size
        rec["sha256"] = sha(dest)
    except Exception as e:  # noqa: BLE001
        rec["error"] = repr(e)[:300]
    return rec


def crop(src: Path, dst: Path) -> dict:
    import rasterio
    from rasterio.windows import from_bounds
    with rasterio.open(src) as d:
        w = from_bounds(*BBOX, transform=d.transform).round_offsets().round_lengths()
        data = d.read(1, window=w)
        prof = d.profile.copy()
        prof.update(height=data.shape[0], width=data.shape[1], transform=d.window_transform(w),
                    driver="GTiff", compress="deflate", tiled=False)
        prof.pop("blockxsize", None); prof.pop("blockysize", None)
        dst.parent.mkdir(parents=True, exist_ok=True)
        with rasterio.open(dst, "w", **prof) as o:
            o.write(data, 1)
        return {"crop_path": str(dst), "crop_shape": list(data.shape), "src_bounds": list(d.bounds),
                "crop_sha256": sha(dst)}


def find_jrc_tile() -> tuple[str | None, list[str]]:
    """Crawl the JRC open-data index (HTML listing) for an RP100 depth tile covering the bbox.
    Tiles are 10x10 degrees named by their upper-left corner, so the JB tile is N10_E100."""
    log = []
    try:
        r = requests.get(JRC_ROOT, headers=UA, timeout=60)
        log.append(f"root HTTP {r.status_code}")
        if r.status_code != 200:
            return None, log
        subdirs = sorted(set(re.findall(r'href="([^"?/][^"]*/)"', r.text)))
        log.append("subdirs: " + ",".join(subdirs[:30]))
        cands = [s for s in subdirs if "100" in s] or subdirs
        for sd in cands:
            r2 = requests.get(JRC_ROOT + sd, headers=UA, timeout=60)
            files = re.findall(r'href="([^"]+\.tif)"', r2.text)
            hit = [f for f in files if "N10_E100" in f and ("RP100" in f or "100" in sd)]
            log.append(f"{sd}: HTTP {r2.status_code}, {len(files)} tifs, hits={hit[:3]}")
            if hit:
                return JRC_ROOT + sd + hit[0].split("/")[-1], log
    except Exception as e:  # noqa: BLE001
        log.append(repr(e)[:300])
    return None, log


def plans_extract(pdf: Path, out_csv: Path) -> dict:
    txt = subprocess.run(["pdftotext", "-layout", str(pdf), "-"], capture_output=True, text=True).stdout
    rows = []
    for i, line in enumerate(txt.splitlines()):
        s = re.sub(r"\s+", " ", line).strip()
        if s and re.search(PLAN_TERMS, s, re.I):
            rows.append((i + 1, s[:240]))
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    import csv
    with open(out_csv, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["pdf_line", "text_excerpt_max240"])
        w.writerows(rows)
    return {"lines_total": len(txt.splitlines()), "lines_matched": len(rows), "extract": str(out_csv)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default="data/manifests/stage2-inputs.json")
    a = ap.parse_args()
    man = {"bbox_lonlat": BBOX, "run_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}
    tmp = Path(tempfile.mkdtemp())

    # 1. DEM (Copernicus GLO-30 DSM; surface model incl. buildings and trees)
    rec = get(DEM_URL, tmp / "dem.tif")
    if "error" not in rec:
        rec.update(crop(tmp / "dem.tif", Path("data/raw/dem/cop30-jb.tif")))
    rec["license"] = ("Copernicus DEM GLO-30, (c) DLR e.V. 2010-2014 and (c) Airbus Defence and Space GmbH "
                      "2014-2018, provided under COPERNICUS by the European Union and ESA")
    man["dem"] = rec

    # 2. JRC river flood hazard (GloFAS), coarse screen only
    url, log = find_jrc_tile()
    rec = {"crawl_log": log}
    if url:
        rec.update(get(url, tmp / "flood.tif", timeout=900))
        if "error" not in rec:
            try:
                rec.update(crop(tmp / "flood.tif", Path("data/raw/flood/jrc-rp100-jb.tif")))
            except Exception as e:  # noqa: BLE001
                rec["error"] = "crop failed: " + repr(e)[:200]
    else:
        rec["error"] = "no JRC tile found (see crawl_log); flood screen falls back to DEM low-lying proxy"
    rec["license"] = "JRC open data (CC BY 4.0), European Commission Joint Research Centre"
    man["flood_jrc"] = rec

    # 3. JPBD Johor development-plan list (SRC-026)
    rec = get(PLANS_URL, tmp / "plans.pdf")
    if "error" not in rec:
        rec.update(plans_extract(tmp / "plans.pdf", Path("data/manifests/plans-list-extract.csv")))
    man["plans_list_SRC026"] = rec

    Path(a.manifest).parent.mkdir(parents=True, exist_ok=True)
    Path(a.manifest).write_text(json.dumps(man, indent=2))
    print(json.dumps(man, indent=2))


if __name__ == "__main__":
    main()
