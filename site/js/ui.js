// DOM glue for the three views: Intro (orbit), Tour (cards + camera), Places (3D stations).
import { createTour, cardPhoto } from "./tour.js";
import { cameraMove } from "./camera.js";
import { COLORS } from "./layers.js";

const motionQuery = matchMedia("(prefers-reduced-motion: reduce)");
const reduced = () => motionQuery.matches;
const STATION_ZOOM = 16.3;
const STATION_PITCH = 60;

function el(tag, attrs = {}, ...kids) {
  const n = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v === undefined || v === null) continue;
    if (k === "class") n.className = v;
    else if (k === "text") n.textContent = v;
    else if (k.startsWith("on")) n.addEventListener(k.slice(2), v);
    else n.setAttribute(k, v);
  }
  for (const c of kids) if (c !== null && c !== undefined) n.append(c);
  return n;
}

const pad2 = (n) => String(n).padStart(2, "0");

// Every station after the shared first one, in line order, plus a start entry.
function placeList(data) {
  const lines = data.network.features.filter((f) => f.properties.kind === "line").map((f) => f.properties);
  const stations = data.network.features.filter((f) => f.properties.kind === "station");
  const shared = stations.find((f) => f.properties.seq === 1);
  const list = [{
    id: "start", label: shared ? shared.properties.name : "Start", title: shared ? `${shared.properties.name} interchange` : "Start",
    kicker: "Interchange · concept", line_id: lines[0] && lines[0].line_id, status: "concept", camera: data.story.places.start,
    body: "Our concept interchange, beside the RTS Link viaduct and a short walk from JB Sentral and the checkpoint. " +
      "Colored blocks are our 3D models. Gray buildings are the real city.",
  }];
  for (const ln of lines) {
    const own = stations.filter((f) => f.properties.line_id === ln.line_id).sort((a, b) => a.properties.seq - b.properties.seq);
    for (const f of own) {
      const p = f.properties;
      if (shared && p.seq === 1 && p.name === shared.properties.name) continue;
      const bearing = (Math.atan2(p.ux, p.uy) * 180) / Math.PI + 30;
      list.push({
        id: p.station_id, label: `${ln.name} ${pad2(p.seq)} · ${p.name}`, title: p.name,
        kicker: `${ln.name} · station ${pad2(p.seq)} of ${own.length}`, line_id: p.line_id, status: p.status,
        camera: { center: f.geometry.coordinates, zoom: STATION_ZOOM, bearing, pitch: STATION_PITCH },
        body: "A concept station: a 100 m platform box under a colored roof, on a viaduct about 11 m up. " +
          "The same generic design is used at every station.",
      });
    }
  }
  return list;
}

