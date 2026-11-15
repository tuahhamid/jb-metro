import test from "node:test";
import assert from "node:assert/strict";
import { buildLayers, tileNotice, COLORS } from "../js/layers.js";

test("debug layers only with ?debug=1", () => {
  assert.ok(!buildLayers({ debug: false }).some(l => l.id.startsWith("debug")));
  assert.deepEqual(buildLayers({ debug: true }).filter(l => l.id.startsWith("debug")).map(l => l.id), ["debug-road", "debug-crossing"]);
});

test("layer order is buildings, rail, rts, eart, massing", () => {
  assert.deepEqual(buildLayers({ debug: false }).map(l => l.id), ["bld3d", "rail", "rts", "eart", "massing"]);
});

test("tileNotice", () => {
  assert.equal(tileNotice({ error: { url: "https://tiles.openfreemap.org/planet/1/2/3.pbf" } }), true);
  assert.equal(tileNotice({ error: { url: "https://example.org/x" } }), false);
  assert.equal(tileNotice({ error: { message: "Failed to fetch https://tiles.openfreemap.org/styles/positron" } }), true);
  assert.equal(tileNotice({}), false);
});

test("line colors match the proposed extension", () => {
  assert.deepEqual(COLORS, { T1: "#FF6A13", IP2: "#2E8C83", RTS: "#13213A", KTM: "#8C8577", MUTIARA: "#E8C547", MRT3: "#8F7CF0" });
});

test("tileNotice: any error before the style has loaded is a base-map failure", () => {
  const blocked = { error: new TypeError("Failed to fetch") };     // blocked/offline: no URL in the error
  assert.equal(tileNotice(blocked, { styleLoaded: false }), true);
  assert.equal(tileNotice(blocked, { styleLoaded: true }), false);
});
