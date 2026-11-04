# Handoff: Stage 2 (alignment hypotheses)

**Date:** 2026-11-04
**Branch:** `claude/loving-ramanujan-vl0spd`, not yet merged to `main`.
**State:** Stage 2 draft complete, **awaiting owner review.** Stage 3 has not started.

Read `docs/project-brief.md`, then `docs/handoffs/stage-1.md` (owner decisions), then
this note, then `docs/alignments/options.md`.

## What was completed

1. **Status refresh** (`docs/evidence-audit.md` §7):
   - There is still no published E-ART alignment and no letter of acceptance.
   - Depots are still being agreed with the state.
   - The technology (rubber-tired ART vs. rail/APM) is now unclear.
   - The 2024 line lengths have two more sources.
   - The JPBD list shows RSN Johor 2030 gazetted.

   No official alignment exists, so all geometry stays `concept`.
2. **Primary inputs via a new workflow** (`.github/workflows/stage2-alignments.yml`), all
   fetched successfully in the definitive run 41886438950:
   - OSM study-area clip (103.55–103.88 E, 1.38–1.62 N, tag-filtered, 12.5 MB, committed);
   - Copernicus GLO-30 DEM;
   - JRC RP100 river-flood tile;
   - the JPBD plan list (SRC-026).

   Manifests are in `data/manifests/osm-study.json` and `stage2-inputs.json`.
3. **Options:**
   - **Tebrau:** 3 carried (T1–T3) and 2 rejected with metrics (T-R1 EDL, T-R2 Larkin).
   - **Iskandar Puteri:** 4 carried (IP1–IP4).
   - Two options were rejected without drawing geometry (IP-R1 Skudai/Tampoi, IP-R2 E3),
     and one excluded source (T-R3).
   - Spec: `pipeline/stage2/options.json`. Builder: `pipeline/stage2/build_alignments.py`.
4. **Per option:**
   - Length vs. reported (±15%).
   - Stations at 1.0–1.5 km, placed by exclusive 800 m network-walk catchments.
   - Road reserve (lanes, dual carriageway, façade setbacks).
   - Curves, flyovers, and rail/river crossings.
   - DSM grades.
   - JRC and DEM flood screens.
   - Depot land from OSM.
   - Bukit Chagar walking access.
   - Bus and KTM connections.
5. **Deliverables:**
   - `data/concept/alignments.geojson`, `stations.geojson`, `depot-candidates.geojson`. Every
     feature carries `status` and `source_ids`.
   - `results/stage2/option_comparison.csv`, `pinch_points.csv`, `flood_spots.csv`,
     `interchange_access.csv`, `segments.csv`, `ip_shortest_road_km.json`,
     `v4alt_bukit_chagar.json`, `options-map.png`.
   - `docs/alignments/README.md` (method) and `options.md` (results, pinch-point and
     flood-spot lists, rejected options).
6. **Register and log updated:**
   - Source register: SRC-041 to SRC-052; SRC-021 and SRC-026 updated.
   - Assumptions log: A-026 to A-036; A-013, A-014, A-015, and A-021 updated.
   - `docs/site-checks.md` points to the SC-4 and SC-5 substitute lists.
   - `data/LICENSES.md` covers the new data.
7. **Security re-scan:** clean (`docs/security-review.md`, last section).

## Key decisions and why

