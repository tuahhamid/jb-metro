"""Bound the RTS Link ridership conflict (40,000/day vs 35% x 350,000 = 122,500/day).

Pure arithmetic on documented inputs. Every input carries a status label and a
source ID from docs/sources/source-register.csv. This is NOT a forecast; the
frozen pre-opening prediction is a Stage 5 deliverable.

Usage:
    python pipeline/analysis/rts_ridership_bounds.py --out results/stage1/rts_ridership_bounds.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

INPUTS = {
    # name: (value, status, source_id, note)
    "line_capacity_pphpd": (10_000, "official", "SRC-003|SRC-004", "design capacity per hour per direction"),
    "train_capacity_pax": (600, "inferred", "SRC-011", "reported ~600 per 4-car train; not confirmed by operator"),
    "peak_headway_min": (3.6, "inferred", "SRC-011", "most-reported peak headway; not confirmed by operator"),
    "operating_hours": (18, "inferred", "SRC-011", "reported 06:00-24:00; final hours not announced"),
    "claim_opening_daily": (40_000, "official", "SRC-003", "MRT Corp: expected ridership on opening"),
    "claim_share": (0.35, "official", "SRC-005", "MRT Corp 2022: share of Causeway travelers"),
    "claim_causeway_daily": (350_000, "official", "SRC-005", "pre-pandemic Causeway travelers/day used with the 35% claim"),
    "woodlands_daily_2024": (327_000, "official", "SRC-012", "ICA: average daily travelers via Woodlands Checkpoint, 2024"),
}
# Peak-direction peak-hour flow as a share of two-way daily ridership.
# Assumption A-010 (inferred): commuter peak hour ~8-12% of daily two-way trips,
# tidal split 60/40 to 80/20 for cross-border commuting -> 5%-10%, base 6.5%.
K_PEAK = {"low": 0.05, "base": 0.065, "high": 0.10}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="results/stage1/rts_ridership_bounds.json")
    args = ap.parse_args()
    v = {k: x[0] for k, x in INPUTS.items()}
    claim_b = round(v["claim_share"] * v["claim_causeway_daily"])
    tph = 60 / v["peak_headway_min"]
    res: dict = {
        "inputs": {k: {"value": x[0], "status": x[1], "source": x[2], "note": x[3]} for k, x in INPUTS.items()},
        "k_peak_assumption": K_PEAK,
        "consistency_capacity_from_headway_x_train": round(tph * v["train_capacity_pax"]),
        "claim_A_daily": v["claim_opening_daily"],
        "claim_B_daily": claim_b,
        "ratio_B_over_A": round(claim_b / v["claim_opening_daily"], 2),
        "share_of_2024_woodlands": {
            "A": round(v["claim_opening_daily"] / v["woodlands_daily_2024"], 3),
            "B": round(claim_b / v["woodlands_daily_2024"], 3),
        },
        "implied_peak_pphpd": {}, "implied_peak_utilization": {},
        "theoretical_daily_ceiling_flat": v["line_capacity_pphpd"] * 2 * v["operating_hours"],
        "practical_daily_ceiling_at_peak_saturation": {},
    }
    for case, k in K_PEAK.items():
        for name, daily in (("A", v["claim_opening_daily"]), ("B", claim_b)):
            pph = daily * k
            res["implied_peak_pphpd"][f"{name}_{case}"] = round(pph)
            res["implied_peak_utilization"][f"{name}_{case}"] = round(pph / v["line_capacity_pphpd"], 2)
        res["practical_daily_ceiling_at_peak_saturation"][case] = round(v["line_capacity_pphpd"] / k)
    res["interpretation"] = (
        "A (40,000/day) and B (122,500/day) are different quantities. A is an opening-period "
        "forecast; B is a market-share target that, under the stated peaking assumption, would load "
        "the peak direction to roughly 61-123% of the 10,000 pphpd design capacity. B is therefore "
        "best read as a mature, capacity-constrained upper case, not an opening-year figure. "
        "For the Bukit Chagar stress test, peak flow is capped by line capacity (10,000 pphpd) "
        "regardless of which daily figure is right."
    )
    res["stage1_planning_bounds_daily"] = {
        "low": 25_000, "base": 40_000, "high": 80_000, "mature_upper": round(claim_b),
        "status": "inferred",
        "basis": "low = slower ramp-up (assumption A-011); base = official opening forecast; "
                 "high = 2x official, about the level where base peaking reaches ~50% of capacity; "
                 "mature_upper = claim B. Not a forecast; replaced by the frozen Stage 5 range.",
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(res, indent=2))
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
