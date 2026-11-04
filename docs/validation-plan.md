# Validation plan (pre-registered)

**Registered:** 2026-11-04, Stage 1, before any access, capacity, or interchange
result was produced. Thresholds may be tightened later. Loosening one requires a
dated entry in the change log at the bottom with the reason, and the original
threshold stays visible.

Every result is reported as **PASS**, **FAIL**, or **NOT RUN**. A check that was not
executed is never reported as passed.

## Stage 1: pipeline smoke tests (S-series)

These test the plumbing, not the transport findings. Implemented in
`pipeline/smoke/r5py_smoke_test.py` and run by `.github/workflows/stage1-pipeline.yml`.

| ID | Test | Pass threshold |
|---|---|---|
| S0 | GTFS calendar covers the analysis date | Feed `end_date` ≥ run date. If it fails, the run continues on a date inside the feed window, the result is flagged, and the expired feed is logged as a risk. |
| S1 | R5 transport network builds from the OSM clip and myBAS GTFS | Builds without error |
| S2 | Travel time matrix computes | >0 non-null transit+walk pairs |
| S3 | Grid origins snap to the street network | ≥80% of 500 m cells within 1 km of the network snap within 250 m |
| S4 | Walking uses the street network, not straight lines | Median network/straight-line detour ratio, 0.5–2 km pairs: 1.10–1.60 |
| S5 | Transit logic | ≥5% of pairs faster by transit (≥2 min); ≤1% of pairs slower with transit than walking alone (+1 min tolerance) |
| S6 | Runtime on a free GitHub runner | ≤30 min |
| S7 | Vehicle-position feed reachable and decodable | ≥1 vehicle; newest position ≤10 min old at fetch time |

## Stages 3–5: model validation (V-series)

| ID | Test | Data | Pass threshold |
|---|---|---|---|
| V1 | GTFS validity of every draft scenario feed | MobilityData `gtfs-validator` (open source, runs in Actions) | 0 errors. All warnings listed and explained. |
| V2 | Station access points on the walk network | Draft GTFS + OSM | 100% of concept stations snap ≤50 m to a walkable edge. Each station's 800 m network catchment area must be ≥35% of the matching 800 m circle; below that, flag the station as poorly connected. |
| V3a | Modeled vs. observed bus in-vehicle times | ≥3 weeks of vehicle positions for myBAS routes in the study area, compared with r5/GTFS segment times | Median absolute percentage error ≤20%, and ≥80% of route-segment pairs within ±30% |
| V3b | Modeled vs. timed door-to-door trips | ≥10 owner-timed trips (site check SC-2) | ≥80% of trips within ±25% or ±10 min, whichever is larger; no systematic bias >15% |
| V4 | Walking catchment realism | OSM network vs. owner-timed walks at Bukit Chagar and 3 sample stations (SC-1, SC-2) | Modeled walk time within ±20% of the timed walk for ≥80% of walks |
| V5 | Scenario monotonicity | r5py outputs | Adding a line never increases any origin's median travel time by >1 min. Opportunities reachable in 30/45 min: C ≥ B ≥ A for ≥99% of origins. |
| V6 | E-ART run-time plausibility | Draft GTFS | Average commercial speed, including dwell, 20–35 km/h. Outside this band needs a cited justification. |
| V7 | Capacity and fleet arithmetic | Ops model | Hand-recomputable. Fleet = ceil(cycle time ÷ headway) + 10–15% spares. Capacity = vehicles/h × vehicle capacity. The independent recomputation in the review pack matches exactly. |
| V8 | Reproducibility | Clean Actions run from a tagged commit | Main result tables are identical (byte-equal CSVs, or ≤0.5 min median difference if R5 versions differ) |
| V9 | RTS ridership prediction | Frozen dated range (Stage 5), scored against first published ridership | **Scored, not passed:** hit if the observed first-full-month average daily ridership falls inside the frozen 80% interval. The range must be committed before the announced opening date. |
| V10 | Tebrau vs. Iskandar Puteri priority | Independent indicators (below) | See decision rule |
| V11 | Bukit Chagar bottleneck identification | Stage 4 flow model | Every element's capacity has a cited source or an explicit low/base/high range. The "first bottleneck" claim must hold across the base case and at least one of low or high; otherwise report it as uncertain. |

### V10 decision rule (registered before any corridor result)

Four indicators are computed for each corridor using the same method and inputs,
along each corridor's Stage 2 hypotheses. None of them comes from the claim's own
source.

1. Residents within an 800 m street-network walk of stations (DOSM-based)
2. Jobs or destination proxies (OSM POIs, building floor area) within an 800 m walk
3. Gain in population-weighted opportunities reachable in 45 min (B − A vs. C − B, each line also tested alone)
4. Peak-hour bus supply on parallel roads (GTFS trips/h), plus RTVM or other traffic counts if acquired

**Verdict:**
- "Independent evidence ranks Tebrau ahead" if Tebrau leads on ≥3 of 4.
- "Ranks Iskandar Puteri ahead" if Iskandar Puteri leads on ≥3 of 4.
- Otherwise "inconclusive."

**The 75% vehicle-share claim:**
- SUPPORTED if an independent cordon count puts the Tebrau corridor's share of JB
  cordon vehicles at 65–85%.
- CONTRADICTED if the share is <50%.
- UNTESTED if no count data is obtained. Without count data the claim will be
  reported as UNTESTED, not assumed.

## Change log
- 2026-11-04: plan registered (Stage 1).
- 2026-11-04: owner declined the paid RTVM report. The V10 count test uses free data only, so the UNTESTED outcome is more likely. Thresholds unchanged.
- 2026-11-04: V3a data collection started (Tue–Thu peak windows). This is a data-collection change only; thresholds unchanged.
- 2026-11-04: owner reports site checks SC-1 and SC-3 are not feasible. **V4 (walk times vs. timed walks) cannot run as written and will be reported NOT RUN.** V4-alt is added below; it is weaker and does not replace V4. V3b still depends on SC-2 (feasibility unconfirmed). Original thresholds remain as written above.

### V4-alt (added 2026-11-04; weaker substitute for V4)
- **Test:** OSM pedestrian completeness within 800 m of Bukit Chagar.
- **Pass:**
  - Every station entrance mapped in OSM connects to the walk network.
  - ≥90% of signalized or zebra crossings on the main desire lines are mapped.
  - Every grade change on those routes is tagged (steps, ramp, or elevator).
- **Report:** gaps as data limitations. This does not validate walking times; it only checks that the network R5 uses is plausible.
