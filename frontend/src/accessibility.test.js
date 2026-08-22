import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const root = new URL("../", import.meta.url);

test("document metadata identifies the French TRIDENT AI entry", () => {
  const html = readFileSync(new URL("index.html", root), "utf8");
  assert.match(html, /<html lang="fr">/);
  assert.match(html, /<meta name="viewport"/);
  assert.match(html, /<title>TRIDENT AI<\/title>/);
});

test("Workspace shell retains landmark and current-page semantics", () => {
  const layout = readFileSync(new URL("src/app/layout/MainLayout.jsx", root), "utf8");
  const sidebar = readFileSync(new URL("src/components/Sidebar.jsx", root), "utf8");
  assert.match(layout, /<main className="main-content">/);
  assert.match(sidebar, /<aside[^>]+aria-label=/);
  assert.match(sidebar, /<nav className=/);
  assert.match(sidebar, /aria-current=/);
});

test("current product navigation exposes Nova without Genesis presentation classes", () => {
  const registry = readFileSync(new URL("src/app/modules/registry.jsx", root), "utf8");
  const home = readFileSync(new URL("src/features/home/WorkspaceHome.jsx", root), "utf8");
  const workspaceStyles = readFileSync(new URL("src/styles/workspaces.css", root), "utf8");
  assert.match(registry, /id: "conversations", label: "Nova"/);
  assert.doesNotMatch(home, /genesis-/i);
  assert.doesNotMatch(workspaceStyles, /\.genesis-/i);
});

test("mobile Workspace dialog supports modal and keyboard-close semantics", () => {
  const selector = readFileSync(new URL("src/components/workspace/MobileWorkspaceSelector.jsx", root), "utf8");
  assert.match(selector, /role="dialog"/);
  assert.match(selector, /aria-modal="true"/);
  assert.match(selector, /event\.key === "Escape"/);
});

test("entry failures are announced and controls use native buttons", () => {
  const entry = readFileSync(new URL("src/features/session/EntryExperience.jsx", root), "utf8");
  assert.match(entry, /role="alert"/);
  assert.match(entry, /type="button"/);
  assert.doesNotMatch(entry, /onClick=\{[^}]+\}[^>]*role="button"/);
});

test("command and product onboarding dialogs are keyboard dismissable", () => {
  const command = readFileSync(new URL("src/components/command/CommandPalette.jsx", root), "utf8");
  const onboarding = readFileSync(new URL("src/features/onboarding/ProductOnboarding.jsx", root), "utf8");
  for (const surface of [command, onboarding]) {
    assert.match(surface, /role="dialog"/);
    assert.match(surface, /aria-modal="true"/);
    assert.match(surface, /event\.key/);
  }
  assert.match(command, /inputRef\.current\?\.focus/);
  assert.match(onboarding, /closeRef\.current\?\.focus/);
});
