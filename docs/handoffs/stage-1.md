# Handoff: Stage 1 (repo and evidence audit)

**Date:** 2026-11-04
**Branch:** `main`
**State:** Stage 1 work complete; **awaiting owner review and approval**. Do not start
Stage 2 until the owner approves it in writing.

The governing brief is `docs/project-brief.md`. Read it first, then this note, then
`docs/evidence-audit.md`.

## What was completed

1. **Repo structure and README.** Layout, status labels, and how to run are in `README.md`.
2. **Source register.** `docs/sources/source-register.csv` holds 40 sources with URL,
   access date, publisher, tier, confidence, license and usage, limitations, access method,
   and the probe outcome. James Clark's concept map is registered as **excluded** (SRC-031).
3. **Assumptions log.** `docs/assumptions/assumptions-log.csv` holds 25 entries, each with
   a `kind` (fact, assumption, inference) and a `status` (existing, official, inferred,
   concept), plus low/base/high values where relevant.
4. **Evidence audit.** `docs/evidence-audit.md` covers what is known, unknown, and
   conflicting, the RTS ridership bound, and the status of the 75% claim.
5. **RTS ridership conflict bounded.** Reproducible with
   `pipeline/analysis/rts_ridership_bounds.py`. 40,000/day is an opening forecast;
   122,500/day is a mature, capacity-constrained upper case. Peak flow at Bukit Chagar is
   capped by the 10,000 pphpd design capacity.
6. **Validation plan pre-registered.** `docs/validation-plan.md` defines S0–S7 (pipeline)
   and V1–V11 (model), including the V10 decision rule for Tebrau vs. Iskandar Puteri.
   The thresholds were set before any results existed.
7. **Site checks for the owner.** `docs/site-checks.md` lists SC-1 to SC-6 with priorities.
8. **Web-only pipeline proven.** `.github/workflows/stage1-pipeline.yml`:
   1. Fetches data.gov.my GTFS and vehicle positions.
   2. Fetches and clips Geofabrik OSM.
   3. Probes every source URL (metadata only).
   4. Runs r5py 1.1.7 on Java 21.
   5. Commits the outputs back to the branch.
9. **Design system access confirmed.** Buruh Hybrid tokens are snapshotted in `docs/design/`.

## Key decisions and why

| Decision | Why |
|---|---|
| Fetch data in GitHub Actions, not in the Claude session | The session's network policy blocks data.gov.my, Geofabrik, and all MY/SG news and government hosts. The brief requires a workflow in that case. |
| Probe stores metadata and term matches only, not page text | Copyright on news sources. Still lets us confirm that claimed figures appear on the live page. |
| No access restriction bypassed | 403 responses (SRC-036) and a TLS hostname mismatch (mbjb.gov.my) were recorded, not worked around. |
| RTS opening treated as **February 2027** | The joint statement of 2026-10-02 supersedes the January 2027 reports. |
| E-ART B/C scenarios are future-network concepts on 2027 land use | E-ART cannot open before ~2030 (4 years from a letter of acceptance not yet confirmed). We do not invent land-use growth. |
| E-ART capacity range 3,000 / 5,000 / 10,000 pphpd | Reports conflict. 12,000 is excluded until a vehicle spec exists. |
| The 75% claim is never a model input | The brief requires testing it. V10 reports it as UNTESTED if no count data is obtained. |
| OSM clip and GTFS zips committed (4.2 MB + 4.9 MB) | Reproducibility. The workflow reuses the pinned OSM clip unless `refresh_osm` is set. |

## Validation results (only checks that actually ran)

From the Actions runs. The definitive run is 41818831614 at commit `c151634`; outputs
are committed in `18a09bd`.

| Test | Result | Value | Threshold |
|---|---|---|---|
| S0 GTFS calendar current | PASS | myBAS valid 2026-10-05 to 2027-02-02 | end ≥ run date |
| S1 network builds | PASS | | |
| S2 matrix computed | PASS | 417,962 pairs | >0 |
| S3 origin snapping | PASS | 0.891 | ≥0.80 |
| S4 walk detour median | PASS (near upper bound) | 1.568 | 1.10–1.60 |
| S5 transit logic | PASS | 22.0% faster; 0.0% slower | ≥5%; ≤1% |
| S6 runtime | PASS | 0.6 min | ≤30 min |
| S7 vehicle positions | PASS | 115 vehicles, newest 20 s old | ≥1; ≤10 min |

- **Repeat run:** run 41817401708 (commit `6b0d02e`, earlier code) produced identical S-values. This is an informal reproducibility signal, not V8.
- **Not run:** V1–V11. They belong to Stages 3–5.

## Known risks

1. **Workflow triggering.**
   - Pushes from the Claude session did **not** trigger runs. Runs were started by `workflow_dispatch` through the API.
   - The first commit-back push failed with GitHub HTTP 500 three times. The workflow now fails loudly if all pushes fail, and the outputs are always uploaded as an artifact.
   - Artifact downloads are blocked from the Claude session (Azure blob host). Use committed outputs or job logs.
