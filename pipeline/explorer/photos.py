"""Download credited, freely licensed Wikimedia Commons photos for explorer landmarks.

    python pipeline/explorer/photos.py --titles pipeline/explorer/jb_photos.json --out site/photos/jb --json site/data/jb/photos.json

Every title was looked at by a person before it went into the titles file (spec section 5.6).
A file whose license is not CC0, CC BY, CC BY-SA or public domain stops the run.
"""
from __future__ import annotations

import argparse
import html
import io
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from PIL import Image

API = "https://commons.wikimedia.org/w/api.php?"
UA = {"User-Agent": "jb-metro-explorer/1.0 (open-source research prototype)"}
FREE = re.compile(r"^(CC0|CC BY( |-SA )[0-9.]+|Public domain)$", re.I)
MIN_SOURCE_WIDTH = 800
MAX_BYTES = 250_000


def is_free_license(short_name: str) -> bool:
    return bool(FREE.match((short_name or "").strip()))


def _strip(s: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", s or "")).strip()


def credit_line(meta: dict) -> str:
    author = _strip(meta.get("author", ""))[:80] or "unknown"
    return f"Photo: {author} · {meta['license']} · Wikimedia Commons"


def shrink_jpeg(data: bytes, max_bytes: int = MAX_BYTES, max_width: int = 960) -> bytes:
    """Re-encode as JPEG no wider than max_width, lowering quality until it fits max_bytes."""
    img = Image.open(io.BytesIO(data)).convert("RGB")
    if img.width > max_width:
        img = img.resize((max_width, round(img.height * max_width / img.width)), Image.LANCZOS)
    for q in (85, 80, 75, 70, 65, 60, 55, 50):
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=q, optimize=True, progressive=True)
        if buf.tell() <= max_bytes:
            return buf.getvalue()
    raise RuntimeError("cannot fit JPEG under the size limit")


def _get(url: str, sleep: float = 3.0) -> bytes:
    for attempt in range(1, 7):
        time.sleep(sleep)
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code != 429:
                raise
            time.sleep(20 * attempt)
    raise RuntimeError(f"rate limited: {url}")


def _info(title: str, width: int) -> dict:
    q = {"action": "query", "format": "json", "titles": title, "prop": "imageinfo",
         "iiprop": "url|extmetadata|mime|size", "iiurlwidth": width}
    pages = json.loads(_get(API + urllib.parse.urlencode(q)))["query"]["pages"]
    page = next(iter(pages.values()))
    if "imageinfo" not in page:
        raise RuntimeError(f"not found on Commons: {title}")
    return page["imageinfo"][0]


def fetch(titles: dict[str, str], out_dir: Path, json_path: Path, width: int = 960) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    result = {}
    for key, title in titles.items():
        ii = _info(title, width)
        m = ii.get("extmetadata", {})
        lic = _strip(m.get("LicenseShortName", {}).get("value", ""))
        if not is_free_license(lic):
            raise RuntimeError(f"{key}: license {lic!r} is not allowed ({title})")
        if ii.get("width", 0) < MIN_SOURCE_WIDTH:
            raise RuntimeError(f"{key}: source narrower than {MIN_SOURCE_WIDTH} px ({title})")
        data, w = _get(ii["thumburl"]), width
        if len(data) > MAX_BYTES or Image.open(io.BytesIO(data)).width > width:
            data = shrink_jpeg(data, MAX_BYTES, width)
        (out_dir / f"{key}.jpg").write_bytes(data)
        meta = {"author": m.get("Artist", {}).get("value", ""), "license": lic}
        result[key] = {
            "src": f"photos/{out_dir.name}/{key}.jpg",
            "title": title,
            "page": ii["descriptionurl"],
            "author": _strip(meta["author"])[:80] or "unknown",
            "license": lic,
            "license_url": m.get("LicenseUrl", {}).get("value", ""),
            "credit": credit_line(meta),
        }
        print(f"{key}: {len(data) // 1000} KB at {w} px, {lic}", flush=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    return result


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--titles", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--json", required=True)
    a = ap.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")
    titles = json.loads(Path(a.titles).read_text(encoding="utf-8"))
    fetch(titles, Path(a.out), Path(a.json))


if __name__ == "__main__":
    main()