| Decision | Why |
|---|---|
| Routes follow OSM road reserves between named trip generators. Spine roads are weighted ×0.3 and expressways ×4 unless the option is about one (A-026). | Elevated lines are normally built over road reserves. The route is reproducible, and no unofficial map is used. |
| Via-points only at termini; intermediate centers become forced stations only if within 500 m of the line | The first runs showed via-points pulling routes into detours (e.g., IP4 at 18.3 km instead of 15.0 km) |
| Stations by exclusive-catchment dynamic programming on a floor-area proxy (A-028) | Only consistent activity measure in OSM before Stage 3 population data. Stage 3 re-scores. |
| No station within 25 m of water unless forced | The first definitive run put a station on the Sungai Skudai bridge |
| Curve and grade screens use both rail and ART thresholds (A-030, A-031) | Technology unresolved (A-035) |
| EDL option (T-R1) rejected on metrics, not assumption | Same length as T1 but 31% less floor area, the lowest Tebrau catchment ratio, and a median of 1 bus route vs. 3 |
| IP4 added after the first run | The shortest road distance from Bukit Chagar to Bukit Indah (14.77 km) matched the reported 14.78 km |
| End-of-stage self-check fix: forced anchors within 150 m of a line end snap to it; forced stations closer than 0.8 km merge; 0.8 km minimum next to forced stations (A-028) | The self-check found a duplicate Bukit Chagar station 6 m from the first on every option, and undocumented 0.6 km gaps. Fixed and re-run (41886438950). Earlier runs' station counts are superseded. |
| V4-alt operationalized and logged in `docs/validation-plan.md` | No ground truth exists. One refinement after the first smoke-clip result is disclosed there. |

## Validation results (only what ran)

