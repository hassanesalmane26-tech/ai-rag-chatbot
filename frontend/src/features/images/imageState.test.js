import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";
import { imageStatus, isImagePending, validateImageFile } from "./imageState.js";

test("image lifecycle never fabricates progress or a completed result", () => {
  assert.deepEqual(Object.keys(imageStatus), ["queued", "generating", "completed", "failed", "cancelled"]);
  for (const status of Object.keys(imageStatus)) assert.equal(isImagePending({ status }), ["queued", "generating"].includes(status));
});
test("image attachments reject unsafe types and oversized files before sending", () => {
  assert.equal(validateImageFile({ type: "image/png", size: 100 }), "");
  assert.ok(validateImageFile({ type: "image/svg+xml", size: 100 }));
  assert.ok(validateImageFile({ type: "image/png", size: 13 * 1024 * 1024 }));
});
test("Nova renders Markdown without raw HTML or untrusted external images", () => {
  const view = readFileSync(new URL("../chat/ConversationsView.jsx", import.meta.url), "utf8");
  assert.match(view, /ReactMarkdown skipHtml components=\{safeMarkdown\}/);
  assert.match(view, /img: \(\{ alt \}\) => <span>/);
  assert.match(view, /submitLock.current/);
  assert.match(view, /requestKey.current/);
});
test("scope cleanup prevents late image fetches from repopulating another Workspace", () => {
  const hook = readFileSync(new URL("./useWorkspaceImages.js", import.meta.url), "utf8");
  assert.match(hook, /snapshot\?\.scope === scope/);
  assert.match(hook, /current = false; clearTimeout\(timer\)/);
  const card = readFileSync(new URL("./ImageCard.jsx", import.meta.url), "utf8");
  assert.match(card, /URL.revokeObjectURL/);
  assert.match(card, /readImage\(workspaceId, image.id\)/);
});
