// MapLibre layer specs for the explorer. Pure data: no DOM, no map instance (tested with node --test).

// Proposed extension of Buruh Hybrid (owner reviews at release, spec §5.2).
export const COLORS = { T1: "#FF6A13", IP2: "#2E8C83", RTS: "#13213A", KTM: "#8C8577", MUTIARA: "#E8C547", MRT3: "#8F7CF0" };

const TILE_HOST = "tiles.openfreemap.org";
const byLine = (fallback) => ["match", ["get", "line_id"], ...Object.entries(COLORS).flat(), fallback];

// `vectorSource` is the style's vector source id (OpenFreeMap: "openmaptiles").
export function buildLayers({ debug = false, vectorSource = "openmaptiles" } = {}) {
  const kind = (k) => ["==", ["get", "kind"], k];
  const layers = [
    { id: "bld3d", type: "fill-extrusion", source: vectorSource, "source-layer": "building", minzoom: 13,
      paint: { "fill-extrusion-color": "#ECE8E0", "fill-extrusion-height": ["coalesce", ["get", "render_height"], 8],
               "fill-extrusion-base": ["coalesce", ["get", "render_min_height"], 0], "fill-extrusion-opacity": 0.92 } },
    { id: "rail", type: "line", source: "network", filter: ["all", kind("context_rail"), ["==", ["get", "line_id"], "KTM"]],
      paint: { "line-color": COLORS.KTM, "line-width": 2, "line-dasharray": [2, 1.5] } },
    { id: "rts", type: "line", source: "network", filter: ["all", kind("context_rail"), ["==", ["get", "line_id"], "RTS"]],
      paint: { "line-color": COLORS.RTS, "line-width": ["interpolate", ["linear"], ["zoom"], 11, 3, 16, 6] } },
    { id: "eart", type: "line", source: "network", filter: kind("line"), layout: { "line-cap": "round", "line-join": "round" },
      paint: { "line-color": byLine("#13213A"), "line-width": ["interpolate", ["linear"], ["zoom"], 11, 4, 16, 8],
               "line-opacity": ["interpolate", ["linear"], ["zoom"], 15, 1, 16.5, 0.25] } },
    { id: "massing", type: "fill-extrusion", source: "massing",
      paint: { "fill-extrusion-color": ["match", ["get", "kind"], "rts_viaduct", COLORS.RTS, "station", "#F6F3EC", "roof", byLine("#13213A"), byLine("#13213A")],
               "fill-extrusion-base": ["get", "base"], "fill-extrusion-height": ["get", "top"], "fill-extrusion-opacity": 0.97 } },
  ];
  if (debug) {
    layers.push(
      { id: "debug-road", type: "line", source: "debug", filter: kind("road_route"),
        paint: { "line-color": "#B23F06", "line-width": 2, "line-dasharray": [1, 1.5] } },
      { id: "debug-crossing", type: "circle", source: "debug", filter: kind("crossing"),
        paint: { "circle-color": "#DD1111", "circle-radius": 5, "circle-stroke-color": "#FFFFFF", "circle-stroke-width": 1.5 } });
  }
  return layers;
}

function hostOf(url) {
  try { return new URL(url).host; } catch { return null; }
}

// True when a MapLibre "error" event means the base map failed: an error from the tile/style
// server, or any error before the style has loaded (a blocked or offline request has no URL).
export function tileNotice(event, { styleLoaded = true } = {}) {
  const err = event && event.error;
  if (!err) return false;
  if (!styleLoaded) return true;
  if (err.url) return hostOf(err.url) === TILE_HOST;
  const urls = String(err.message || "").match(/https?:\/\/[^\s"')]+/g) || [];
  return urls.some((u) => hostOf(u) === TILE_HOST);
}
