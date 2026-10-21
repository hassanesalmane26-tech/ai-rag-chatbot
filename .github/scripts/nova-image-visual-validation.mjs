import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { mkdir, writeFile } from "node:fs/promises";
import { join, resolve } from "node:path";
import { pathToFileURL } from "node:url";

const root = resolve(new URL("../..", import.meta.url).pathname);
const frontend = join(root, "frontend");
const outputDir = process.env.TRIDENT_VISUAL_OUTPUT_DIR || join(root, "artifacts", "nova-image-visual");
const baseUrl = "http://127.0.0.1:4173";
const baseOrigin = new URL(baseUrl).origin;

const imageRecords = {
  "ws-completed": [
    { id: "completed-1", status: "completed" },
    { id: "queued-1", status: "queued" },
    { id: "failed-1", status: "failed" },
    { id: "completed-2", status: "completed" },
  ],
  "ws-empty": [
    { id: "queued-2", status: "queued" },
    { id: "failed-2", status: "failed" },
  ],
  "ws-loading": [],
  "ws-error": null,
  "ws-unavailable": null,
};

const workspaces = [
  { id: "ws-completed", name: "Workspace avec images terminées", description: "Données synthétiques du test navigateur." },
  { id: "ws-empty", name: "Workspace sans image terminée", description: "Données synthétiques du test navigateur." },
  { id: "ws-loading", name: "Workspace chargement", description: "Données synthétiques du test navigateur." },
  { id: "ws-error", name: "Workspace erreur", description: "Données synthétiques du test navigateur." },
  { id: "ws-unavailable", name: "Workspace indisponible", description: "Données synthétiques du test navigateur." },
];

const report = {
  status: "RUNNING",
  tested_commit: process.env.TRIDENT_TESTED_SHA || "local-uncommitted-test-harness",
  browser: null,
  data_policy: "All API data is synthetic and intercepted in the browser. No backend, provider, credentials, or production service is used.",
  scenarios: [],
  captures: [],
  blocked_external_requests: [],
  blocked_non_get_api_requests: [],
  unexpected_api_requests: [],
  page_errors: [],
  started_at_utc: new Date().toISOString(),
};

function envelope(data, meta = { pagination: { has_more: false } }) {
  return { data, meta };
}

async function fulfillJson(route, data, status = 200) {
  await route.fulfill({
    status,
    contentType: "application/json",
    body: JSON.stringify(status >= 400 ? { error: { message: "Synthetic API failure" } } : envelope(data)),
  });
}

function completedImageCount(workspaceId) {
  const records = imageRecords[workspaceId];
  return Array.isArray(records) ? records.filter((record) => record.status === "completed").length : null;
}

async function mockRequest(route, loadingEnabled) {
  const request = route.request();
  const url = new URL(request.url());

  if (url.origin !== baseOrigin) {
    report.blocked_external_requests.push({ origin: url.origin, path: url.pathname });
    await route.abort("blockedbyclient");
    return;
  }
  if (!url.pathname.startsWith("/api/")) {
    await route.continue();
    return;
  }
  if (request.method() !== "GET") {
    report.blocked_non_get_api_requests.push({ method: request.method(), path: url.pathname });
    await fulfillJson(route, null, 405);
    return;
  }

  if (url.pathname === "/api/v1/session/configuration") {
    await fulfillJson(route, { enabled: true });
    return;
  }
  if (url.pathname === "/api/v1/session") {
    await fulfillJson(route, {
      user: { id: "synthetic-user", display_name: "Synthetic User" },
      organizations: [{ id: "synthetic-org", name: "Synthetic Organization", role: "owner", workspaces: [] }],
      active_organization_id: "synthetic-org",
    });
    return;
  }
  if (url.pathname === "/api/v1/workspaces") {
    await fulfillJson(route, workspaces);
    return;
  }

  const overviewMatch = url.pathname.match(/^\/api\/v1\/workspaces\/([^/]+)\/overview$/);
  if (overviewMatch) {
    const workspaceId = overviewMatch[1];
    if (workspaceId === "ws-loading" && loadingEnabled()) {
      await new Promise((resolveDelay) => setTimeout(resolveDelay, 1600));
    }
    if (workspaceId === "ws-error") {
      report.overview_responses ||= [];
      report.overview_responses.push({ workspace_id: workspaceId, status: 503, synthetic_completed_count: null });
      await fulfillJson(route, null, 503);
      return;
    }
    const count = completedImageCount(workspaceId);
    report.overview_responses ||= [];
    report.overview_responses.push({ workspace_id: workspaceId, status: 200, synthetic_completed_count: count });
    await fulfillJson(route, {
      metrics: { conversations: 0, documents: 0, messages: 0, memories: 0, images: count },
    });
    return;
  }

  if (/^\/api\/v1\/workspaces\/[^/]+\/activity$/.test(url.pathname)
    || /^\/api\/v1\/workspaces\/[^/]+\/conversations$/.test(url.pathname)
    || /^\/api\/v1\/workspaces\/[^/]+\/images$/.test(url.pathname)) {
    await fulfillJson(route, []);
    return;
  }
  if (/^\/api\/v1\/workspaces\/[^/]+\/images\/capability$/.test(url.pathname)) {
    await fulfillJson(route, { available: false, reason: "synthetic_disabled" });
    return;
  }

  report.unexpected_api_requests.push({ method: request.method(), path: url.pathname });
  await fulfillJson(route, null, 404);
}

