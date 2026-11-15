import test from "node:test";
import assert from "node:assert/strict";
import { validateStory } from "../js/schema.js";

const cam = { center: [103.76, 1.46], zoom: 14, bearing: 0, pitch: 45 };
const ok = { line_set: "jb", intro: { headline: "h", body: "b" }, places: { start: cam },
  tour: [{ id: "a", title: "t", body: "b", status_tag: "Concept line", camera: cam, photo: null, fact: { text: "x", source_id: "SRC-053" } }] };

test("validateStory rejects fact without source", () => {
  assert.ok(validateStory({ tour: [{ id: "a", title: "t", body: "b", camera: { center: [0, 0], zoom: 1, bearing: 0, pitch: 0 }, fact: { text: "x" } }] }).length > 0);
});

test("validateStory accepts a full story", () => {
  assert.deepEqual(validateStory(ok), []);
});

test("validateStory rejects a bad camera and a bad source id", () => {
  const bad = structuredClone(ok);
  bad.tour[0].camera = { center: [1], zoom: "x" };
  bad.tour[0].fact.source_id = "SRC-5";
  assert.ok(validateStory(bad).length >= 2);
});
