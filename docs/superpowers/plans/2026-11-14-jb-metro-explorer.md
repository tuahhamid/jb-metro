# JB Metro Explorer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A public-ready (but not yet published) JB Metro Explorer: a Sydney-Metro-West-style intro → guided tour → 3D places site for the two concept JB E-ART lines, built on track-like geometry, real landmarks, credited photos and sourced facts.

**Architecture:** A Python pipeline (`pipeline/explorer/`) turns Stage 2 concept routes into track geometry (150 m arcs, 160 m station straights). It extends Tebrau to Ulu Tiram, names stations, and writes GeoJSON and JSON into `site/data/jb/`. A static, build-free site (`site/`) uses MapLibre GL JS 4.7.1 on key-less OpenFreeMap tiles to render it. Pure-logic JS modules are tested with `node --test`. DOM and map glue is checked by hand in a browser. A dispatch-only Pages workflow exists but nothing is published until the owner approves.

**Tech Stack:** Python 3.12+ (numpy, shapely, pyproj, networkx, osmium, pytest), MapLibre GL JS 4.7.1 (unpkg), OpenFreeMap positron style, vanilla ES modules, Node 26 test runner, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-11-14-jb-metro-explorer-design.md` (read it first; §-references below point into it). Reference spike code: `docs/superpowers/specs/2026-11-14-explorer-spike/` (`track2.py`, `extend_t1.py`, `commons.py`, `make_mock_data.py`, `map-v6-photos.html`). Port its algorithms. Do not copy its hard-coded paths.

**Scope:** JB only (spec §6 step 1). Mutiara and MRT3 get their own plans later. The data format here must already be line-agnostic (spec §5.1).

## Global Constraints

- $0, web-only, public repo: no API keys, tokens or `.env` anywhere, including client code.
- Map: MapLibre GL JS `4.7.1` from `https://unpkg.com/maplibre-gl@4.7.1/dist/`. Style: `https://tiles.openfreemap.org/styles/positron`.
- Design: Buruh Hybrid tokens (`docs/design/buruh-hybrid-tokens.snapshot-2026-11-04.json`). Square corners. Archivo plus IBM Plex Mono from Google Fonts. `orange` `#FF6A13` is never used as text on paper; orange text uses `accent-text` `#B23F06`. Light theme for this release.
- Line colors (proposed extension, owner reviews at the end): Tebrau `#FF6A13`, Iskandar Puteri `#2E8C83`, RTS `#13213A`, KTM `#8C8577`, Mutiara `#E8C547`, MRT3 `#8F7CF0`.
- Track rules: min radius `150` m; `100` m only where 150 cannot fit (flagged); below 100 = violation reported; station straight = `100` m platform + `30` m each side = `80` m clear each side of center; station centers never move.
- Massing (m): viaduct width `9`, base `11`, top `13.5`; station box `100 × 24`, base `9`, top `21`; roof slab `112 × 30`, base `21`, top `22.5`; RTS viaduct base `14`, top `17`.
- Every line and station carries `status`: `concept` (E-ART), `under construction` (RTS Link), `existing` (KTM). Footer text always shows: "Map is indicative only · E-ART lines are concepts, not official · © OpenStreetMap · OpenFreeMap".
- Copy Sydney Metro West's flow only: no logos, colors, wording or imagery from it.
- "Buildings crossed" and the road-route comparison appear **only** with `?debug=1`. They are never in the default UI.
- Photos: Wikimedia Commons only. Licenses must match `^(CC0|CC BY( |-SA )[0-9.]+|Public domain)$` (case-insensitive). Every photo shows "Photo: {author} · {license} · Wikimedia Commons" linked to its file page.
- Facts: each needs a `source_id` present in `docs/sources/source-register.csv`. A fact without a source is removed.
- Stage 2 outputs (`data/concept/`, `results/stage2/`) are read-only.
- Pages deploy must not run automatically: `workflow_dispatch` only.
- Commits are authored as the owner (CLAUDE.md `git config` lines) and end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Work on branch `claude/explorer-design`.
- External HTTP requests (Commons) use User-Agent `jb-metro-explorer/1.0 (open-source research prototype)`. No personal details.

## Review Focus

1. **Tiles fail to load** (OpenFreeMap down or offline). Lines, stations, cards and the tour must still work, and a notice says the base map is unavailable. → Task 7 test `tileNotice`.
2. **`prefers-reduced-motion: reduce`.** No orbit, and camera moves jump instead of fly. → Task 8 test `cameraMove reduced`.
3. **A photo is missing or fails to load.** The card falls back to a 3D snapshot with no broken credit line. → Task 8 test `cardPhoto fallback`.
4. **Rapid Next/Prev clicks during a camera flight.** The card and camera end on the same step. → Task 8 test `tour rapid steps`.
5. **Narrow screens (<700 px).** Cards become bottom sheets and never cover the map's navigation control. → Task 7 manual check, with the CSS rule pinned in Task 7 step 5.

---

### Task 1: Housekeeping for the scope change

