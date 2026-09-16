import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { artifactCapability } from "./artifactState.js";

test("reports the current Artifact boundary without fake persistence or counts", () => {
  assert.deepEqual(artifactCapability, {
    available: false,
    persisted: false,
    canCreate: false,
    count: null,
    state: "unavailable",
  });
});

test("Artifact UI exposes no fake count, creation, lifecycle or persistence", () => {
  const view = readFileSync(new URL("./ArtifactsView.jsx", import.meta.url), "utf8");
  assert.doesNotMatch(view, /0 artefact|Créer un artefact|Générer|progression|statut/i);
  assert.match(view, /Capacité indisponible/);
  assert.match(view, /ne crée ni ne persiste actuellement d’artefacts/);
});