| Test | Result | Value | Threshold |
|---|---|---|---|
| V4-alt (a) entrances connect | **NOT EVALUABLE** | 0 entrances mapped within 250 m | all connected |
| V4-alt (b) crossings mapped | **FAIL** | 2 of 18 (11%) | ≥90% |
| V4-alt (c) grade changes tagged | **FAIL** | 1 of 6 | all |
| V4-alt overall | **FAIL** | | |
| Length check (not a registered V-test; brief's ±15% rule) | 5 of 9 options within the band: T1, T3, T-R1, T-R2, IP4 | see `options.md` §1 | ±15% |
| Reproducibility (informal) | Local rerun reproduced the comparison table exactly | | |

**Not run:** V1–V3, V5–V11. They belong to Stages 3–5. V2 needs the draft GTFS
stations; `options.md` shows preliminary catchment ratios, which are *not* a V2 result.
**V4 and V3b remain NOT RUN** (no fieldwork).

## Main findings (all inferred or concept)

1. The **FT3 Tebrau spine (T1) is 14.07 km**, matching the reported 14 km.
2. **No road route from Bukit Chagar reaches Kota Iskandar under 20.9 km.** Bukit Chagar to
   **Bukit Indah is 14.77 km**, matching the reported 14.78 km. A single 14.78 km line from
   Bukit Chagar to the Iskandar Puteri administrative center is not possible on road
   reserves (A-036).
3. Viaduct *space* on the FT3 and coastal spines is mostly ample. The constraints are:
   - junction curves (25–45 m radii);
   - 5–10 existing flyovers per option;
   - the first 0.3 km at Bukit Chagar, where every option must cross the KTM line and the
     RTS viaduct beside the ICQ.
4. The OSM pedestrian network around Bukit Chagar is incomplete (V4-alt FAIL). The walk
   from the E-ART station point is 929 m to JB Sentral (2.1× straight-line) and 1,390 m to
   the ICQ (11×).
5. Iskandar Puteri options have weak walk catchments (median ratio 0.27–0.30) and almost no
   BAS.MY service near stations.

## Known risks

1. **The official alignment may differ.** It is reportedly agreed between the consortium
   and the state but unpublished (SRC-043). Re-search before Stage 3 and Stage 6.
2. **Technology may be rail or APM, not ART** (SRC-044). That affects curves, grades, and
   capacity (A-012).
3. **Anchor choice is a judgment.** It is documented in `options.json` but subjective.
   Different trip generators would give different routes.
4. **Floor-area proxy** (footprint × levels where tagged; most buildings lack levels)
   understates high-rise areas.
5. **DSM, not terrain:** grades include buildings and trees.
6. **JRC is river-only.** Flash and tidal flooding is represented only by news leads.
7. **Depots:** OSM has no ownership data. Some candidates are likely committed
   developments, and one is tagged as a kampung.
8. **Bukit Chagar walking on raw OSM is unreliable** (V4-alt). Stage 3 and Stage 4 results
   there need explicit handling (decision 3).
9. **KTMB GTFS calendar ends 2026-11-18.** Re-fetch before Stage 3.
10. **IP4 shares its first ~6 km of FT1 with a likely Skudai line.** If the official Skudai
    line takes that reserve, IP4 and Skudai would share track or a corridor.
11. **The workflow triggers on `claude/**` pushes.** That was needed because a
    `workflow_dispatch` file must exist on `main` before it can be dispatched by API. After
    merging, the `main` trigger and manual dispatch both work.

## Decisions needed from the owner

1. **Approve Stage 2?**
2. **Which options go into Stage 3?**
   - Scenario B, recommended: **T1 as base.** It matches the length, has the fewest
     curves, and has good bus connections. T2 and T3 are variants that share the spine.
   - Scenario C, recommended: **IP2 as base.** It is coastal, avoids the Skudai reserve,
     and has 58% more floor area than IP4, at +20% length.
   - Also carry IP4 (length-consistent) and IP1 (reaches Kota Iskandar, 25 km) as
     sensitivities. Drop IP3: it is the longest, has the poorest catchment, and misses
     Bukit Indah's center.
   - Alternative: make IP4 the base because it matches the reported length.
3. **Bukit Chagar walking network for Stages 3–4.**
   - Recommendation: report raw OSM as the **high (pessimistic)** case.
   - Add a small, documented local patch for the **base** case: concept footway links
     between the RTS station, the E-ART station, JB Sentral, and the bus bays, labeled
     `concept`, kept in the repo only, and never uploaded to OSM.
   - Alternatively, use raw OSM only and accept that results will be poor.
4. **OSM contributions.** Should the project leave OSM untouched? Recommendation: yes. We
   cannot survey, so we should not edit OSM.

## Exact scope of Stage 3 (operations and access model), after approval

1. **Refresh** BAS.MY and KTMB GTFS (`stage1-pipeline`). Re-search E-ART news. If an
   official alignment appears, add it as `official` and compare it with the hypotheses.
2. **Population and destinations:** decide and implement the DOSM disaggregation (A-025),
   using building footprints or GHSL, sum-preserving to DOSM totals. Destinations: OSM POIs
   and building floor area.
3. **Re-score stations** of the chosen options with residents and jobs proxies. Keep
   spacing at 1.0–1.5 km; record any station moves.
4. **Draft GTFS** per scenario:
   - A: existing BAS.MY + KTMB + RTS Link (A-005, A-007).
   - B: A + the chosen Tebrau option.
   - C: B + the chosen IP option(s).

   Use low/base/high run times (V6: 20–35 km/h commercial speed), headways, fleet
   (V7 arithmetic), and capacity (A-012).
5. **r5py access:** people and destinations reachable in 30 and 45 minutes, with a
   ≤250 m grid. Windows: 07:00–08:00, plus 17:30–18:30 for Bukit Chagar dispersal.
   Walk speeds 3.0 / 3.6 / 4.5 km/h. Use street-network catchments (V2), not circles.
6. **Run V1** (gtfs-validator), **V2**, **V5**, **V6**, and **V7**. Report each as
   PASS, FAIL, or NOT RUN.
7. **Bukit Chagar walking per decision 3.**
8. **Out of scope:** the Bukit Chagar flow model (Stage 4), any ridership forecast, and
   the frozen RTS prediction (Stage 5).

## How to resume

1. Check out `claude/loving-ramanujan-vl0spd`, or `main` after merge.
2. Re-run Stage 2: push under `pipeline/stage2/`, or use Actions → **stage2-alignments** →
   **Run workflow**. Dispatch works only once the workflow file is on `main`.
3. Read `results/stage2/run_metadata.json` for the run and commit behind the committed
   outputs: run 41886438950 at `b1295bb`, committed in `c908890`.
4. The vehicle-position collector continues on branch `vp-data`. V3a data should be ready
   around 2026-11-26.
5. Re-run the security scan (`docs/security-review.md`) before each handoff.