**Files:**
- Modify: `.github/workflows/vp-collector.yml` (remove the `schedule:` block; keep `workflow_dispatch`; update the header comment to say the schedule was turned off 2026-11-14 because Stages 3–5 are paused)
- Modify: `README.md` (Status table: Stages 3–5 "Paused 2026-11-14, see `docs/handoffs/2026-11-14-scope-change.md`"; add a row "Explorer: in progress, see design spec"; keep everything else)
- Create: `pipeline/requirements-explorer.txt`

- [ ] **Step 1: Write `pipeline/requirements-explorer.txt`**

```
numpy==2.5.4
shapely==2.2.0
pyproj==3.8.0
networkx==3.7
osmium==4.3.2
pytest==8.4.2
```

- [ ] **Step 2: Verify the install**

Run: `python -m venv .venv && .venv/Scripts/python -m pip install -r pipeline/requirements-explorer.txt && .venv/Scripts/python -c "import osmium, shapely, pytest; print('ok')"`
Expected: `ok` (`.venv/` is already in `.gitignore`)

- [ ] **Step 3: Verify the collector no longer has a schedule**

Run: `grep -c "schedule:" .github/workflows/vp-collector.yml`
Expected: `0`

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/vp-collector.yml README.md pipeline/requirements-explorer.txt
git commit -m "Explorer: pause collector schedule, README status, explorer requirements"
```

---

### Task 2: Track geometry core (`track.py`)

**Files:**
- Create: `pipeline/explorer/track.py`
- Create: `pipeline/explorer/tests/conftest.py` (prepends `pipeline/explorer` and `pipeline/stage2` to `sys.path`)
- Test: `pipeline/explorer/tests/test_track.py`

**Interfaces:**
- Produces:
  - `TrackRules` dataclass: `r_min=150.0, r_fallback=100.0, clear_half=80.0, resample_m=10.0, loop_look_m=800.0, loop_ratio=1.6, loop_min_m=60.0, simplify_tol_m=35.0, free_pi_keepout_m=200.0`
  - `StationIn` dataclass: `key: str, x: float, y: float`
  - `TrackResult` dataclass: `xy: np.ndarray` (N×2, metres, EPSG:32648); `stations: dict[str, tuple[float, float, float, float]]` (key → x, y, ux, uy, the platform axis); `radii: list[float]` (one per arc); `flags: list[dict]`
  - `resample(xy: np.ndarray, step: float) -> np.ndarray`
  - `remove_loops(xy: np.ndarray, look_m: float, ratio: float, min_len_m: float) -> np.ndarray`
  - `build_track(road_xy: np.ndarray, stations: list[StationIn], rules: TrackRules = TrackRules()) -> TrackResult`. Stations are ordered by chainage along `road_xy`. The first and last are termini, and the track runs straight 80 m past each terminus center.
  - `track_report(result: TrackResult, road_xy: np.ndarray, buildings: list[tuple]) -> dict`. `buildings` uses the Stage 2 `Layers.buildings` shape `(polygon, levels, osm_id)`. Keys: `curves, curves_r150, curves_r100, curves_below_r100, flags, max_station_error_m, length_km_before, length_km_after, max_offset_from_road_m, buildings_crossed` (list of osm ids).

Test helpers (`min_radius`, `straightness_dev`, `dist_to_line`, `path_length`) live in `conftest.py` and use 3-point circle radii and point-to-segment distances.

Algorithm: port `build()` from spike `track2.py` (PI method: station PIs on the platform axis, free PIs from the simplified road, arc fitting, merge/drop free PIs, push station PIs outward, then fallback radius, then rotate both platforms toward each other, at most 12 tries per pair). Every arc is sampled at ≤5 m.

- [ ] **Step 1: Write the failing tests**

```python
def test_straight_road_gives_no_curves():
    road = np.array([[0, 0], [5000, 0]], float)
    r = build_track(road, [StationIn("a", 0, 0), StationIn("b", 2500, 0), StationIn("c", 5000, 0)])
    assert r.radii == [] and r.flags == []

def test_right_angle_becomes_one_r150_arc():
    road = np.array([[0, 0], [2000, 0], [2000, 2000]], float)
    r = build_track(road, [StationIn("a", 0, 0), StationIn("b", 2000, 2000)])
    assert r.radii == [150.0]
    # every point is >= 150 m from the inside corner region: max 3-point curvature radius check
    assert min_radius(r.xy, chord=30) >= 149.0          # helper in the test file

def test_station_has_80m_clear_straight_each_side():
    road = np.array([[0, 0], [1500, 0], [1500, 1500], [3000, 1500]], float)
    st = [StationIn("a", 0, 0), StationIn("m", 1500, 750), StationIn("z", 3000, 1500)]
    r = build_track(road, st)
    assert straightness_dev(r.xy, (1500, 750), half=80) < 0.5   # metres
    assert dist_to_line(r.xy, (1500, 750)) < 0.5

def test_cloverleaf_loop_is_removed():
    t = np.linspace(0, 2 * np.pi, 60)
    loop = np.c_[1000 + 60 * np.sin(t), 60 - 60 * np.cos(t)]      # 377 m loop at x=1000
    road = np.vstack([[[0, 0]], loop, [[2000, 0]]])
    out = remove_loops(resample(road, 10), 800, 1.6, 60)
    assert path_length(out) < 2050