2. **E-ART alignment unpublished.** All Stage 2 geometry will be `concept`. The project could draw an alignment that later differs from the official one.
3. **Line lengths unconfirmed** (14 km and 14.78 km). The probe did not find them on the cited page.
4. **Scope risk for Scenario C.** October 2026 expert proposals name Skudai–Tampoi–Larkin and Tebrau–Pandan as priority corridors, not Iskandar Puteri (SRC-009, SRC-010).
5. **Population data granularity.** DOSM public data found so far is at parliament/state-seat level. Stage 3 needs a disaggregation method.
6. **Baseline completeness.** Causeway Link and other private buses are absent from open GTFS.
7. **KTMB GTFS calendar** ends 2026-11-18. It is refreshed daily, so re-fetch before Stage 3.
8. **Vehicle-position history** does not exist publicly. V3a needs ≥3 weeks of collection, so it should start early.
9. **Cost items (not used; flagged):**
   - RTVM traffic-count report (paid).
   - GitHub Pages on a private repo (paid plan).
   - Mapbox (account; avoid by using MapLibre plus free tiles).
   - Private-repo Actions minutes count against the free allowance.
10. **Statutory plans:** RSNJ 2030 and RTJB 2035 status and content are not yet read (PDFs).

## Open questions for the owner (decisions needed)

1. **Approve Stage 1?**
2. **Scenario C scope.** Keep Iskandar Puteri as specified, or also test Skudai, given the October 2026 expert priority list? Recommendation: keep C as specified. Report Skudai only as a sensitivity note, unless you want it added.
3. **Vehicle-position collection.** Start a scheduled Actions collector now (e.g., every 10 minutes during peaks), stored outside the main history (separate data branch or monthly bundles)? It uses free minutes. Recommendation: yes, start before Stage 3.
4. **RTVM traffic counts.** Buy the RTVM 2024 report (paid) to test the 75% claim, or accept "UNTESTED" if no free count data is found?
5. **Final hosting.** Make the repo public at Stage 6 for free GitHub Pages, or host as a Claude artifact?
6. **Site checks.** Can you do SC-1 and SC-3 (P1) before Stage 3?

## Exact scope of Stage 2 (alignment hypotheses), to start only after approval

1. **Refresh status.** Re-search E-ART news since 2026-11-04 for any published alignment,
   station list, letter of acceptance, or vehicle spec. If an official alignment appears,
   it replaces the hypotheses as `official`.
2. **Obtain primary inputs** via a new Actions workflow:
   - OSM extract for the full study area (Tebrau to Iskandar Puteri). Use roads with `width` and `lanes` tags, landuse, and buildings.
   - Elevation (Copernicus GLO-30 DEM, free) for terrain.
   - Any free flood-hazard layer (e.g., JRC global flood maps) as a coarse screen only.
   - The JPBD Johor plan list (SRC-026) and RSNJ 2030 / RTJB 2035 documents, if they are public.
3. **Build 2–3 alignment options per corridor** (Tebrau, Iskandar Puteri). All terminate at
   or link to Bukit Chagar. Each carries status `concept`. Check each option's length
   against the reported lengths (±15%) and record any deviation.
4. **For each option, record** in `docs/alignments/` and `data/concept/*.geojson`:
   - Road reserve and median width evidence (OSM tags; SC-4 photo needs).
   - Viaduct column space.
   - Candidate depot land (vacant or government land from OSM landuse).
   - Grades from the DEM.
   - Flood screen.
   - Interchange walking access at Bukit Chagar and at KTM/BAS.MY hubs.
   - Stations every ~1–1.5 km, placed by network-walk catchment logic.
   - Reasons for each choice, and **rejected options with reasons**.
5. **Do not copy** geometry from James Clark's map or from any unofficial map. Do not present any option as official.
6. **Deliverables:**
   - Option GeoJSON with per-feature `status` and `source_ids`.
   - Option comparison table.
   - Updated register and assumptions log.
   - The site-check list for SC-4 and SC-5.
   - `docs/handoffs/stage-2.md`.
7. **Out of scope for Stage 2:** draft GTFS, run times, access results, and the Bukit Chagar flow model (Stages 3–4).

## How to resume

1. `git clone https://github.com/tuahhamid/jb-metro`, then read `docs/project-brief.md` and this note.
2. To re-run Stage 1, go to the Actions tab → **stage1-pipeline** → **Run workflow**. From a Claude session, POST a `workflow_dispatch` to `/repos/tuahhamid/jb-metro/actions/workflows/stage1-pipeline.yml/dispatches` with `{"ref":"main"}` and header `Content-Type: application/json`.
3. Outputs are committed to `results/stage1/` and `data/manifests/`. Job logs are readable through the Actions API.
