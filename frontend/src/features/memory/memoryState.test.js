import assert from "node:assert/strict";
import test from "node:test";
import { acceptsMemoryResult, upsertMemory, validateMemory } from "./memoryState.js";

test("rejects stale Memory results after a Workspace switch", () => {
  assert.equal(acceptsMemoryResult("workspace-b", "workspace-a"), false);
  assert.equal(acceptsMemoryResult("workspace-a", "workspace-a"), true);
});

test("upserts memories without duplicate identities", () => {
  assert.deepEqual(upsertMemory([{ id: "a" }, { id: "b", active: true }], { id: "b", active: false }), [
    { id: "b", active: false }, { id: "a" },
  ]);
});

test("validates bounded explicit memory fields", () => {
  assert.match(validateMemory("", "content"), /titre/);
  assert.match(validateMemory("Title", ""), /contenu/);
  assert.equal(validateMemory("Title", "Content"), "");
});