export function initUI(map, data) {
  if (!data.story) return;
  const story = data.story;
  const tour = createTour(story.tour);
  const places = placeList(data);
  let placeIndex = 0;
  let view = null;
  let req = 0;          // only the latest camera request may finish (snapshot, orbit)
  let orbit = null;

  const ui = { intro: document.getElementById("introUI"), tour: document.getElementById("tourUI"), places: document.getElementById("placesUI") };
  const navButtons = [...document.querySelectorAll(".views button")];

  function stopOrbit() {
    if (orbit) cancelAnimationFrame(orbit);
    orbit = null;
  }

  // Move the camera; `after` runs once the map has settled on this (still the latest) request.
  function move(camera, after) {
    const mine = ++req;
    stopOrbit();
    const m = cameraMove(camera, { reduced: reduced() });
    map[m.method](m.options);
    if (!after) return;
    const settle = () => setTimeout(() => {
      if (mine !== req || map.isMoving()) return;
      let done = false;
      const fire = () => { if (!done && mine === req) { done = true; after(); } };
      map.once("idle", fire);
      setTimeout(fire, 4000);
    }, 0);
    if (m.method === "jumpTo") settle();
    else map.once("moveend", function onEnd() {
      if (mine !== req) return;
      if (map.isMoving()) { map.once("moveend", onEnd); return; }
      settle();
    });
  }

  function setView(v) {
    view = v;
    stopOrbit();
    for (const [k, node] of Object.entries(ui)) node.hidden = k !== v;
    for (const b of navButtons) b.setAttribute("aria-pressed", String(b.dataset.view === v));
    if (v === "intro") showIntro();
    if (v === "tour") showTour();
    if (v === "places") showPlace();
  }
  for (const b of navButtons) b.addEventListener("click", () => setView(b.dataset.view));

  // ---- Intro ----
  const nStations = new Set(data.network.features.filter((f) => f.properties.kind === "station").map((f) => f.geometry.coordinates.join(","))).size;
  const nLines = data.network.features.filter((f) => f.properties.kind === "line").length;
  ui.intro.append(
    el("div", { class: "intro" },
      el("div", { class: "k", text: `Concept · ${nLines} lines · ${nStations} stations` }),
      el("h1", { text: story.intro.headline }),
      el("p", { text: story.intro.body }),
      el("button", { type: "button", class: "btn go", text: "Start the tour →", onclick: () => { tour.goto(0); setView("tour"); } })),
    el("button", { type: "button", class: "btn ghost skip", text: "Skip intro →", onclick: () => setView("places") }));

  function showIntro() {
    const start = { center: map.getCenter().toArray(), zoom: Math.min(map.getZoom(), 11.6), bearing: -10, pitch: 35 };
    move(start, () => {
      if (view !== "intro" || reduced()) return;
      let last = performance.now();
      const spin = (t) => {
        map.setBearing(map.getBearing() + (t - last) * 0.0015);
        last = t;
        orbit = requestAnimationFrame(spin);
      };
      orbit = requestAnimationFrame(spin);
    });
  }
  for (const ev of ["mousedown", "touchstart", "wheel"]) map.getCanvasContainer().addEventListener(ev, stopOrbit, { passive: true });

  // ---- Tour ----
  const media = el("div", { class: "media" });
  const tag = el("span", { class: "tag" });
  const stopN = el("span", { class: "k" });
  const title = el("h2");
  const head = el("div", { class: "hd" }, tag, " ", stopN, title);
  const body = el("p");
  const factText = el("span");
  const fact = el("div", { class: "fact" }, el("div", { class: "k", text: "Did you know?" }), factText);
  const open3d = el("button", { type: "button", class: "btn ghost wide", text: "Open in 3D ↗", onclick: () => openIn3D() });
  const prev = el("button", { type: "button", class: "btn ghost", text: "← Prev", onclick: () => { tour.prev(); showTour(); } });
  const next = el("button", { type: "button", class: "btn", text: "Next →", onclick: () => { tour.next(); showTour(); } });
  ui.tour.append(el("article", { class: "card", "aria-live": "polite" }, media, head,
    el("div", { class: "bd" }, body, fact, open3d, el("div", { class: "row" }, prev, next))));

  function snapshotInto(box, alt) {
    box.replaceChildren(el("span", { class: "tag label", text: "3D view" }));
    return () => {
      try {
        const src = map.getCanvas().toDataURL("image/jpeg", 0.8);
        box.replaceChildren(el("img", { src, alt }), el("span", { class: "tag label", text: "3D view" }));
      } catch { /* canvas unavailable: keep the label only */ }
    };
  }

  function showTour() {
    const s = tour.current();
    const i = tour.index;
    tag.textContent = s.status_tag;
    tag.className = "tag" + (/under construction/i.test(s.status_tag) ? " under-construction" : "");
    head.className = "hd" + (/rts/i.test(s.status_tag) ? " navy" : "");
    stopN.textContent = `Stop ${i + 1} of ${story.tour.length}`;
    title.textContent = s.title;
    body.textContent = s.body;
    fact.hidden = !s.fact;
    factText.textContent = s.fact ? s.fact.text : "";
    const ph = cardPhoto(s, data.photos);
    let after = null;
    if (ph.kind === "photo") {
      const img = el("img", { src: ph.src, alt: s.title });
      const credit = el("div", { class: "credit" }, el("a", { href: ph.page, target: "_blank", rel: "noopener", text: ph.credit }));
      img.addEventListener("error", () => {
        if (tour.index !== i) return;
        const shoot = snapshotInto(media, `3D view of ${s.title}`);
        if (!map.isMoving()) shoot(); else map.once("idle", () => { if (tour.index === i) shoot(); });
      });
      media.replaceChildren(img, credit);
    } else {
      after = snapshotInto(media, `3D view of ${s.title}`);
    }
    move(s.camera, after && (() => { if (view === "tour" && tour.index === i) after(); }));
  }

  function openIn3D() {
    const c = tour.current().camera.center;
    let best = 0, bd = Infinity;
    places.forEach((p, k) => {
      const d = (p.camera.center[0] - c[0]) ** 2 + (p.camera.center[1] - c[1]) ** 2;
      if (d < bd) { bd = d; best = k; }
    });
    placeIndex = best;
    setView("places");
  }

  // ---- Places ----
  const select = el("select", { id: "placeSelect", "aria-label": "Location" });
  places.forEach((p, k) => select.append(el("option", { value: String(k), text: p.label })));
  select.addEventListener("change", () => { placeIndex = +select.value; showPlace(); });
  const pTag = el("span", { class: "tag" });
  const pKick = el("div", { class: "k" });
  const pTitle = el("h2");
  const pHead = el("div", { class: "hd" }, pTag, pKick, pTitle);
  const pBody = el("p");
  const pPrev = el("button", { type: "button", class: "btn ghost", text: "← Prev", onclick: () => stepPlace(-1) });
  const pNext = el("button", { type: "button", class: "btn", text: "Next →", onclick: () => stepPlace(1) });
  const key = el("div", { class: "key", "aria-label": "Map key" });
  for (const f of data.network.features.filter((x) => x.properties.kind === "line")) {
    key.append(el("div", {}, el("i", { style: `background:${COLORS[f.properties.line_id] || "#13213A"}` }), `${f.properties.name} (${f.properties.status})`));
  }
  const ctx = new Map();
  for (const f of data.network.features) if (f.properties.kind === "context_rail") ctx.set(f.properties.line_id, f.properties);
  const ctxName = { RTS: "RTS Link", KTM: "KTM rail" };
  for (const [id, p] of ctx) key.append(el("div", {}, el("i", { style: `background:${COLORS[id]}` }), `${ctxName[id] || id} (${p.status})`));
  key.append(el("div", {}, el("i", { style: "background:#fff;outline:1px solid #8C8577" }), "Buildings (OpenStreetMap)"));
  ui.places.append(
    el("div", { class: "tools" }, el("label", {}, el("span", { class: "k", text: "Location" }), el("br"), select),
      el("button", { type: "button", text: "↻ Reset", onclick: () => showPlace() })),
    el("article", { class: "card places-card", "aria-live": "polite" }, pHead,
      el("div", { class: "bd" }, pBody, el("div", { class: "row" },
        el("button", { type: "button", class: "btn ghost", text: "Tour", onclick: () => setView("tour") }),
        el("span", {}, pPrev, " ", pNext)))),
    key);

  function stepPlace(d) {
    placeIndex = (placeIndex + d + places.length) % places.length;
    showPlace();
  }

  function showPlace() {
    const p = places[placeIndex];
    select.value = String(placeIndex);
    pTag.textContent = p.status;
    pKick.textContent = p.kicker;
    pTitle.textContent = p.title;
    pBody.textContent = p.body;
    pHead.className = "hd " + (p.line_id || "");
    move(p.camera);
  }

  // ---- Keyboard ----
  document.addEventListener("keydown", (e) => {
    if (e.altKey || e.ctrlKey || e.metaKey) return;
    if (e.target && /^(INPUT|SELECT|TEXTAREA)$/.test(e.target.tagName)) return;
    if (e.target && e.target.closest && e.target.closest("#map")) return;   // arrows on the map pan it
    const d = e.key === "ArrowRight" ? 1 : e.key === "ArrowLeft" ? -1 : 0;
    if (!d) return;
    if (view === "tour") { d > 0 ? tour.next() : tour.prev(); showTour(); e.preventDefault(); }
    else if (view === "places") { stepPlace(d); e.preventDefault(); }
  });

  setView("intro");
}
