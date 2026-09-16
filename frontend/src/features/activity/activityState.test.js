import assert from "node:assert/strict";
import test from "node:test";
import { acceptsActivityResult, activityLifecycle, formatActivityTime, normalizeActivityEvents } from "./activityState.js";

test("formats valid Workspace activity dates without exposing raw metadata", () => {
  assert.match(formatActivityTime("2026-08-22T10:00:00Z"), /2026/);
});

test("uses a recoverable label for invalid activity dates", () => {
  assert.equal(formatActivityTime("not-a-date"), "Date indisponible");
});

test("keeps only the sanitized Activity contract in deterministic order", () => {
  const values = normalizeActivityEvents([
    { id: "a", label: "Older", created_at: "2026-01-01", actor_user_id: "secret", metadata: { private: true } },
    { id: "b", label: "Newer", created_at: "2026-01-02", request_id: "secret" },
  ]);
  assert.deepEqual(values.map(({ id }) => id), ["b", "a"]);
  assert.equal("actor_user_id" in values[1], false);
  assert.equal("metadata" in values[1], false);
  assert.equal("request_id" in values[0], false);
});

test("rejects stale Activity after a Workspace switch", () => {
  assert.equal(acceptsActivityResult("workspace-b", "workspace-a"), false);
  assert.equal(acceptsActivityResult("workspace-a", "workspace-a"), true);
});

test("derives exclusive loading, error, empty and ready Activity states", () => {
  const base = { workspaceId: "workspace-a", loading: false, error: "", count: 0 };
  assert.equal(activityLifecycle(base), "empty");
  assert.equal(activityLifecycle({ ...base, loading: true }), "loading");
  assert.equal(activityLifecycle({ ...base, error: "offline" }), "error");
  assert.equal(activityLifecycle({ ...base, count: 1 }), "ready");
  assert.equal(activityLifecycle({ ...base, workspaceId: null }), "unavailable");
});
