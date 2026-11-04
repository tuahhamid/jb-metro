# Site checks for the project owner

These are things the web-only workflow cannot establish. Do them only in
public areas. Do not enter construction sites, restricted CIQ zones, or private
land, and do not photograph officers or security installations. Record each check
in `data/site-checks/<id>-<date>.csv` (template columns below). Photos go
in `data/site-checks/photos/` with faces and plates blurred.

Priority: **P1** is needed before Stage 3 or 4 results. **P2** is needed for Stage 5
validation. **P3** is useful.

**Status 2026-11-04: no physical site checks are feasible** (owner decision). None of SC-1 to SC-6 will be done. The table is kept for the record. Every check has a web-only substitute, listed below, and each substitute is weaker than the field check it replaces.

| ID | Priority | What | Where | When | Why (test) |
|---|---|---|---|---|---|
| SC-1 | P1 | Walk and time the public routes from Bukit Chagar station entrances to bus bays, taxi and e-hailing pickup, JB Sentral/BSI, and the city center. Count stairs, escalators, and lifts on each route and note any closed links. Measure the narrowest walkway width (phone measure app is fine). | Bukit Chagar surroundings (public roads and walkways) | Weekday 07:30–09:00 and 17:30–19:00 | Stage 4 walking routes and vertical circulation; V4 |
| SC-2 | P2 | ≥10 timed door-to-door trips on BAS.MY routes in the test area, ideally including Jalan Tebrau and the Skudai Highway/Iskandar Puteri direction. Log walk, wait, and in-vehicle times (phone GPS track if you can). | JB city, Tebrau, toward Iskandar Puteri | Weekday AM peak | V3b, V4 |
| SC-3 | P1 | Check whether the BAS.MY routes in the GTFS actually run as published. Note route numbers seen at 3–4 stops, plus non-GTFS operators (Causeway Link, etc.) and their frequency. | JB Sentral, Bukit Chagar area, Tebrau, Taman Universiti | Any weekday, 30 min per stop | A-019/A-020 baseline completeness |
| SC-4 | P2 | Photograph road cross-sections at pinch points along candidate alignments: median width, existing flyovers, utilities, building setbacks. The list of points is produced in Stage 2. | Stage 2 list | Daytime | Stage 2 viaduct-space assumptions |
| SC-5 | P3 | Note known local flooding spots (from residents or news) near candidate stations or depots | Stage 2 list | Any | Stage 2 flood constraints |
| SC-6 | P2 | After RTS opening (target Feb 2027): time the full Bukit Chagar departure sequence (entrance to e-gate to platform) and the arrival sequence (platform to street) in peaks. Count open e-gate lanes. | Bukit Chagar | First 4 weeks after opening | Stage 4 border processing; V9 context |

**Template columns:** `check_id, date, start_time, end_time, location_from,
location_to, mode, minutes, distance_m, stairs, escalators, lifts,
min_width_m, notes, observer`

## Web-only substitutes (owner decision 2026-11-04: no fieldwork)

| Check | Substitute (web-only) | What is lost |
|---|---|---|
| SC-1 Bukit Chagar walking routes and vertical circulation | 1. OSM pedestrian-network audit around Bukit Chagar: footways, crossings, `highway=steps`, `elevator`, `conveying`, `width` tags (V4-alt).<br>2. Official station or ICQ documents and published walking-time claims, if any.<br>3. Stage 4 treats stair, escalator, and lift counts and walkway widths as low/base/high ranges, labeled `inferred`. | No ground truth for walk times or pinch-point widths. Stage 4 bottleneck findings carry wider uncertainty and must say so. V4 cannot run as written. |
| SC-3 Do buses run as published? Non-GTFS operators | 1. **Vehicle-position data** (already collecting): compare routes and trips observed in `vp-data` with GTFS-scheduled trips per peak window.<br>2. Non-GTFS operators (e.g., Causeway Link): use their published route lists and timetables as **leads** to bound the missing service; label the result `inferred`. | No on-street count of private operators. The baseline gap stays a stated limitation. |
| SC-2 Timed door-to-door trips | Vehicle positions (`vp-data`) give observed in-vehicle and stop-to-stop times for BAS.MY (V3a). Walk and wait legs are not observed. | V3b cannot run and will be reported NOT RUN. Door-to-door accuracy is unvalidated; only in-vehicle times are checked. |
| SC-4 Road cross-section photos at pinch points | OSM `width`/`lanes` tags, building footprints vs. road centerlines (setback estimates), and published road-scheme documents where available. Street-level imagery is used only if a free, license-compatible source is confirmed (e.g., Mapillary needs a free account and token; flagged before use). | Viaduct-space findings in Stage 2 are screening-level and labeled `inferred`. |
| SC-5 Local flood spots | Free global or national flood layers (e.g., JRC flood hazard maps), the DEM, and news reports of flooded roads as leads only | Local hotspots may be missed. Flood screening is coarse. |
| SC-6 Bukit Chagar timings after opening | Official RTS/ICQ statements, published processing times, and operator ridership releases after opening. News is used only as leads. | Stage 4 border-processing and circulation results rest on published claims and low/base/high ranges, not observation. |