def test_close_stations_on_reversal_rotate_and_do_not_hang():
    # IP2-like: path goes NE then back W past the start
    road = np.array([[0, 0], [-150, 180], [-130, 310], [25, 507], [76, 763], [-1185, 415]], float)
    r = build_track(road, [StationIn("s1", 0, 0), StationIn("s4", -1185, 415)])
    assert all(rad >= 100.0 for rad in r.radii)

def test_report_counts_buildings_crossed():
    road = np.array([[0, 0], [1000, 0]], float)
    r = build_track(road, [StationIn("a", 0, 0), StationIn("b", 1000, 0)])
    rep = track_report(r, road, [(box(400, -5, 420, 5), None, 77), (box(400, 50, 420, 60), None, 78)])
    assert rep["buildings_crossed"] == [77] and rep["curves_below_r100"] == 0
```

- [ ] **Step 2: Run them and see them fail**

Run: `.venv/Scripts/python -m pytest pipeline/explorer/tests/test_track.py -v`
Expected: FAIL (`ModuleNotFoundError: track`)

- [ ] **Step 3: Implement `track.py` per the Interfaces block**

- [ ] **Step 4: Run them and see them pass**

Run: `.venv/Scripts/python -m pytest pipeline/explorer/tests/test_track.py -v`
Expected: 6 passed, in under 30 s

- [ ] **Step 5: Commit**

```bash
git add pipeline/explorer/track.py pipeline/explorer/tests/
git commit -m "Explorer: tangent-and-arc track geometry with station straights"
```

---

### Task 3: Route extension, bypass and new stations (`extend.py`)

**Files:**
- Create: `pipeline/explorer/extend.py`
- Test: `pipeline/explorer/tests/test_extend.py`

**Interfaces:**
- Consumes: Stage 2 `Layers` (`node_xy`, `ways` with `tags["highway"]`) from `pipeline/stage2/osm_layers.py`.
- Produces:
  - `EXT_WEIGHTS = {"trunk": 0.4, "primary": 0.5, "secondary": 1.0, "tertiary": 1.3, "motorway": 3.0, "trunk_link": 2.0, "primary_link": 2.0}`
  - `route_on_roads(L, start_xy: tuple, end_xy: tuple, weights: dict = EXT_WEIGHTS) -> np.ndarray`. This is the shortest path on edges weighted length × class weight. Classes not in `weights` are excluded.
  - `splice(road_xy: np.ndarray, cut_xy: tuple, extension_xy: np.ndarray) -> np.ndarray`. It keeps `road_xy` up to the projection of `cut_xy`, then appends `extension_xy`.
  - `bypass(road_xy: np.ndarray, from_xy: tuple, to_xy: tuple) -> np.ndarray`. It replaces the stretch between the two projections with a straight segment.
  - `even_stations(line_xy: np.ndarray, from_xy: tuple, to_xy: tuple, target_m: float = 1200, band: tuple = (1000, 1500)) -> list[tuple]`. It returns new station points after `from_xy`, and the last one is exactly `to_xy`. `n = round(L / target_m)`, adjusted so `L / n` falls inside `band`.

- [ ] **Step 1: Write the failing tests**

```python
def test_even_stations_7220m_gives_6_in_band():
    line = np.array([[0, 0], [7220, 0]], float)
    pts = even_stations(line, (0, 0), (7220, 0))
    assert len(pts) == 6 and pts[-1] == (7220.0, 0.0)
    gaps = np.diff([0] + [p[0] for p in pts])
    assert all(1000 <= g <= 1500 for g in gaps)

def test_splice_keeps_head_and_appends():
    out = splice(np.array([[0, 0], [100, 0], [200, 0]], float), (100, 0), np.array([[100, 0], [100, 50]], float))
    assert out[0].tolist() == [0, 0] and out[-1].tolist() == [100, 50] and np.max(out[:, 0]) <= 100

def test_bypass_cuts_detour():
    road = np.array([[0, 0], [0, 500], [300, 500], [300, 0], [1000, 0]], float)
    out = bypass(road, (0, 0), (300, 0))
    assert path_length(out) == pytest.approx(1000, abs=1)

def test_route_prefers_trunk():
    # tiny synthetic Layers: a trunk detour (len 1400) vs a tertiary direct (len 1000)
    L = fake_layers(...)            # helper builds node_xy/ways
    xy = route_on_roads(L, (0, 0), (1000, 0))
    assert path_length(xy) == pytest.approx(1400, abs=1)   # 1400*0.4 < 1000*1.3