async function makePage(browser, { width, height, mobile = false, loadingEnabled = () => false }) {
  const context = await browser.newContext({
    viewport: { width, height },
    deviceScaleFactor: 1,
    isMobile: mobile,
    hasTouch: mobile,
    serviceWorkers: "block",
  });
  await context.addInitScript(() => {
    localStorage.setItem("trident.ai.active_workspace_id", "ws-completed");
    localStorage.setItem("trident.ai.product_onboarding.synthetic-user", "complete");
  });
  await context.route("**/*", (route) => mockRequest(route, loadingEnabled));
  const page = await context.newPage();
  page.on("pageerror", (error) => report.page_errors.push(error.message));
  await page.goto(baseUrl, { waitUntil: "domcontentloaded" });
  await page.getByRole("heading", { name: "Workspace avec images terminées" }).waitFor({ timeout: 15000 });
  await openHome(page);
  return { context, page };
}

async function openHome(page) {
  const sidebarHome = page.getByRole("button", { name: "Accueil", exact: true }).first();
  if (await sidebarHome.isVisible().catch(() => false)) {
    await sidebarHome.click();
  } else {
    await page.getByRole("button", { name: "Ouvrir le menu système TRIDENT" }).click();
    await page.getByRole("dialog").getByRole("button", { name: "Accueil", exact: true }).click();
  }
  await page.locator(".workspace-home").waitFor({ timeout: 10000 });
}

async function assertImageMetric(page, expected) {
  await page.waitForFunction((value) => {
    const label = [...document.querySelectorAll(".metric-grid--v1 .metric-card span")]
      .find((element) => element.textContent?.trim() === "Images créées");
    return label?.closest(".metric-card")?.querySelector("strong")?.textContent?.trim() === value;
  }, expected, { timeout: 8000 });
}

function pngDimensions(buffer) {
  return { width: buffer.readUInt32BE(16), height: buffer.readUInt32BE(20) };
}

async function capture(page, name, width, height) {
  const path = join(outputDir, name);
  const buffer = await page.screenshot({ path, fullPage: false, animations: "disabled" });
  const dimensions = pngDimensions(buffer);
  assert.deepEqual(dimensions, { width, height }, `Unexpected screenshot size for ${name}`);
  report.captures.push({ file: name, ...dimensions });
}

async function selectWorkspace(page, name) {
  await page.locator(".sidebar .workspace-card").filter({ hasText: name }).click();
  await page.getByRole("heading", { name }).waitFor({ timeout: 5000 });
  await openHome(page);
}

function pass(name, evidence) {
  report.scenarios.push({ name, result: "PASS", evidence });
}

async function waitForPreview(server) {
  const deadline = Date.now() + 30000;
  while (Date.now() < deadline) {
    if (server.exitCode !== null) throw new Error(`Vite preview exited early with ${server.exitCode}`);
    try {
      const response = await fetch(baseUrl);
      if (response.ok) return;
    } catch {
      await new Promise((resolveDelay) => setTimeout(resolveDelay, 250));
    }
  }
  throw new Error("Timed out waiting for the local Vite preview.");
}

