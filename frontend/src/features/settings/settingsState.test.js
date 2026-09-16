import assert from "node:assert/strict";
import test from "node:test";
import { persistSettingChange, validateWorkspaceDescription } from "./settingsState.js";

test("validates the real persisted Workspace description boundary", () => {
  assert.equal(validateWorkspaceDescription("a".repeat(1000)), "");
  assert.match(validateWorkspaceDescription("a".repeat(1001)), /1 000/);
});

test("does not report a saved setting after persistence failure", async () => {
  const previous = { id: "workspace-a", description: "Persisted" };
  let visible = previous;
  const failure = new Error("save rejected");
  const result = await persistSettingChange(async () => { throw failure; }, (workspace) => { visible = workspace; return true; });
  assert.deepEqual(result, { ok: false, error: failure });
  assert.strictEqual(visible, previous);
});

test("rejects a late Settings save after the active Workspace changes", async () => {
  const previous = { id: "workspace-b", description: "Current" };
  let visible = previous;
  const result = await persistSettingChange(
    async () => ({ id: "workspace-a", description: "Late" }),
    () => false,
  );
  assert.deepEqual(result, { ok: false, stale: true });
  assert.strictEqual(visible, previous);
});

test("reports success only after the persisted Workspace response is accepted", async () => {
  const saved = { id: "workspace-a", description: "Saved" };
  const result = await persistSettingChange(async () => saved, (workspace) => workspace.id === "workspace-a");
  assert.deepEqual(result, { ok: true, value: saved });
});
