import assert from "node:assert/strict";
import test from "node:test";
import { authorizationId, consentConfiguration, requestedScopes, safeAuthorizationRedirect } from "./consentState.js";

test("requires an exact HTTPS Supabase origin and a publishable key", () => {
  assert.equal(consentConfiguration("https://project.supabase.co", "sb_publishable_example").enabled, true);
  assert.equal(consentConfiguration("https://project.supabase.co/auth/v1", "sb_publishable_example").enabled, false);
  assert.equal(consentConfiguration("http://project.supabase.co", "sb_publishable_example").enabled, false);
  assert.equal(consentConfiguration("https://project.supabase.co", "[placeholder]").enabled, false);
});

test("accepts only bounded opaque authorization identifiers", () => {
  assert.equal(authorizationId("?authorization_id=valid_identifier-123"), "valid_identifier-123");
  assert.equal(authorizationId("?authorization_id=%3Cscript%3E"), "");
  assert.equal(authorizationId(""), "");
});

test("normalizes scopes and rejects unsafe redirects", () => {
  assert.deepEqual(requestedScopes("openid profile openid"), ["openid", "profile"]);
  assert.equal(
    safeAuthorizationRedirect("https://trident-ai.org/api/v1/session/callback?code=test", "https://trident-ai.org"),
    "https://trident-ai.org/api/v1/session/callback?code=test",
  );
  assert.throws(() => safeAuthorizationRedirect("https://attacker.test/callback", "https://trident-ai.org"));
  assert.throws(() => safeAuthorizationRedirect("https://trident-ai.org/wrong", "https://trident-ai.org"));
});