async function main() {
  await mkdir(outputDir, { recursive: true });
  const vite = join(frontend, "node_modules", "vite", "bin", "vite.js");
  const server = spawn(process.execPath, [vite, "preview", "--host", "127.0.0.1", "--port", "4173", "--strictPort"], {
    cwd: frontend,
    stdio: "ignore",
  });
  let browser;
  const contexts = [];
  let loadingEnabled = false;

  try {
    await waitForPreview(server);
    const modulePath = process.env.PLAYWRIGHT_MODULE || join(frontend, "node_modules", "playwright", "index.mjs");
    const { chromium } = await import(pathToFileURL(modulePath).href);
    browser = await chromium.launch({ headless: true });
    report.browser = `Chromium ${browser.version()}`;

    const desktop = await makePage(browser, { width: 1440, height: 900, loadingEnabled: () => loadingEnabled });
    contexts.push(desktop.context);
    const { page } = desktop;

    await assertImageMetric(page, "2");
    await capture(page, "workspace-home-desktop-1440x900.png", 1440, 900);
    pass("Completed image count and exclusions", "Two completed synthetic artifacts are counted; one queued and one failed artifact are excluded by the synthetic aggregate fixture.");

    await selectWorkspace(page, "Workspace sans image terminée");
    await assertImageMetric(page, "0");
    pass("Workspace with no completed images", "Queued and failed synthetic artifacts produce a displayed count of 0.");

    await selectWorkspace(page, "Workspace avec images terminées");
    await assertImageMetric(page, "2");
    pass("Workspace isolation", "Switching from the zero-count Workspace back to the completed-image Workspace restores only its count of 2.");

    loadingEnabled = true;
    await selectWorkspace(page, "Workspace chargement");
    await page.locator('.metric-grid--v1[aria-busy="true"]').waitFor({ timeout: 5000 });
    await assertImageMetric(page, "…");
    await capture(page, "workspace-home-loading.png", 1440, 900);
    pass("Loading state", "Delayed synthetic overview displays an ellipsis and marks the metric grid busy.");
    await assertImageMetric(page, "0");
    loadingEnabled = false;

    await selectWorkspace(page, "Workspace erreur");
    await page.locator('.workspace-home .inline-error[role="alert"]').waitFor({ timeout: 5000 });
    await assertImageMetric(page, "—");
    await capture(page, "workspace-home-error.png", 1440, 900);
    pass("Overview error state", "Synthetic HTTP 503 displays an unavailable metric and the existing retry alert.");

    await selectWorkspace(page, "Workspace indisponible");
    await assertImageMetric(page, "—");
    assert.equal(await page.locator('.workspace-home .inline-error[role="alert"]').count(), 0);
    await capture(page, "workspace-home-unavailable.png", 1440, 900);
    pass("Unavailable count state", "Successful synthetic response with a null count displays — without a request-error alert.");

    const tablet = await makePage(browser, { width: 1024, height: 768, mobile: true });
    contexts.push(tablet.context);
    await assertImageMetric(tablet.page, "2");
    await capture(tablet.page, "workspace-home-ipad-landscape-1024x768.png", 1024, 768);
    pass("iPad landscape rendering", "Workspace Home rendered in Chromium with a 1024×768 touch viewport.");

    const mobile = await makePage(browser, { width: 390, height: 844, mobile: true });
    contexts.push(mobile.context);
    await assertImageMetric(mobile.page, "2");
    await capture(mobile.page, "workspace-home-mobile-390x844.png", 390, 844);
    pass("Mobile rendering", "Workspace Home rendered in Chromium with a 390×844 touch viewport.");

    assert.deepEqual(report.blocked_non_get_api_requests, [], "The app attempted a non-GET API request; all mutations must stay disabled in this test.");
    assert.deepEqual(report.unexpected_api_requests, [], "The app made an API request not covered by synthetic fixtures.");
    assert.deepEqual(report.page_errors, [], "The browser reported an uncaught page error.");
    report.status = "PASS";
  } finally {
    for (const context of contexts) await context.close().catch(() => {});
    await browser?.close().catch(() => {});
    if (server.exitCode === null) {
      const exited = new Promise((resolveExit) => server.once("exit", resolveExit));
      server.kill("SIGTERM");
      await Promise.race([exited, new Promise((resolveDelay) => setTimeout(resolveDelay, 2000))]);
    }
  }
}

await mkdir(outputDir, { recursive: true });
try {
  await main();
} catch (error) {
  report.status = "FAIL";
  report.error = error instanceof Error ? `${error.name}: ${error.message}` : String(error);
  process.exitCode = 1;
} finally {
  report.finished_at_utc = new Date().toISOString();
  const summary = [
    `# PR #1 Nova Images visual validation: ${report.status}`,
    "",
    `- Tested commit: \`${report.tested_commit}\``,
    `- Browser: ${report.browser || "not launched"}`,
    "- Data: synthetic API fixtures only; requests outside the loopback preview are blocked.",
    "- Provider calls: 0; API mutations: blocked.",
    "",
    "## Scenarios",
    "",
    ...(report.scenarios.length
      ? report.scenarios.map((scenario) => `- **${scenario.result}** — ${scenario.name}: ${scenario.evidence || scenario.workspace_id}`)
      : ["- No browser scenarios completed."]),
    "",
    "## Captures",
    "",
    ...(report.captures.length
      ? report.captures.map((captureItem) => `- \`${captureItem.file}\` — ${captureItem.width}×${captureItem.height}`)
      : ["- No screenshots were produced."]),
    "",
    `- Blocked external requests: ${report.blocked_external_requests.length}`,
    `- Blocked non-GET API requests: ${report.blocked_non_get_api_requests.length}`,
    ...(report.error ? ["", `## Failure`, "", `\`${report.error}\``] : []),
  ].join("\n");
  await writeFile(join(outputDir, "report.json"), `${JSON.stringify(report, null, 2)}\n`);
  await writeFile(join(outputDir, "summary.md"), `${summary}\n`);
}
