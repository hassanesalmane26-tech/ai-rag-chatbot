import assert from "node:assert/strict";
import test from "node:test";
import { commandKeyAction, commandResults, commandSurfaceState, executeCommandResult, nextCommandIndex, normalizeCommandQuery } from "./commandState.js";

const modules = [{ id: "memory", label: "Memory" }, { id: "settings", label: "Paramètres" }];
const workspaces = [{ id: "w1", name: "Atlas", description: "Workspace produit" }];

test("normalizes empty and localized command queries", () => {
  assert.equal(normalizeCommandQuery("  MÉMOIRE  "), "mémoire");
  assert.equal(normalizeCommandQuery("   "), "");
});

test("returns one unified contract for real actions, modules and Workspaces", () => {
  const results = commandResults({ query: "", modules, workspaces, activeWorkspaceId: "w1" });
  assert.deepEqual(results.map(({ type }) => type), ["action", "module", "module", "workspace"]);
  assert.equal(results.at(-1).active, true);
  for (const result of results) assert.deepEqual(Object.keys(result).includes("title"), true);
});

test("returns no result for unsupported commands and never fabricates domains", () => {
  assert.deepEqual(commandResults({ query: "agents", modules, workspaces, activeWorkspaceId: "w1" }), []);
});

test("filters real Workspace descriptions without leaking unrelated entries", () => {
  const results = commandResults({ query: "produit", modules, workspaces, activeWorkspaceId: null });
  assert.deepEqual(results.map(({ key }) => key), ["workspace:w1"]);
});

test("keyboard selection wraps deterministically", () => {
  assert.equal(nextCommandIndex(-1, "next", 3), 0);
  assert.equal(nextCommandIndex(0, "previous", 3), 2);
  assert.equal(nextCommandIndex(2, "next", 3), 0);
  assert.equal(nextCommandIndex(1, "first", 3), 0);
  assert.equal(nextCommandIndex(1, "last", 3), 2);
  assert.equal(nextCommandIndex(0, "next", 0), -1);
});

test("exposes loading, error, empty and ready states without fake results", () => {
  assert.equal(commandSurfaceState({ loading: true, error: null, resultCount: 2 }), "loading");
  assert.equal(commandSurfaceState({ loading: false, error: "offline", resultCount: 2 }), "error");
  assert.equal(commandSurfaceState({ loading: false, error: null, resultCount: 0 }), "empty");
  assert.equal(commandSurfaceState({ loading: false, error: null, resultCount: 2 }), "ready");
});

test("executes only real module and Workspace destinations", () => {
  const calls = [];
  const actions = { navigate: (id) => calls.push(["navigate", id]), switchWorkspace: (id) => calls.push(["workspace", id]) };
  assert.equal(executeCommandResult({ type: "module", id: "memory" }, actions), true);
  assert.equal(executeCommandResult({ type: "workspace", id: "w1" }, actions), true);
  assert.equal(executeCommandResult({ type: "agent", id: "fake" }, actions), false);
  assert.deepEqual(calls, [["navigate", "memory"], ["workspace", "w1"]]);
});

test("mobile Command interaction uses the real shared loading, error and navigation path", () => {
  const calls = [];
  assert.equal(commandSurfaceState({ loading: true, error: null, resultCount: 0 }), "loading");
  assert.equal(commandSurfaceState({ loading: false, error: "offline", resultCount: 0 }), "error");
  const result = commandResults({ query: "memory", modules, workspaces, activeWorkspaceId: "w1" })[0];
  assert.equal(executeCommandResult(result, { navigate: (id) => calls.push(id), switchWorkspace: () => {} }), true);
  assert.deepEqual(calls, ["memory"]);
});

test("desktop Command interaction supports arrows and Enter on a real destination", () => {
  const calls = [];
  const results = commandResults({ query: "Atlas", modules, workspaces, activeWorkspaceId: "w1" });
  const selection = commandKeyAction({ key: "ArrowDown", selectedIndex: -1, resultCount: results.length, inputFocused: true });
  assert.deepEqual(selection, { handled: true, selectedIndex: 0, execute: false });
  const enter = commandKeyAction({ key: "Enter", selectedIndex: 0, resultCount: results.length, inputFocused: true });
  assert.equal(enter.execute, true);
  executeCommandResult(results[enter.selectedIndex], { navigate: () => {}, switchWorkspace: (id) => calls.push(id) });
  assert.deepEqual(calls, ["w1"]);
});
