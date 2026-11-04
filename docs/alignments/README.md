# Stage 2: alignment hypotheses

**Status of everything in this folder and in `data/concept/`: `concept` (lines, stations)
or `inferred` (screening values).** No line, station, or depot here is an official E-ART
alignment. The E-ART alignment, stations, depots, and vehicle are unpublished as of
2026-11-04 (A-014, SRC-043). No geometry was copied from James Clark's map or any other
unofficial map (SRC-031). Every route was computed from OpenStreetMap road reserves
between trip generators that we chose and justified.

No field observations were made (owner decision 6). Cross-section, flood, and walking
results are web-only screens. They are weaker than the site checks SC-1, SC-4, and SC-5
they replace.

## How the options were built (reproducible)

`pipeline/stage2/build_alignments.py`, run by `.github/workflows/stage2-alignments.yml`.
The options are defined in `pipeline/stage2/options.json`.

1. **Anchors.** Each option is a sequence of anchors: Bukit Chagar RTS station, malls,
   neighborhood centers, and termini. Each anchor is resolved to a named OSM feature.
   The run report (`results/stage2/run_report.json`) records the OSM id, or says that a
   fallback coordinate was used.
2. **Routing on road reserves (A-026).** The OSM road graph (tertiary and above) is
   searched between consecutive anchors.
   - Roads named in the option spec are weighted ×0.3.
   - Otherwise trunk ×1.0, primary ×1.05, secondary ×1.3, tertiary ×1.8.
   - Expressways ×4, unless the option is about an expressway.
   - Loops and spurs are cut out of the path.
3. **Stations (A-027, A-028).** Candidates are placed every 100 m along the line. Each
   candidate gets an 800 m street-network walk catchment on the OSM walk graph, scored by
   a building floor-area proxy: footprint × `building:levels` where tagged, else × 1.
   A dynamic program then picks stations that maximize the *unique* (non-overlapping)
   floor area, with 1.0–1.5 km spacing. The interchange and terminus stations listed in
   the spec are forced, with these rules:
   - A forced station may sit 0.8–1.0 km from a neighbor.
   - Anchors within 150 m of a line end become that end.
   - Forced anchors that project less than 0.8 km apart share one station.
   - Anchors more than 500 m from the line are not forced. They are reported as "not
     served".
   - No candidate within 25 m of a waterway or the coastline is used, so no station sits on
     a river bridge.
4. **Screens per 100 m segment and per station:**
   - **Road reserve.** OSM `highway`, `lanes`, `width`, and one-way pairs, which mark dual
     carriageways and medians.
   - **Building-to-building clear width.** Measured with 60 m rays from the route
     centerline to OSM footprints (A-029). This is the SC-4 web-only substitute.
   - **Curve radius** at 40 m chord spacing (A-030).
   - **Rail, river, and flyover crossings** from OSM geometry.
   - **Ground grade** from Copernicus GLO-30. It is a surface model, so it is smoothed
     (A-031).
   - **Flood.** JRC RP100 river-flood depth, plus a DEM low-lying-near-water proxy (A-032).
     News reports are leads only. This is the SC-5 substitute.
   - **Depot land** from OSM landuse (A-033). Ownership is unknown.
   - **Interchange walking access** at Bukit Chagar: network walk from the first station
     to the RTS station, JB Sentral (KTM), the JB Sentral bus terminal, the ICQ, and
     Larkin Sentral.
   - **Bus and KTM connections** at each station (A-034), from the committed GTFS feeds.
5. **Length check.** Each option's length is compared with the reported line length:
   Tebrau 14 km, Iskandar Puteri 14.78 km (A-013), with a ±15% band.

## Outputs

| File | Content |
|---|---|
| `data/concept/alignments.geojson` | One line per option, with `status`, `source_ids`, `decision` (carried or rejected), length, and deviation |
| `data/concept/stations.geojson` | Stations with catchment, bus, KTM, and flood attributes |
| `data/concept/depot-candidates.geojson` | Up to 5 landuse polygons per option (`inferred`; ownership unknown) |
| `results/stage2/option_comparison.csv` | The comparison table summarized below |
| `results/stage2/pinch_points.csv` | Narrow cross-sections, tight curves, crossings, steep ground |
| `results/stage2/flood_spots.csv` | Stations flagged by JRC or the DEM proxy |
| `results/stage2/interchange_access.csv` | Walk distances at Bukit Chagar |
| `results/stage2/segments.csv` | Every 100 m segment's screen values |
| `results/stage2/v4alt_bukit_chagar.json` | V4-alt pedestrian audit |
| `results/stage2/options-map.png` | Overview map (concept labeling on the map) |

Results and the comparison are in [`options.md`](options.md).
