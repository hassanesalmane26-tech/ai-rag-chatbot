import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { imageMetricValue } from "./workspaceHomeState.js";

test("Workspace Home presents only the server-provided image count", () => {
  assert.equal(imageMetricValue({ loading: true, count: null }), "…");
  assert.equal(imageMetricValue({ error: "unavailable", count: null }), "—");
  assert.equal(imageMetricValue({ count: null }), "—");
  assert.equal(imageMetricValue({ count: 0 }), 0);
  assert.equal(imageMetricValue({ count: 4 }), 4);
});

test("Workspace Home uses the overview count without downloading image records", () => {
  const home = readFileSync(new URL("./WorkspaceHome.jsx", import.meta.url), "utf8");
  assert.match(home, /metrics\.images/);
  assert.doesNotMatch(home, /listImages|createImage/);
});
