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
  assert.match(registry, /id: "home", label: "Accueil"/);
  assert.match(registry, /id: "files", label: "Fichiers"/);
  assert.match(registry, /id: "artifacts", label: "Artefacts"/);
  assert.match(registry, /id: "activity", label: "Activité"/);
  assert.match(registry, /id: "settings", label: "Paramètres"/);
  assert.doesNotMatch(home, /genesis-/i);
  assert.doesNotMatch(workspaceStyles, /\.genesis-/i);
});

test("mobile navigation is limited to four real modules and reserves its safe area", () => {
  const registry = readFileSync(new URL("src/app/modules/registry.jsx", root), "utf8");
  const sidebarStyles = readFileSync(new URL("src/styles/sidebar.css", root), "utf8");
  const layoutStyles = readFileSync(new URL("src/styles/layout.css", root), "utf8");
  assert.equal((registry.match(/mobile: true/g) || []).length, 4);
  assert.match(sidebarStyles, /menu-item:not\(\.menu-item--mobile\)/);
  assert.match(sidebarStyles, /env\(safe-area-inset-bottom\)/);
  assert.match(layoutStyles, /scroll-padding-bottom:var\(--layout-bottom-nav-offset\)/);
});

test("the definitive shell uses real status and lightweight environmental layers", () => {
  const home = readFileSync(new URL("src/features/home/WorkspaceHome.jsx", root), "utf8");
  const environment = readFileSync(new URL("src/components/visual/VisualEnvironment.jsx", root), "utf8");
  const environmentStyles = readFileSync(new URL("src/styles/animations.css", root), "utf8");
  assert.match(home, /overviewState === "ready"/);
  assert.doesNotMatch(home, /Contexte serveur actif/);
  assert.match(environment, /trident-environment__portal/);
  assert.match(environment, /trident-environment__floor/);
  assert.match(environmentStyles, /prefers-reduced-motion:reduce/);
});

test("tablet and landscape phone shells have explicit responsive strategies", () => {
  const styles = readFileSync(new URL("src/styles/definitive.css", root), "utf8");
  assert.match(styles, /min-width:761px\) and \(max-width:1024px\) and \(min-height:501px/);
  assert.match(styles, /--layout-sidebar-width:82px/);
  assert.match(styles, /orientation:landscape\) and \(max-width:950px\) and \(max-height:500px/);
  assert.match(styles, /grid-template-columns:repeat\(4,minmax\(0,1fr\)\)/);
  assert.match(styles, /env\(safe-area-inset-right\)/);
});

test("mobile Workspace dialog supports modal and keyboard-close semantics", () => {
  const selector = readFileSync(new URL("src/components/workspace/MobileWorkspaceSelector.jsx", root), "utf8");
  assert.match(selector, /role="dialog"/);
  assert.match(selector, /aria-modal="true"/);
  assert.match(selector, /useModalFocus/);
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
  const modalFocus = readFileSync(new URL("src/hooks/useModalFocus.js", root), "utf8");
  for (const surface of [command, onboarding]) {
    assert.match(surface, /role="dialog"/);
    assert.match(surface, /aria-modal="true"/);
    assert.match(surface, /useModalFocus/);
  }
  assert.match(modalFocus, /event\.key === "Escape"/);
  assert.match(modalFocus, /event\.key !== "Tab"/);
  assert.match(modalFocus, /previousFocus/);
});
