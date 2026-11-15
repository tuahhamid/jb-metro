# Handoff: JB Metro Explorer (first release, not yet published)

**Date:** 2026-11-15
**Branch:** `claude/explorer-design` (not merged, not pushed)
**Design:** `docs/superpowers/specs/2026-11-14-jb-metro-explorer-design.md`
**Plan:** `docs/superpowers/plans/2026-11-14-jb-metro-explorer.md`
**Scope change:** `docs/handoffs/2026-11-14-scope-change.md`

## What was built

- **Track geometry pipeline** (`pipeline/explorer/`). It turns the Stage 2 concept routes into track-like lines:
  - curves are 150 m radius, with 100 m allowed only as a flagged exception;
  - each station sits on a 160 m straight;
  - station centers never move.
- **The two lines:**
  - Tebrau (T1) now runs to Ulu Tiram: 19 stations, 19.0 km, 59 curves, all 150 m.
  - Iskandar Puteri (IP2) skips the north-east detour: 15 stations, 15.3 km, 39 curves, all 150 m.
  - No curve is below 150 m and the station error is 0 m (`results/explorer/jb_track_report.json`).
- **Station names** follow a unique-name rule: landmark, then neighbourhood, then "road km". Three names were overridden by hand, with reasons in `pipeline/explorer/jb.json`.
- **17 photos** from Wikimedia Commons, downloaded with credits (`site/data/jb/photos.json`).
- **The explorer site** (`site/`), with no build step:
  - Intro: a slow orbit, "Start the tour" and "Skip intro".
  - Tour: 8 stops, each with a photo or a 3D snapshot.
  - Places 3D: every station, with a map key and Reset.
  - It has a line switcher (Mutiara and MRT3 show "Coming soon") and keyboard arrows.
  - Reduced motion is respected and narrow screens get a mobile bottom sheet.
  - If the base map fails to load, a notice appears and the lines and stations still draw.
- **Internal debug view:** `?debug=1` shows the old road route (dashed) and the buildings the track crosses (red dots). T1 crosses 14 and IP2 crosses 26. These never appear in the default view.
- **Pages workflow** `explorer-pages.yml` runs only when started by hand. **It has not been run.**
- **Collector:** the `vp-collector` schedule is off, and it can still be started by hand.

## Your review list (one pass, spec §5.9)

1. **Line colors.** These extend Buruh Hybrid, which has no line colors:

   | Line | Color |
   |---|---|
   | Tebrau | `#FF6A13` |
   | Iskandar Puteri | `#2E8C83` |
   | RTS Link | `#13213A` |
   | KTM | `#8C8577` |
   | Mutiara (later) | `#E8C547` |
   | MRT3 (later) | `#8F7CF0` |

2. **Station names:** `results/explorer/jb_station_names.csv`. The `rule_used` column shows how each name was picked. Points to look at:
   - Six stations have a "road km" name, for example "Jalan Kota Tinggi km 15.4". The km is the distance along the line from Bukit Chagar.
   - Three names were overridden by hand: T1-02 "Kim Teng Park", T1-09 "Taman Istimewa" and T1-14 "Desa Jaya". The rule had picked two condo names and a road-like tag.
   - T1-04 is near KSL City but is named "Melodies Garden", because KSL is 530 m away, beyond the 300 m landmark radius.
   - Some names are developments, for example "Country Garden Danga Bay".

   To change a name, edit `name_overrides` in `pipeline/explorer/jb.json` and rebuild.
3. **Facts.** Each one is shown only with a registered source:

   | Stop | Fact | Source |
   |---|---|---|
   | 1 | The RTS Link is a 4 km rail shuttle to Woodlands North. Over the middle of the strait its viaduct stands 25 m above the water. | SRC-053, LTA release, 24 Mar 2023 |
   | 3 | Tourism Johor lists the Sultan Abu Bakar Mosque as the earliest mosque in Johor Bahru, built in 1892. | SRC-054, Tourism Johor |
   | 5 | Legoland Malaysia opened in September 2012 as Asia's first Legoland theme park. | SRC-055, AFP via Dawn, 15 Sep 2012 |

   - Stops 2 and 8 have no fact. JB Sentral's opening date and Ulu Tiram facts were found only on Wikipedia, which is not enough.
   - Some tour copy changed from the mockup to match the new lines. IP2 is now "about 15 km". The unsourced "Skudai Highway jam" line was dropped. Stop 1 is now "Across the strait" instead of "Five minutes to Singapore", because no source gives a journey time.
4. **The explorer itself.** Run it locally:

   ```bash
   python -m http.server -d site 8000
   ```

   Then open http://localhost:8000/, and http://localhost:8000/?debug=1 for the internal view. Try it at phone width as well.

## How to publish once approved

1. Make sure the repo's Pages setting is "Source: GitHub Actions" (it already is, per `docs/security-review.md`).
2. Merge the branch to `main` (or run from the branch).
3. Go to Actions → **explorer-pages** → **Run workflow**.

The workflow runs the JS tests, then deploys `site/`.

## Deferred (not in this release)

- Hand-set heights for named towers and malls. OSM has few heights in JB, so most buildings use a small default.
- Detailed Three.js models for 2–3 hero stations. Every station now uses the same generic box and roof.
- Mutiara Line and MRT3 Circle Line plans (spec §6).
- A console warning from the OpenFreeMap style ("Expected value to be of type number, but found null"). It comes from the base style, not our layers.

## Checks run

- `pytest pipeline/explorer/tests`: 27 passed. This includes the full JB build from the committed OSM clip.
- `node --test site/tests/`: 15 passed.
- Checked by hand in headless Chrome:
  - the default view and `?debug=1`;
  - 3D at Bukit Chagar;
  - tile server blocked;
  - photos blocked, which falls back to the snapshot;
  - 10 rapid Next clicks, after which the card and the camera are on the same stop;
  - arrow keys;
  - reduced motion;
  - 390 px mobile.

  A check on a real phone was not done.
- Security re-scan: `docs/security-review.md`, "Re-scan before the explorer handoff". No credentials found.

## Rebuild the data

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r pipeline/requirements-explorer.txt
.venv/Scripts/python pipeline/explorer/build_line.py --config pipeline/explorer/jb.json --out site/data/jb --report results/explorer
.venv/Scripts/python pipeline/explorer/photos.py --titles pipeline/explorer/jb_photos.json --out site/photos/jb --json site/data/jb/photos.json
```
