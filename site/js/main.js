// Explorer entry point: loads a line set's data, builds the map, layers and markers.
// Views (intro, tour, places) are wired in ui.js.
import { buildLayers, tileNotice } from "./layers.js";
import { initUI } from "./ui.js";

const STYLE_URL = "https://tiles.openfreemap.org/styles/positron";
// Used when the base-map style cannot load: our lines, stations and massing still draw on paper.
const FALLBACK_STYLE = { version: 8, sources: {}, layers: [{ id: "bg", type: "background", paint: { "background-color": "#F6F3EC" } }] };

const params = new URLSearchParams(location.search);
const DEBUG = params.get("debug") === "1";

async function getJSON(url, { optional = false } = {}) {
  try {
    const r = await fetch(url);
    if (!r.ok) throw new Error(`${url}: HTTP ${r.status}`);
    return await r.json();
  } catch (e) {
    if (optional) return null;
    throw e;
  }
}

function el(tag, attrs = {}, ...kids) {
  const n = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") n.className = v;
    else if (k === "text") n.textContent = v;
    else n.setAttribute(k, v);
  }
  for (const c of kids) n.append(c);
  return n;
}

function lineSwitcher(lines, current) {
  const sel = document.getElementById("lineSwitch");
  for (const l of lines) {
    const o = el("option", { value: l.id, text: l.available ? l.name : `${l.name} · Coming soon` });
    if (!l.available) o.disabled = true;
    if (l.id === current) o.selected = true;
    sel.append(o);
  }
  sel.addEventListener("change", () => {
    const p = new URLSearchParams(location.search);
    p.set("line", sel.value);
    location.search = p.toString();
  });
}

function bbox(features) {
  const b = [Infinity, Infinity, -Infinity, -Infinity];
  for (const f of features) for (const [x, y] of f.geometry.coordinates) {
    b[0] = Math.min(b[0], x); b[1] = Math.min(b[1], y); b[2] = Math.max(b[2], x); b[3] = Math.max(b[3], y);
  }
  return [[b[0], b[1]], [b[2], b[3]]];
}

function addOverlays(map, data) {
  if (map.getSource("network")) return;
  const sources = map.getStyle().sources || {};
  const vectorSource = Object.keys(sources).find((k) => sources[k].type === "vector");
  map.addSource("network", { type: "geojson", data: data.network });
  map.addSource("massing", { type: "geojson", data: data.massing });
  if (data.debug) map.addSource("debug", { type: "geojson", data: data.debug });
  for (const layer of buildLayers({ debug: !!data.debug, vectorSource })) {
    if (layer.id === "bld3d" && !vectorSource) continue;
    map.addLayer(layer);
  }
}

function addMarkers(map, data) {
  const lineName = {};
  for (const f of data.network.features) if (f.properties.kind === "line") lineName[f.properties.line_id] = f.properties.name;
  const seen = new Set();
  for (const f of data.network.features) {
    const p = f.properties;
    const at = f.geometry.coordinates;
    if (p.kind === "station") {
      const spot = at.join(",");
      if (seen.has(spot)) continue;           // shared interchange: one marker
      seen.add(spot);
      const btn = el("button", { type: "button", class: `stn ${p.line_id}${p.seq === 1 ? " big" : ""}`, "aria-label": `${p.name} station`, title: p.name });
      const pop = el("div", { class: "pop" }, el("b", { text: p.name }), el("br"),
        el("span", { class: "k", text: `${lineName[p.line_id] || p.line_id} · ${p.status}` }));
      new maplibregl.Marker({ element: btn }).setLngLat(at).setPopup(new maplibregl.Popup({ offset: 10 }).setDOMContent(pop)).addTo(map);
    } else if (p.kind === "landmark") {
      const ph = p.photo && data.photos ? data.photos[p.photo] : null;
      const node = el(ph ? "button" : "div", { class: `lm${ph ? " photo" : ""}` }, el("i", { "aria-hidden": "true" }),
        el("span", { text: `${p.name}${ph ? " ▣" : ""}` }));
      if (ph) node.setAttribute("type", "button");
      const m = new maplibregl.Marker({ element: node, anchor: "left" }).setLngLat(at);
      if (ph) {
        const pop = el("div", { class: "pop" }, el("img", { src: ph.src, alt: p.name, loading: "lazy" }), el("b", { text: p.name }), el("br"),
          el("a", { class: "k", href: ph.page, target: "_blank", rel: "noopener", text: ph.credit }));
        m.setPopup(new maplibregl.Popup({ offset: 12, maxWidth: "300px" }).setDOMContent(pop));
      }
      m.addTo(map);
    }
  }
}

function navControl(map) {
  const mq = matchMedia("(max-width: 700px)");
  let ctrl = null;
  const place = () => {
    if (ctrl) map.removeControl(ctrl);
    ctrl = new maplibregl.NavigationControl({ visualizePitch: true });
    map.addControl(ctrl, mq.matches ? "top-right" : "bottom-right");
  };
  place();
  mq.addEventListener("change", place);
}

export async function boot() {
  const lines = await getJSON("data/lines.json");
  const want = params.get("line") || "jb";
  const line = lines.find((l) => l.id === want && l.available) || lines.find((l) => l.available);
  lineSwitcher(lines, line.id);
  document.getElementById("brandName").textContent = line.name;

  const base = `data/${line.id}/`;
  const [network, massing, story, photos, debug] = await Promise.all([
    getJSON(base + "network.geojson"), getJSON(base + "massing.geojson"),
    getJSON(base + "story.json", { optional: true }), getJSON(base + "photos.json", { optional: true }),
    DEBUG ? getJSON(base + "debug.geojson", { optional: true }) : null,
  ]);
  const data = { line, network, massing, story, photos, debug };

  const map = new maplibregl.Map({
    container: "map", style: STYLE_URL, bounds: bbox(network.features.filter((f) => f.properties.kind === "line")),
    fitBoundsOptions: { padding: 40 }, maxPitch: 75, attributionControl: false, preserveDrawingBuffer: true,
  });
  map.addControl(new maplibregl.AttributionControl({ compact: true }), "bottom-left");
  navControl(map);

  const notice = document.getElementById("notice");
  let fellBack = false;
  let styleLoaded = false;
  map.on("error", (e) => {
    if (!tileNotice(e, { styleLoaded })) return;
    notice.hidden = false;
    if (!fellBack && !styleLoaded) {
      fellBack = true;
      map.setStyle(FALLBACK_STYLE);
    }
  });
  map.on("style.load", () => { styleLoaded = true; addOverlays(map, data); });
  addMarkers(map, data);

  initUI(map, data);
  window.explorer = { map, data };   // handle for manual checks in the browser console
  return { map, data };
}

boot().catch((e) => {
  console.error(e);
  const n = document.getElementById("notice");
  n.textContent = "The explorer could not load its data.";
  n.hidden = false;
});
