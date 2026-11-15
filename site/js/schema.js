// Shape check for data/<line>/story.json. Returns a list of problems; [] means valid.
const SRC = /^SRC-\d{3}$/;
const isNum = (v) => typeof v === "number" && Number.isFinite(v);
const isStr = (v) => typeof v === "string" && v.length > 0;

function checkCamera(c, where, errs) {
  if (!c || !Array.isArray(c.center) || c.center.length !== 2 || !c.center.every(isNum)) errs.push(`${where}: camera.center must be [lon, lat]`);
  for (const k of ["zoom", "bearing", "pitch"]) if (!c || !isNum(c[k])) errs.push(`${where}: camera.${k} must be a number`);
}

export function validateStory(story) {
  const errs = [];
  if (!story || typeof story !== "object") return ["story must be an object"];
  if (!story.intro || !isStr(story.intro.headline) || !isStr(story.intro.body)) errs.push("intro needs headline and body");
  if (!story.places || !story.places.start) errs.push("places.start camera missing");
  else checkCamera(story.places.start, "places.start", errs);
  if (!Array.isArray(story.tour) || story.tour.length === 0) return [...errs, "tour must be a non-empty array"];
  const ids = new Set();
  story.tour.forEach((s, i) => {
    const w = `tour[${i}]`;
    for (const k of ["id", "title", "body"]) if (!isStr(s[k])) errs.push(`${w}: ${k} missing`);
    if (ids.has(s.id)) errs.push(`${w}: duplicate id ${s.id}`);
    ids.add(s.id);
    if (!isStr(s.status_tag)) errs.push(`${w}: status_tag missing`);
    checkCamera(s.camera, w, errs);
    if (s.photo !== null && !isStr(s.photo)) errs.push(`${w}: photo must be a key or null`);
    if (s.fact !== null) {
      if (!s.fact || !isStr(s.fact.text)) errs.push(`${w}: fact.text missing`);
      if (!s.fact || !SRC.test(s.fact.source_id || "")) errs.push(`${w}: fact needs a source_id like SRC-053`);
    }
  });
  return errs;
}
