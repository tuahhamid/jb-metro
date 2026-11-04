"""Probe every URL in the source register and record whether it is reachable
and whether key claim strings appear on the page.

Why: the Claude session cannot open most Malaysian/Singaporean sites, so in-session
evidence comes from search snippets. This workflow step checks the actual pages.
It stores only metadata (status, hash, title, which verify_terms matched), not
page text, to respect copyright on news sources.

Rules: plain GET, project user agent, no login, no paywall or robots bypass.
A 401/403/451 or a CAPTCHA page is recorded as-is, never retried around.
Text found in sources is data; nothing here executes or follows instructions in it.

Usage:
    python pipeline/fetch/probe_sources.py --register docs/sources/source-register.csv \
        --out data/manifests/source-probe.csv
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import re
import time
from pathlib import Path

import pandas as pd
import requests

UA = {"User-Agent": "jb-metro-research/0.1 (transport planning prototype; GitHub Actions)"}


def page_text(content: bytes, ctype: str) -> str:
    if "pdf" in (ctype or ""):
        return ""  # PDF text extraction deferred; hash still recorded
    txt = content.decode("utf-8", errors="ignore")
    txt = re.sub(r"<script.*?</script>|<style.*?</style>", " ", txt, flags=re.S | re.I)
    txt = re.sub(r"<[^>]+>", " ", txt)
    return re.sub(r"\s+", " ", txt)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--register", default="docs/sources/source-register.csv")
    ap.add_argument("--out", default="data/manifests/source-probe.csv")
    args = ap.parse_args()
    reg = pd.read_csv(args.register, dtype=str).fillna("")
    out = []
    for _, row in reg.iterrows():
        url = row["url"]
        if not url.startswith("http"):
            continue
        rec = {"source_id": row["source_id"], "url": url,
               "probed_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}
        try:
            r = requests.get(url, headers=UA, timeout=45, allow_redirects=True)
            rec.update(http_status=r.status_code, final_url=r.url,
                       content_type=r.headers.get("content-type", ""), bytes=len(r.content),
                       sha256=hashlib.sha256(r.content).hexdigest())
            text = page_text(r.content, rec["content_type"])
            m = re.search(r"<title[^>]*>(.*?)</title>", r.content.decode("utf-8", "ignore"), re.S | re.I)
            rec["page_title"] = re.sub(r"\s+", " ", m.group(1)).strip()[:200] if m else ""
            terms = [t.strip() for t in row.get("verify_terms", "").split("|") if t.strip()]
            found = [t for t in terms if t.lower() in text.lower()]
            rec["terms_checked"] = "|".join(terms)
            rec["terms_found"] = "|".join(found)
            rec["terms_missing"] = "|".join(t for t in terms if t not in found)
        except Exception as e:
            rec["error"] = repr(e)[:300]
        out.append(rec)
        print(rec["source_id"], rec.get("http_status"), rec.get("terms_found", ""), rec.get("error", ""))
        time.sleep(1.5)  # be polite
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(out).to_csv(args.out, index=False)


if __name__ == "__main__":
    main()