```

- [ ] **Step 2: Run them and see them fail**

Run: `.venv/Scripts/python -m pytest pipeline/explorer/tests/test_extend.py -v`
Expected: FAIL (`ModuleNotFoundError: extend`)

- [ ] **Step 3: Implement `extend.py` per the Interfaces block** (port from spike `extend_t1.py`)

- [ ] **Step 4: Run them and see them pass**

Run: `.venv/Scripts/python -m pytest pipeline/explorer/tests/test_extend.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add pipeline/explorer/extend.py pipeline/explorer/tests/test_extend.py
git commit -m "Explorer: road extension, detour bypass, even station placement"
```

---

### Task 4: Station naming (`names.py`)

**Files:**
- Create: `pipeline/explorer/names.py`
- Test: `pipeline/explorer/tests/test_names.py`

**Interfaces:**
- Produces: `name_stations(stations: list[dict], landmarks: list[tuple[str, float, float]], places: list[tuple[str, float, float]], roads: list[tuple[str, LineString]], line_xy: np.ndarray, overrides: dict[str, str]) -> dict[str, str]`
  - `stations`: dicts with `key, x, y`. Returns key → name.
  - Order of precedence (spec §5.5):
    1. `overrides[key]`;
    2. the nearest landmark within `300` m that is not yet used on this line;
    3. the nearest place within `700` m that is not yet used;
    4. `"{nearest road name} km {chainage_km:.1f}"`, with chainage along `line_xy`.
  - Names are unique per line.

- [ ] **Step 1: Write the failing tests**

```python
def test_two_stations_near_one_place_get_different_names():
    st = [dict(key="T1-06", x=0, y=0), dict(key="T1-07", x=1000, y=0)]
    places = [("Kampung Stulang Baru", 500, 0), ("Taman Sri Amar", 1400, 0)]
    n = name_stations(st, [], places, [], line, {})
    assert n["T1-06"] == "Kampung Stulang Baru" and n["T1-07"] == "Taman Sri Amar"

def test_landmark_beats_place():
    n = name_stations([dict(key="k", x=0, y=0)], [("KSL City", 100, 0)], [("Taman X", 50, 0)], [], line, {})
    assert n["k"] == "KSL City"

def test_road_fallback_uses_km():
    n = name_stations([dict(key="k", x=3600, y=0)], [], [], [("Jalan Kota Tinggi", LineString([(0, 5), (9000, 5)]))], line_0_to_9000, {})
    assert n["k"] == "Jalan Kota Tinggi km 3.6"

def test_override_wins():
    n = name_stations([dict(key="k", x=0, y=0)], [("A", 0, 0)], [], [], line, {"k": "Bukit Chagar"})
    assert n["k"] == "Bukit Chagar"
```

- [ ] **Step 2: Run and see them fail**

Run: `.venv/Scripts/python -m pytest pipeline/explorer/tests/test_names.py -v`
Expected: FAIL

- [ ] **Step 3: Implement `name_stations` per the Interfaces block** (greedy in station order)

- [ ] **Step 4: Run and see them pass**

Run: `.venv/Scripts/python -m pytest pipeline/explorer/tests/test_names.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add pipeline/explorer/names.py pipeline/explorer/tests/test_names.py
git commit -m "Explorer: unique station naming rule"
```

---

### Task 5: JB data build (`build_line.py` + `jb.json`)

**Files:**
- Create: `pipeline/explorer/jb.json` (line config)
- Create: `pipeline/explorer/build_line.py` (CLI)
- Create (outputs, committed): `site/data/jb/network.geojson`, `site/data/jb/massing.geojson`, `site/data/jb/debug.geojson`, `results/explorer/jb_track_report.json`, `results/explorer/jb_station_names.csv`
- Test: `pipeline/explorer/tests/test_build_jb.py`

**Interfaces:**
- Consumes: `read_osm` (stage2), `build_track`, `track_report` (Task 2), `route_on_roads`, `splice`, `bypass`, `even_stations` (Task 3), `name_stations` (Task 4).
- Produces: the JSON shapes that Tasks 7–8 read:
  - `network.geojson` features:
    - `kind ∈ {"line", "station", "context_rail", "landmark"}`
    - `line_id` (`"T1"`/`"IP2"`/`"RTS"`/`"KTM"`)
    - `name`, `status`
    - stations also carry `station_id` (`"T1-01"`), `seq` (int, 1-based after renumbering) and `ux, uy`
    - landmarks also carry `landmark_id` and `photo` (key or null)
  - `massing.geojson` features: `kind ∈ {"viaduct", "station", "roof", "rts_viaduct"}`, `line_id`, `base`, `top` (Global Constraints values)
  - `debug.geojson` features: `kind ∈ {"road_route", "crossing"}`, `line_id`

`jb.json` content (exact):

```json
{
  "line_set": "jb",
  "osm": "data/raw/osm/jb-study.osm.pbf",
  "lines": [
    {"id": "T1", "name": "Tebrau", "status": "concept", "stage2_option": "T1",
     "keep_seq": [1,2,3,4,5,6,7,8,9,10,11,12,13],
     "extend_to": {"name": "Ulu Tiram", "lon": 103.82088, "lat": 1.59936}},
    {"id": "IP2", "name": "Iskandar Puteri", "status": "concept", "stage2_option": "IP2",
     "drop_seq": [2,3], "bypass": {"from_seq": 1, "to_seq": 4}}
  ],
  "shared_first_station": "Bukit Chagar",
  "landmarks": "pipeline/explorer/jb_landmarks.json",
  "name_overrides": {"T1-01": "Bukit Chagar", "IP2-01": "Bukit Chagar"}
}
```

- `pipeline/explorer/jb_landmarks.json`: the 21 landmarks in the spike page `map-v6-photos.html` (`LM` array, Ulu Tiram included). Each has `{id, name, lon, lat, photo}`. `photo` follows the spike's `LPH` mapping (Task 6 keys), and every landmark not in `LPH` gets null.
- Context rail: OSM `railway=construction` near the checkpoint (bbox 103.755–103.790 E, 1.440–1.475 N) is `RTS`, `under construction`. `railway=rail` is `KTM`, `existing`.

CLI: `python pipeline/explorer/build_line.py --config pipeline/explorer/jb.json --out site/data/jb --report results/explorer`

- [ ] **Step 1: Write the failing integration test** (it uses the committed OSM clip and takes under 3 minutes)

```python
def test_jb_build(tmp_path):
    run_cli(["--config", "pipeline/explorer/jb.json", "--out", tmp_path / "site", "--report", tmp_path / "rep"])
    rep = json.loads((tmp_path / "rep/jb_track_report.json").read_text())
    for lid in ("T1", "IP2"):
        assert rep[lid]["curves_below_r100"] == 0
        assert rep[lid]["max_station_error_m"] < 1.0
    net = json.loads((tmp_path / "site/network.geojson").read_text())
    st = lambda lid: [f["properties"] for f in net["features"] if f["properties"]["kind"] == "station" and f["properties"]["line_id"] == lid]
    assert len(st("T1")) == 19 and len(st("IP2")) == 15
    assert max(st("T1"), key=lambda p: p["seq"])["name"] == "Ulu Tiram"
    for lid in ("T1", "IP2"):
        names = [p["name"] for p in st(lid)]
        assert len(names) == len(set(names)) and all(names)
    assert {f["properties"]["status"] for f in net["features"] if f["properties"]["kind"] in ("line", "station") and f["properties"]["line_id"] in ("T1", "IP2")} == {"concept"}
    assert not any(f["properties"]["kind"] in ("road_route", "crossing") for f in net["features"])
