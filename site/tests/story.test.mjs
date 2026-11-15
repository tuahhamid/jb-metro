import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { validateStory } from "../js/schema.js";

test("story.json is valid and every fact source is registered", async () => {
  const story = JSON.parse(await readFile("site/data/jb/story.json", "utf8"));
  assert.deepEqual(validateStory(story), []);
  assert.equal(story.tour.length, 8);
  const reg = (await readFile("docs/sources/source-register.csv", "utf8")).replace(/\r\n/g, "\n");
  for (const s of story.tour) if (s.fact) assert.ok(reg.includes("\n" + s.fact.source_id + ","), s.fact.source_id);
});

test("story photo keys exist in photos.json or are null", async () => {
  const story = JSON.parse(await readFile("site/data/jb/story.json", "utf8"));
  const photos = JSON.parse(await readFile("site/data/jb/photos.json", "utf8"));
  assert.deepEqual(story.tour.map((s) => s.photo), ["woodlands_rts", "jb_sentral", "dataran", null, "bukit_indah", "ksl", "ikea_tebrau", "ulu_tiram"]);
  for (const s of story.tour) if (s.photo) assert.ok(photos[s.photo], s.photo);
});

test("tour titles make no unsourced time or number claims", async () => {
  // spec §5.7: facts without a source are removed. Titles are not checked by validateStory, so pin them here.
  const story = JSON.parse(await readFile("site/data/jb/story.json", "utf8"));
  for (const s of story.tour) assert.doesNotMatch(s.title, /\d|\b(one|two|three|four|five|six|seven|eight|nine|ten)\s+(minutes?|hours?|km)\b/i, s.title);
});
