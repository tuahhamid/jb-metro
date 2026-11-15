# JB Metro Explorer: design

**Date:** 2026-11-14
**Status:** draft for owner review
**Decided with the owner in the 2026-11-14 brainstorming session.** Calls Claude made without an explicit owner answer are marked *(Claude's call)*.

## 1. Intent

The owner wants an interactive, story-led explorer of proposed Malaysian rail lines, in the
style of the Sydney Metro West site (caportal.com.au/tfnsw/sydmetrowest). Visitors travel a
line on a live map, stop at stations and landmarks, and see the line and its stations in 3D
over the real city.

The aim is to bridge planning and the public with web tech: storytelling through an
interactive map and 3D models. Speed to a working 3D explorer matters more than engineering
certainty. *(Claude's reading of "bridging tech"; the owner did not correct it.)*

### What changed from the governing brief

The brief (`docs/project-brief.md`) set up an evidence-first study with 3D only at the end
(Stage 6) and only for Bukit Chagar. On 2026-11-14 the owner changed direction:

| Brief said | Now |
|---|---|
| Stages 3–5 (access model, Bukit Chagar stress test, validation) before any prototype | **Paused** (owner picked "pause", not "drop"). The Stage 3 scope stays in `docs/handoffs/stage-2.md` for a possible return. |
| 3D only for Bukit Chagar, only where it explains a finding | 3D across the whole line, as the main experience |
| No other corridors | Three Malaysian lines: **JB E-ART** first, then **Mutiara Line** (Penang LRT, https://laluanmutiara.mymrt.com.my/) and **MRT3 Circle Line** (Klang Valley, https://www.mymrt.com.my/ms/awam/mrt3-laluan-lingkaran/) |
| Engineering certainty drives the work | The story drives it. Certainty is shown by a small status badge only. |

The brief text is not edited. This change is recorded in `docs/handoffs/2026-11-14-scope-change.md`.

## 2. Goals, non-goals, anti-goals

**Goals**
1. A working JB explorer with the Sydney Metro West flow: Intro → Guided tour → Places (3D).
2. Lines that look like railways: smooth curves and straight platforms, not car paths.
3. Real landmarks with photos and short "Did you know?" facts.
4. The same pattern reused for Mutiara and MRT3 afterwards.

**Non-goals**
- Ridership forecasts, access modeling, capacity or validation tests (paused).
- Photoreal renders.
- Engineering-grade alignments, vertical profiles or structural design.

**Anti-goals (a failure even if it works)**
- A viewer mistakes our JB concept line for the government's plan. Every concept line keeps a visible `concept` badge and the "Map is indicative only" footer.
- Copying Sydney Metro's brand: no logos, colors, wording or imagery. We copy the *flow* only.
- Presenting an unverified fact as true.
- Leaking keys or personal data in the public repo.

## 3. Constraints (unchanged from the brief unless noted)

- $0 software cost. Web-only. Public repo, so no API keys anywhere.
- Map: **MapLibre GL JS** with key-less **OpenFreeMap** vector tiles (`https://tiles.openfreemap.org/styles/positron`). This was proven in the mockup.
- Hosting: **GitHub Pages, deployed by a GitHub Actions workflow** (repo setting already "Source = GitHub Actions", `docs/security-review.md`). The site is public once deployed. See §5.9 for when that happens.
- Design: **Buruh Hybrid** (tokens snapshot in `docs/design/`): square corners, Archivo and IBM Plex Mono, navy and safety orange, `orange` never as text on paper.
- Line geometry for the official lines (Mutiara, MRT3) comes from OSM or official open data, never traced from official maps or James Clark's map (brief source rule). *(Claude's call)*
- Status labels stay: each line and station shows `concept` or `official` (and `existing` / `under construction` for context lines such as the RTS Link and KTM).

## 4. Approaches considered

### 4.1 Explorer layout
| Option | Trade-off | Picked |
|---|---|---|
| **Map-first, Sydney flow**: Intro → tour cards over a live map → 3D precinct | Closest to the reference; best for exploring | **Yes** (owner: "copy flow") |
| Station-first: a large 3D station with a mini-map | Strong 3D feel, weak sense of the line | No |
| Scroll story: chapters with the map pinned | Best narrative, weak for free exploring | No |

### 4.2 3D method
| Option | Trade-off | Picked |
|---|---|---|
| **Map extrusions**: OSM/OpenFreeMap buildings extruded on the map, with our viaduct and stations as colored extrusions | Fast, real city context, matches the reference's "Places" screen | **Yes**, for the first release |
| Hand-built Three.js station models | Rich detail, slow to make per station | Later, for 2–3 hero stations only *(Claude's call)* |

### 4.3 Making lines track-like
| Option | Trade-off | Picked |
|---|---|---|
| **Post-process the road route into tangents and arcs** | Fast, repeatable, fixes all lines at once; can cross buildings (flagged) | **Yes** (owner approved) |
| Re-route with turning limits built in | More "correct", large rewrite | No |
| Hand-placed control points | Most control, manual and slow | No |

### 4.4 Photos
| Option | Trade-off | Picked |
|---|---|---|
| **Wikimedia Commons**, with credit | Free, real photos, licenses allow reuse with credit | **Yes** |
| Owner's photos | Owner has none | No |
| **Our own 3D snapshots** | Always available, less vivid | **Fallback** where Commons has nothing good |

## 5. The design

### 5.1 Screens (JB first)
Proven in mockup `map-v6-photos.html` (see §8).

**One site for all three lines** *(Claude's call)*. A line switcher sits in the header. The data format (lines, stations, landmarks, tour steps, photos, facts) is the same for every line, so Mutiara and MRT3 are added as data, not as new pages. Only JB is filled in for the first release, and the switcher shows the other two as "coming soon" or is hidden until they exist.

1. **Intro:** a full-screen map with a slow orbit, a headline, "Start the tour", and "Skip intro". No renders.
2. **Tour:** a left card with a photo, status badge, stop number, title, text, an optional "Did you know?" box, Prev/Next and "Open in 3D". Each step flies the camera (center, zoom, bearing, pitch). The JB draft has 8 stops: Woodlands/RTS → Bukit Chagar interchange → old town → Danga Bay → Bukit Indah → Tebrau spine → AEON/IKEA/Toppen → Ulu Tiram.
3. **Places (3D):** pitched 3D city. A location dropdown lists Bukit Chagar plus every station. The screen also has a map key, Reset, and a card with Prev/Next through stations.
4. **On the map at all times:**
   - lines, colored per line;
   - square station markers (click for name and status);
   - landmark markers (◆; ▣ means it has a photo, and a click opens the photo with its credit);
   - context rail (RTS Link navy, KTM gray dashed).

### 5.2 3D content
- **City:** OpenFreeMap `building` layer as `fill-extrusion` using `render_height` / `render_min_height`. Most JB buildings have no height in OSM, so the tiles fall back to a small default. Hand-set heights for named towers and malls are left to the builder (§7).
- **Viaduct:** the track buffered to 9 m wide, deck at 11–13.5 m.
- **Station:** a 100 m × 24 m box at 9–21 m, aligned to the track, with a 112 m × 30 m colored roof slab at 21–22.5 m. The same generic design is used at every station. Hero stations get their own model later.
- **RTS Link viaduct:** from OSM `railway=construction` near the checkpoint, at 14–17 m.
- **Colors:**
  - Tebrau: orange `#FF6A13`.
  - Iskandar Puteri: teal `#2E8C83`.
  - RTS: navy `#13213A`.
  - KTM: `#8C8577`.
  - Mutiara and MRT3: proposed `#E8C547` and `#8F7CF0`.

  Line colors extend Buruh Hybrid, which has none. **The owner must approve the extension** (`docs/design/README.md` requires it).

### 5.3 Track rules (owner-approved)
- **Curves:** minimum radius **150 m**. 100 m is allowed only where 150 m cannot fit, and is flagged. Anything tighter is a violation and must be reported.
- **Station:** a **100 m platform plus 30 m straight each side = 160 m straight**, with no curve inside.
- **Station centers stay put.** The line bends to reach them, and platforms may rotate about their center.
- **Method** (proven in the spike `track2.py`, §8):
  1. Resample the road route at 10 m.
  2. Remove loops and ramps: shortcut where the path length is over 1.6× the straight distance within 800 m.
  3. Build intersection points (PIs): two per station on the platform axis, plus simplified road vertices (35 m tolerance) more than 200 m from any station.
  4. Fit 150 m arcs. Where tangents overlap, merge or drop the free PIs. Push station PIs outward so arcs never enter the 80 m clear zone. If two stations conflict, rotate both platforms toward each other.
  5. Report per line:
     - number of curves at each radius;
     - station error;
     - length before and after;
     - maximum offset from the road route;
     - **buildings crossed** by the new track.

     The crossings are **internal only** (owner decision, 2026-11-14). They go in the pipeline report and in a hidden debug view (for example `?debug=1`), never in the public interface. Public red dots on real buildings could read as a demolition list. The same goes for the "old road route" comparison toggle used in the mockup.
- **Spike result:**
  - T1: 19.0 km, 58 curves, all at 150 m, 15 buildings crossed.
  - IP2: 15.3 km, 38 curves, all at 150 m, 19 buildings crossed.
  - All station centers lie on the track.

### 5.4 JB line changes (owner-approved for the explorer)
- **Tebrau (T1), extended to Ulu Tiram:**
  - Keep Stage 2 stations 1–13 (Bukit Chagar → AEON Mall Tebrau City). Drop 14–15 (the Desa Tebrau detour).
  - Continue on Federal Route 3 (Jalan Kota Tinggi) 7.2 km to Ulu Tiram town (OSM `place=town`, 103.82088 E 1.59936 N).
  - Six new stations about 1.2 km apart. In the spike they were named Desa Jaya, Taman Gaya, "Jalan Kota Tinggi km 3.6", "km 4.8", Taman Kasih, and Ulu Tiram.
- **Iskandar Puteri (IP2):**
  - Drop Stage 2 stations 2–3 (SKS Tower, Olympia College). The road route went north-east with T1 and doubled back, which no track can follow, and T1 already serves Olympia College.
  - IP2 now runs west from Bukit Chagar to Kampung Mahmoddiah, then as before to Bukit Indah, with 15 stations. *(Claude's call during the spike, reported to the owner, not objected to.)*
- These are **explorer** geometries, labeled `concept`. The Stage 2 record (`data/concept/`, `results/stage2/`) is not overwritten. The new geometry goes in a separate explorer data folder.
- The other Stage 2 options (T2, T3, IP1, IP3, IP4) are not shown in the explorer. *(Claude's call)*

### 5.5 Station names
Stage 2 labels are "nearest named OSM thing". That gives duplicates (T1 stations 6 and 7 are both "Kampung Stulang Baru") and blanks (T1 10–11).

Rule: a unique, human name per line, chosen in this order:
1. a named landmark within 300 m;
2. an OSM place (`neighbourhood`/`suburb`/`quarter`) within 700 m, used once only;
3. the road name.

Names are reviewed by hand, and the owner sees the final list. *(Claude's call)*

### 5.6 Photos
- **Source:** Wikimedia Commons only.
- **Licenses:** CC0, CC BY, CC BY-SA or public domain.
- **Size:** at least 800 px wide.
- **Check:** every pick is looked at by a person before use.
- **Storage:** photos are downloaded into the repo at about 960 px, with a credits file recording title, page URL, author, license and license URL. Each card and pop-up shows "Photo: author · license · Wikimedia Commons" linked to the file page.
- **Spike picks (21 checked; 17 good):**
  - Good: RTS Link bridge 2025 (CC0), JB Sentral concourse, CIQ/BSI, Dataran Bandaraya clock tower, Legoland, AEON Bukit Indah, KSL City, Plaza Pelangi, IKEA Tebrau, Ulu Tiram, Komtar JBCC, Mid Valley Southkey, Larkin terminal, Paradigm Mall, Puteri Harbour, Masjid Sultan Iskandar, Causeway at night.
  - Weak (re-search or use the 3D fallback): Sultan Abu Bakar Mosque, Danga Bay, City Square, AEON Tebrau.
- **Fallback:** a captured frame of our 3D map at that place.

### 5.7 Facts
- Every "Did you know?" fact needs a source entered in `docs/sources/source-register.csv` before it ships.
- Facts with no source are removed, not softened.
- The three draft facts in the mockup (RTS crossing length, Sultan Abu Bakar Mosque dates, Legoland 2012) are placeholders until checked.

### 5.8 Housekeeping from the scope change
- **Bus-position collector:** turn off the `vp-collector` schedule (keep `workflow_dispatch`). It only fed the paused validation work. Stage 2 handoff decision 5 is closed by this.
- **README:** update the status table to show the pause and the explorer.
- **Security:** re-run the scan in `docs/security-review.md` before the handoff (CLAUDE.md).

### 5.9 Release and owner review (owner decision, 2026-11-14)
- Build the JB explorer with the proposed values: the line colors in §5.2, the station names from §5.5, and facts with sources.
- **The Pages deploy stays off** until the owner approves. The workflow may exist, but it must not publish (for example, manual dispatch only, or no deploy job yet).
- **One review at the end.** The owner reviews the working explorer, the color extension, the final station-name list and every fact in one pass. Only then is the site published.
- Until then, the owner previews it locally or as a private Claude artifact.

## 6. Order of work
1. **JB explorer**, built properly from this design (§5).
2. **Mutiara Line**, the same pattern:
   - fetch the alignment and stations from OSM (under-construction tags) or official open data, labeled `official`;
   - a GitHub Actions fetch if session network rules block the sources.
3. **MRT3 Circle Line**, the same pattern. Parts are underground, so the 3D needs a below-ground treatment (for example a translucent tunnel or a cut-away view). This is designed when we get there.

*(Order: owner chose JB first. Mutiara before MRT3 is Claude's call: Mutiara is smaller and further along.)*

## 7. Left to the builder
- Code structure (single page vs. small modules), the build tooling (none needed), and the folder layout for the explorer and its data.
- Where the track-smoothing step lives (a pipeline script that writes explorer GeoJSON is expected) and its tests.
- Hand-set building heights for named towers and malls near stations, and the source for each.
- Exact tour copy, camera angles and transition timing.
- Mobile layout: cards become bottom sheets under 700 px, as in the mockup.
- Accessibility: keyboard Prev/Next, focus rings from Buruh Hybrid tokens, alt text for photos, reduced motion (no orbit and no fly animation when `prefers-reduced-motion` is set).
- Page weight: inline GeoJSON is about 150 KB in the mockup. Keep it in separate files if it grows.

## 8. Reference material (spike, throwaway)
Copied to `docs/superpowers/specs/2026-11-14-explorer-spike/` for the builder to read, not to ship:
- `track2.py`: the tangent-and-arc smoothing.
- `extend_t1.py`: the Ulu Tiram extension and station placement.
- `commons.py`: the photo search.
- `make_mock_data.py`: the line, station and RTS extraction.
- `map-v6-photos.html`: the last mockup page (MapLibre + OpenFreeMap; data inlined).
