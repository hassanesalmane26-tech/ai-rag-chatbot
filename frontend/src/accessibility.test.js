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

test("entry failures are announced and controls use native buttons", () => {
  const entry = readFileSync(new URL("src/features/session/EntryExperience.jsx", root), "utf8");
  assert.match(entry, /role="alert"/);
  assert.match(entry, /type="button"/);
  assert.doesNotMatch(entry, /onClick=\{[^}]+\}[^>]*role="button"/);
});
