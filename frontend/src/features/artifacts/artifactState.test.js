import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { artifactSurfaceState } from "./artifactState.js";

test("derives Artifact state only from real requests and persisted records", () => {
  assert.equal(artifactSurfaceState({ loading: true, images: [] }), "loading");
  assert.equal(artifactSurfaceState({ error: "Failed", images: [] }), "error");
  assert.equal(artifactSurfaceState({ images: [] }), "empty");
  assert.equal(artifactSurfaceState({ images: [{ id: "real-image" }] }), "ready");
});

test("Artifact UI exposes server-backed images without invented counts or generic creation", () => {
  const view = readFileSync(new URL("./ArtifactsView.jsx", import.meta.url), "utf8");
  assert.doesNotMatch(view, /0 artefact|Créer un artefact|progression/i);
  assert.match(view, /useWorkspaceImages\(activeWorkspaceId\)/);
  assert.match(view, /capability\?\.available/);
  assert.match(view, /Aucune création n’est simulée/);
  assert.match(view, /openNovaConversation\(\{ id: image.conversation_id \}\)/);
});
