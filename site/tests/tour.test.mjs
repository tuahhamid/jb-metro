import test from "node:test";
import assert from "node:assert/strict";
import { createTour, cardPhoto } from "../js/tour.js";
import { cameraMove } from "../js/camera.js";

test("tour rapid steps end consistent", () => {
  const t = createTour([{ id: "a" }, { id: "b" }, { id: "c" }]);
  for (let i = 0; i < 7; i++) t.next();       // 7 mod 3 = 1
  assert.equal(t.current().id, "b");
  t.prev(); t.prev(); assert.equal(t.current().id, "c");
});

test("tour goto clamps into range and index follows", () => {
  const t = createTour([{ id: "a" }, { id: "b" }]);
  t.goto(5); assert.equal(t.index, 1);
  t.goto(-3); assert.equal(t.index, 0);
});

test("cameraMove reduced", () => {
  const c = { center: [103.76, 1.46], zoom: 15, bearing: 0, pitch: 50 };
  assert.equal(cameraMove(c, { reduced: true }).method, "jumpTo");
  assert.deepEqual(cameraMove(c, { reduced: false }).options.duration, 2600);
  assert.equal(cameraMove(c, { reduced: false }).options.essential, true);
  assert.deepEqual(cameraMove(c, { reduced: true }).options.center, c.center);
});

test("cardPhoto fallback", () => {
  assert.deepEqual(cardPhoto({ photo: "danga_bay" }, {}), { kind: "snapshot" });
  assert.deepEqual(cardPhoto({ photo: null }, {}), { kind: "snapshot" });
  assert.deepEqual(cardPhoto({ photo: "ksl" }, null), { kind: "snapshot" });
  assert.equal(cardPhoto({ photo: "ksl" }, { ksl: { src: "photos/jb/ksl.jpg", credit: "Photo: X · CC BY-SA 4.0 · Wikimedia Commons", page: "p" } }).kind, "photo");
});
