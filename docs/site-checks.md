# Site checks for the project owner

These are things the web-only workflow cannot establish. Do them only in
public areas. Do not enter construction sites, restricted CIQ zones, or private
land, and do not photograph officers or security installations. Record each check
in `data/site-checks/<id>-<date>.csv` (template columns below). Photos go
in `data/site-checks/photos/` with faces and plates blurred.

Priority: **P1** is needed before Stage 3 or 4 results. **P2** is needed for Stage 5
validation. **P3** is useful.

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