```

- [ ] **Step 2: Run it and see it fail**

Run: `.venv/Scripts/python -m pytest pipeline/explorer/tests/test_build_jb.py -v`
Expected: FAIL

- [ ] **Step 3: Implement `build_line.py`**

Order of operations:
1. Read the OSM clip and the Stage 2 geojsons.
2. Per line, apply `keep_seq`/`drop_seq`, then `bypass` and `extend_to`, then `even_stations`.
3. Run `build_track`.
4. Run `name_stations`.
5. Build the massing polygons.
6. Write the outputs and the report.

The CSV columns are `station_id,line_id,seq,name,rule_used,lon,lat`.

- [ ] **Step 4: Run it and see it pass, then build the real outputs**

Run: `.venv/Scripts/python -m pytest pipeline/explorer/tests -v && .venv/Scripts/python pipeline/explorer/build_line.py --config pipeline/explorer/jb.json --out site/data/jb --report results/explorer`
Expected: all tests pass. The report shows T1 ≈19.0 km and IP2 ≈15.3 km, with `curves_below_r100 == 0`.

- [ ] **Step 5: Read `results/explorer/jb_station_names.csv` by eye.** Any name that is wrong on its face (for example a petrol station or a shop) gets an entry in `name_overrides` in `jb.json`, chosen by the same rule. Rebuild.

- [ ] **Step 6: Commit**

```bash
git add pipeline/explorer/build_line.py pipeline/explorer/jb.json pipeline/explorer/jb_landmarks.json pipeline/explorer/tests/test_build_jb.py site/data/jb results/explorer
git commit -m "Explorer: JB data build (T1 to Ulu Tiram, IP2 bypass, track, names, massing)"
```

---

### Task 6: Photos from Wikimedia Commons (`photos.py`)

**Files:**
- Create: `pipeline/explorer/photos.py`
- Create: `pipeline/explorer/jb_photos.json` (key → exact Commons title)
- Create (outputs, committed): `site/photos/jb/<key>.jpg`, `site/data/jb/photos.json`
- Modify: `data/LICENSES.md` (add a "Photos (Wikimedia Commons)" section pointing to `site/data/jb/photos.json` for per-file credits)
- Test: `pipeline/explorer/tests/test_photos.py`

**Interfaces:**
- Produces:
  - `is_free_license(short_name: str) -> bool`
  - `credit_line(meta: dict) -> str`, returning `"Photo: {author} · {license} · Wikimedia Commons"`. The author has HTML stripped and is cut to 80 characters, or is `"unknown"`.
  - `fetch(titles: dict[str, str], out_dir: Path, json_path: Path, width: int = 960) -> dict`
  - `photos.json` shape: `{key: {"src": "photos/jb/<key>.jpg", "title", "page", "author", "license", "license_url", "credit"}}`
- Rate limits: sleep 3 s between API calls, with exponential back-off on HTTP 429 (20 s × attempt, 6 attempts). Use the Global Constraints User-Agent.

`jb_photos.json` (exact; 17 picks the owner saw in the mockup):

```json
{
 "woodlands_rts": "File:Johor Bahru-Singapore RTS Link Bridge 2025.jpg",
 "jb_sentral": "File:JB Sentral Station Concourse - 22 Oct 2025.jpg",
 "bsi_ciq": "File:Malaysia Southern Custom Complex ( Bangunan Sultan Iskandar Johor Bahru).jpg",
 "dataran": "File:Johor Bahru City Square.JPG",
 "legoland": "File:Legoland Malaysia 2015 02.jpg",
 "bukit_indah": "File:Aeon Mall, Bukit Indah, Johor Bahru, Johor, Malaysia.jpg",
 "ksl": "File:KSL City.jpg",
 "plaza_pelangi": "File:Pelangi Plaza (2020).jpg",
 "ikea_tebrau": "File:IKEA Tebrau.jpg",
 "ulu_tiram": "File:Ulu Tiram.jpg",
 "komtar": "File:KOMTAR JBCC (220307).jpg",
 "southkey": "File:Mid Valley Southkey.jpg",
 "larkin": "File:Larkin bus terminal.jpg",
 "paradigm": "File:Paradigm Mall Johor Bahru.jpg",
 "puteri_harbour": "File:Puteri Harbour in Johor, Malaysia.jpg",
 "sultan_iskandar_mosque": "File:Sultan Iskandar Mosque.jpg",
 "causeway": "File:Empty Singapore-Malaysia Causeway 2.jpg"
}
```

(`dataran`: the file is named "City Square" but shows the Dataran Bandaraya clock tower. Dataran Bandaraya means "City Square". It was checked by eye.)

- [ ] **Step 1: Write the failing offline tests**

```python
@pytest.mark.parametrize("lic,ok", [("CC0", True), ("CC BY 2.0", True), ("CC BY-SA 4.0", True), ("Public domain", True),
                                    ("CC BY-NC 2.0", False), ("CC BY-ND 4.0", False), ("", False)])
