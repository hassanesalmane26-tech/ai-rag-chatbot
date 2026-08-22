import assert from "node:assert/strict";
import test from "node:test";
import { canEnterWorkspace, membershipRoleLabel, needsPersonalOnboarding, organizationChoices } from "./sessionState.js";

test("requires a validated session and selected Organization before entering", () => {
  assert.equal(canEnterWorkspace("anonymous", null), false);
  assert.equal(canEnterWorkspace("authenticated", { active_organization_id: null }), false);
  assert.equal(canEnterWorkspace("authenticated", { active_organization_id: "org-1" }), true);
});

test("identifies a session with no server-authored tenant for onboarding", () => {
  assert.equal(needsPersonalOnboarding({ organizations: [] }), true);
  assert.equal(needsPersonalOnboarding({ organizations: [{ id: "org-1", workspaces: [] }] }), false);
});

test("enters the Workspace immediately after onboarding returns active context", () => {
  const onboarded = {
    active_organization_id: "org-personal",
    active_workspace_id: "workspace-personal",
    organizations: [{ id: "org-personal", workspaces: [{ id: "workspace-personal" }] }],
  };
  assert.equal(canEnterWorkspace("onboarding", onboarded), false);
  assert.equal(canEnterWorkspace("authenticated", onboarded), true);
});

test("keeps Organization and Workspace choices server-authored", () => {
  const organizations = [{ id: "org-1", workspaces: [{ id: "workspace-1" }] }];
  assert.deepEqual(organizationChoices({ organizations }), organizations);
  assert.deepEqual(organizationChoices({ organizations: [{ name: "invalid" }] }), []);
});

test("presents bounded membership roles without changing authorization values", () => {
  assert.equal(membershipRoleLabel("owner"), "Propriétaire");
  assert.equal(membershipRoleLabel("admin"), "Administrateur");
  assert.equal(membershipRoleLabel("member"), "Membre");
  assert.equal(membershipRoleLabel("unexpected"), "Membre");
});
