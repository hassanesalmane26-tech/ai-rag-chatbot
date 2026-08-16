import assert from "node:assert/strict";
import test from "node:test";
import { canEnterWorkspace, organizationChoices } from "./sessionState.js";

test("requires a validated session and selected Organization before entering", () => {
  assert.equal(canEnterWorkspace("anonymous", null), false);
  assert.equal(canEnterWorkspace("authenticated", { active_organization_id: null }), false);
  assert.equal(canEnterWorkspace("authenticated", { active_organization_id: "org-1" }), true);
});

test("keeps Organization and Workspace choices server-authored", () => {
  const organizations = [{ id: "org-1", workspaces: [{ id: "workspace-1" }] }];
  assert.deepEqual(organizationChoices({ organizations }), organizations);
  assert.deepEqual(organizationChoices({ organizations: [{ name: "invalid" }] }), []);
});