def test_license_filter(lic, ok): assert is_free_license(lic) is ok

def test_credit_line_strips_html():
    assert credit_line({"author": '<a href="x">JohnLim99</a>', "license": "CC BY-SA 4.0"}) == "Photo: JohnLim99 · CC BY-SA 4.0 · Wikimedia Commons"
```

- [ ] **Step 2: Run and see them fail**

Run: `.venv/Scripts/python -m pytest pipeline/explorer/tests/test_photos.py -v`
Expected: FAIL

- [ ] **Step 3: Implement `photos.py`.** `fetch` raises if any file's license fails `is_free_license` and writes nothing for that key.

- [ ] **Step 4: Run the tests, then fetch**

Run: `.venv/Scripts/python -m pytest pipeline/explorer/tests/test_photos.py -v && .venv/Scripts/python pipeline/explorer/photos.py --titles pipeline/explorer/jb_photos.json --out site/photos/jb --json site/data/jb/photos.json`
Expected: tests pass; 17 JPEGs, each ≤ 250 KB; `photos.json` has 17 keys

- [ ] **Step 5: Commit**

```bash
git add pipeline/explorer/photos.py pipeline/explorer/jb_photos.json pipeline/explorer/tests/test_photos.py site/photos/jb site/data/jb/photos.json data/LICENSES.md
git commit -m "Explorer: credited Wikimedia Commons photos for JB landmarks"
```

---

### Task 7: Site shell, data loading, map layers

**Files:**
- Create: `site/index.html`, `site/css/explorer.css`
- Create: `site/data/lines.json`: `[{"id":"jb","name":"Johor Bahru E-ART","available":true},{"id":"mutiara","name":"Mutiara Line","available":false},{"id":"mrt3","name":"MRT3 Circle Line","available":false}]`
- Create: `site/js/schema.js`, `site/js/layers.js`, `site/js/main.js`
- Test: `site/tests/schema.test.mjs`, `site/tests/layers.test.mjs`

**Interfaces:**
- Produces:
  - `schema.js`: `validateStory(story) -> string[]` (an empty array means valid). It checks the `story.json` shape in Task 8 and that every `fact.source_id` matches `/^SRC-\d{3}$/`.
  - `layers.js`:
    - `COLORS` (Global Constraints values, keyed by `line_id`).
    - `buildLayers({debug: boolean}) -> object[]`, the MapLibre layer specs, in order:
      - `bld3d` (fill-extrusion on the style's vector source, `source-layer: "building"`, height `coalesce(render_height, 8)`);
      - `rail`, `rts`, `eart` (line);
      - `massing` (fill-extrusion from `base`/`top`);
      - only when debug: `debug-road` (dashed) and `debug-crossing` (red circle).
    - `tileNotice(event) -> boolean`, true for a style or tile load error whose URL host is `tiles.openfreemap.org`.
  - `main.js`:
    - Reads `?line=` (default `jb`) and `?debug=1`.
    - Loads `data/lines.json`, then `data/<line>/{network.geojson, massing.geojson, story.json, photos.json}`, plus `debug.geojson` only when debug.
    - Creates the map with `preserveDrawingBuffer: true`.
    - Adds the layers and markers: stations as square markers with a popup showing name and status; landmarks as ◆, or ▣ with a photo popup when `photo` is set.
    - Shows the header with the line switcher. Unavailable lines are disabled and show "Coming soon".
    - Shows the footer text verbatim, and the tile-failure notice "Base map unavailable. Lines and stations still work."

- [ ] **Step 1: Write the failing tests**

```js
test("debug layers only with ?debug=1", () => {
  assert.ok(!buildLayers({debug:false}).some(l => l.id.startsWith("debug")));
  assert.deepEqual(buildLayers({debug:true}).filter(l => l.id.startsWith("debug")).map(l => l.id), ["debug-road","debug-crossing"]);
});
test("tileNotice", () => {
  assert.equal(tileNotice({error:{url:"https://tiles.openfreemap.org/planet/1/2/3.pbf"}}), true);
  assert.equal(tileNotice({error:{url:"https://example.org/x"}}), false);
});
test("validateStory rejects fact without source", () => {
  assert.ok(validateStory({tour:[{id:"a", title:"t", body:"b", camera:{center:[0,0],zoom:1,bearing:0,pitch:0}, fact:{text:"x"}}]}).length > 0);
});
```

- [ ] **Step 2: Run and see them fail**

Run: `node --test site/tests/`
Expected: FAIL (module not found)

- [ ] **Step 3: Implement the modules, `index.html` and `explorer.css`.** The CSS uses Buruh tokens as custom properties on `:root`, sets `border-radius: 0` everywhere, and uses a visible focus ring with the `focus` tokens from the snapshot. At `@media (max-width: 700px)`, `.card` becomes a bottom sheet (`left:8px; right:8px; bottom:16px; top:auto; max-height:45vh; overflow:auto`), and the map's navigation control moves to `top-right`.

- [ ] **Step 4: Run the tests, then check by hand**

Run: `node --test site/tests/` → all pass.
Then `.venv/Scripts/python -m http.server -d site 8000` and open `http://localhost:8000/`:
- Lines, stations and landmarks render with 3D buildings and massing.
- `?debug=1` shows the dashed road route and red crossings, and the default view shows neither.
- With the network tab set to block `tiles.openfreemap.org`, the notice appears and markers still render.
- At 390 px wide, the card is a bottom sheet and the zoom control is visible.

