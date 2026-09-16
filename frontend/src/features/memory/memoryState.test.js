import assert from "node:assert/strict";
import test from "node:test";
import { acceptsMemoryResult, memoryLifecycle, persistMemoryChange, upsertMemory, validateMemory } from "./memoryState.js";

test("rejects stale Memory results after a Workspace switch", () => {
  assert.equal(acceptsMemoryResult("workspace-b", "workspace-a"), false);
  assert.equal(acceptsMemoryResult("workspace-a", "workspace-a"), true);
});

test("upserts memories without duplicate identities", () => {
  assert.deepEqual(upsertMemory([{ id: "a", updated_at: "2026-01-01" }, { id: "b", active: true, updated_at: "2026-01-02" }], { id: "b", active: false, updated_at: "2026-01-03" }), [
    { id: "b", active: false, updated_at: "2026-01-03" }, { id: "a", updated_at: "2026-01-01" },
  ]);
});

test("validates bounded explicit memory fields", () => {
  assert.match(validateMemory("", "content"), /titre/);
  assert.match(validateMemory("Title", ""), /contenu/);
  assert.equal(validateMemory("Title", "Content"), "");
});

test("derives explicit persistent Memory lifecycle states", () => {
  const base = { workspaceId: "workspace-a", loading: false, mutationId: null, error: "", count: 0 };
  assert.equal(memoryLifecycle(base), "empty");
  assert.equal(memoryLifecycle({ ...base, loading: true }), "loading");
  assert.equal(memoryLifecycle({ ...base, mutationId: "create" }), "saving");
  assert.equal(memoryLifecycle({ ...base, error: "offline" }), "error");
  assert.equal(memoryLifecycle({ ...base, count: 1 }), "ready");
  assert.equal(memoryLifecycle({ ...base, workspaceId: null }), "unavailable");
});

test("does not commit or report success when Memory persistence fails", async () => {
  const persisted = [{ id: "memory-a", title: "Persisted" }];
  let visible = persisted;
  const failure = new Error("write rejected");
  const result = await persistMemoryChange(
    async () => { throw failure; },
    (memory) => { visible = upsertMemory(visible, memory); },
  );
  assert.deepEqual(result, { ok: false, error: failure });
  assert.strictEqual(visible, persisted);
});

test("commits a Memory only after a successful retry", async () => {
  const persisted = [{ id: "memory-a", title: "Persisted", updated_at: "2026-01-01" }];
  let visible = persisted;
  let attempts = 0;
  const operation = async () => {
    attempts += 1;
    if (attempts === 1) throw new Error("temporary failure");
    return { id: "memory-a", title: "Recovered", updated_at: "2026-01-02" };
  };
  const commit = (memory) => { visible = upsertMemory(visible, memory); };
  assert.equal((await persistMemoryChange(operation, commit)).ok, false);
  assert.strictEqual(visible, persisted);
  assert.equal((await persistMemoryChange(operation, commit)).ok, true);
  assert.equal(visible[0].title, "Recovered");
});

test("rejects a successful write result after its Workspace becomes stale", async () => {
  const persisted = [{ id: "memory-original" }];
  let visible = persisted;
  let commitChecked = false;
  const result = await persistMemoryChange(
    async () => ({ id: "memory-a" }),
    () => { commitChecked = true; return false; },
  );
  assert.deepEqual(result, { ok: false, stale: true });
  assert.equal(commitChecked, true);
  assert.strictEqual(visible, persisted);
});