- [ ] **Step 5: Commit**

```bash
git add site/index.html site/css site/js site/tests site/data/lines.json
git commit -m "Explorer: site shell, data loading, map layers, debug view"
```

---

### Task 8: Story, tour, places and facts

**Files:**
- Create: `site/data/jb/story.json`
- Create: `site/js/tour.js` (pure state and card model), `site/js/camera.js`, `site/js/ui.js` (DOM glue for Intro, Tour and Places)
- Modify: `site/js/main.js` (wire `ui.js`)
- Modify: `docs/sources/source-register.csv` (new rows `SRC-053`… for each fact, in the existing column format)
- Test: `site/tests/tour.test.mjs`, `site/tests/story.test.mjs`

**Interfaces:**
- Consumes: `validateStory` (Task 7), `photos.json` (Task 6), and stations from `network.geojson` (Task 5).
- Produces:
  - `story.json` shape:
    - `{line_set, intro:{headline, body}, tour:[TourStep], places:{start:Camera}}`
    - `TourStep = {id, title, body, status_tag, camera:Camera, photo: key|null, fact: {text, source_id}|null}`
    - `Camera = {center:[lon,lat], zoom, bearing, pitch}`
  - `tour.js`:
    - `createTour(steps) -> {index, next(), prev(), goto(i), current()}`. It wraps at both ends.
    - `cardPhoto(step, photos) -> {kind:"photo", src, credit, page} | {kind:"snapshot"}`
  - `camera.js`: `cameraMove(camera, {reduced:boolean}) -> {method:"flyTo"|"jumpTo", options}`. The `flyTo` duration is `2600` and `essential: true`. When `reduced` is set, it uses `jumpTo` and has no orbit.
  - `ui.js`:
    - Tour cards show the photo or a snapshot. The snapshot is `map.getCanvas().toDataURL("image/jpeg", 0.8)` taken on `moveend`, labeled "3D view".
    - The card shows the status tag, "Stop N of M", the title, the body, a "Did you know?" box only when `fact` exists, "Open in 3D", and Prev/Next.
    - ArrowLeft and ArrowRight work in Tour and Places.
    - The Places dropdown lists Bukit Chagar, then every station in line order (`"Tebrau 05 · Name"` / `"Iskandar Puteri 05 · Name"`).
    - Only the latest camera request is applied. Each move carries the tour index, and stale `moveend` snapshots are ignored.
    - Intro has "Start the tour" and "Skip intro". Places has a map key (line colors and status), Reset (returns to the selected location), and a card with Prev/Next through stations.
    - Every photo `<img>` has `alt` set to the stop or landmark name. Snapshot images use `alt="3D view of {title}"`.

Tour stops (exact order, copy from spike page `TOUR`, updated):
1. Five minutes to Singapore
2. One interchange, three ways out
3. The old town and the waterfront
4. Danga Bay
5. To Bukit Indah
6. Up the Tebrau spine
7. AEON, IKEA and Toppen
8. Straight on to Ulu Tiram

Photo keys: `woodlands_rts, jb_sentral, dataran, null, bukit_indah, ksl, ikea_tebrau, ulu_tiram`. Facts: research each candidate below (WebSearch/WebFetch). Keep a fact only if a primary or reputable source confirms it, register the source, and otherwise set `fact: null`:
- RTS Link crossing length;
- Sultan Abu Bakar Mosque construction years;
- Legoland Malaysia opening year and "first in Asia";
- one fact each for Bukit Chagar/JB Sentral and Ulu Tiram if sourceable.

The text must not say more than the source does.

- [ ] **Step 1: Write the failing tests**

```js
test("tour rapid steps end consistent", () => {
  const t = createTour([{id:"a"},{id:"b"},{id:"c"}]);
  for (let i = 0; i < 7; i++) t.next();       // 7 mod 3 = 1
  assert.equal(t.current().id, "b");
  t.prev(); t.prev(); assert.equal(t.current().id, "c");
});
test("cameraMove reduced", () => {
  const c = {center:[103.76,1.46], zoom:15, bearing:0, pitch:50};
  assert.equal(cameraMove(c, {reduced:true}).method, "jumpTo");
  assert.deepEqual(cameraMove(c, {reduced:false}).options.duration, 2600);
});
test("cardPhoto fallback", () => {
  assert.deepEqual(cardPhoto({photo:"danga_bay"}, {}), {kind:"snapshot"});
  assert.deepEqual(cardPhoto({photo:null}, {}), {kind:"snapshot"});
  assert.equal(cardPhoto({photo:"ksl"}, {ksl:{src:"photos/jb/ksl.jpg", credit:"Photo: X · CC BY-SA 4.0 · Wikimedia Commons", page:"p"}}).kind, "photo");
});
test("story.json is valid and every fact source is registered", async () => {
  const story = JSON.parse(await readFile("site/data/jb/story.json", "utf8"));
  assert.deepEqual(validateStory(story), []);
  assert.equal(story.tour.length, 8);
  const reg = await readFile("docs/sources/source-register.csv", "utf8");
  for (const s of story.tour) if (s.fact) assert.ok(reg.includes("\n" + s.fact.source_id + ","), s.fact.source_id);
});
```

- [ ] **Step 2: Run and see them fail**

Run: `node --test site/tests/`
Expected: FAIL

- [ ] **Step 3: Implement `tour.js`, `camera.js`, `ui.js`; research the facts; write `story.json`; add the source-register rows**

- [ ] **Step 4: Run the tests, then check by hand**

Run: `node --test site/tests/` → all pass.
In the browser:
- Intro orbits (and doesn't with OS reduced motion on).
- Each of the 8 stops flies and shows its photo with a clickable credit. Stop 4 shows a "3D view" snapshot.
- Mashing Next 10 times ends with the card and camera on the same stop.
- Places → the dropdown jumps to any station.
- Arrow keys work.

- [ ] **Step 5: Commit**

```bash
git add site docs/sources/source-register.csv
git commit -m "Explorer: intro, guided tour with photos and sourced facts, 3D places"
```

---

### Task 9: Pages workflow (dispatch-only), security scan, handoff

**Files:**
- Create: `.github/workflows/explorer-pages.yml`
- Modify: `docs/security-review.md` (append an "Explorer re-scan 2026-11-…" section with results)
- Create: `docs/handoffs/explorer-jb.md`
- Modify: `README.md` (explorer section: what it is, how to run locally, how to rebuild data, owner review items)

**Details:**
- **Workflow:**
  - `on: workflow_dispatch` only, with no push or schedule trigger.
  - Jobs: run `node --test site/tests/`, then `actions/upload-pages-artifact` (path `site`), then `actions/deploy-pages`.
  - `permissions: pages: write, id-token: write, contents: read`.
  - Every action is pinned to a full commit SHA with the version in a comment. Look up the SHAs with `gh api repos/actions/<name>/git/ref/tags/<tag>` (repo security rule, `docs/security-review.md` finding 9).
- **Handoff `explorer-jb.md`:**
  - What was built.
  - The owner review list for the single release review (spec §5.9):
    1. line colors;
    2. the station names (`results/explorer/jb_station_names.csv`);
    3. every fact with its source;
    4. the explorer itself (local URL).
  - The deferred items: hand-set building heights; Three.js hero stations; Mutiara and MRT3 plans.
  - How to publish once approved: Actions → explorer-pages → Run workflow.

- [ ] **Step 1: Verify the workflow cannot auto-run**

Run: `grep -E "^\s*(push|schedule|pull_request):" .github/workflows/explorer-pages.yml | wc -l`
Expected: `0`

- [ ] **Step 2: Run the full test suite**

Run: `.venv/Scripts/python -m pytest pipeline/explorer/tests -v && node --test site/tests/`
Expected: all pass

- [ ] **Step 3: Run the security scan** from `docs/security-review.md` §Method over the branch's commits since `main`, including the regex list and the email/path search. Also run `grep -rE "pk\.eyJ|sk\.eyJ|AIza|ghp_|github_pat_" site pipeline/explorer`.
Expected: no credentials. Record the results in the new section.

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/explorer-pages.yml docs/security-review.md docs/handoffs/explorer-jb.md README.md
git commit -m "Explorer: dispatch-only Pages workflow, security re-scan, handoff"
```

- [ ] **Step 5: Stop for owner review** (CLAUDE.md: stop after each stage). Do not dispatch the Pages workflow.
