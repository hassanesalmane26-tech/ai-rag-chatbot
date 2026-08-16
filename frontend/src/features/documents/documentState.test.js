import assert from "node:assert/strict";
import test from "node:test";
import {
  MAX_DOCUMENT_BYTES,
  acceptsDocumentResult,
  documentStatusLabel,
  formatDocumentSize,
  prependDocument,
  removeDocumentById,
  validateDocumentFile,
} from "./documentState.js";

test("rejects stale document results after a Workspace switch", () => {
  assert.equal(acceptsDocumentResult("workspace-b", "workspace-a"), false);
  assert.equal(acceptsDocumentResult("workspace-a", "workspace-a"), true);
});

test("validates supported, non-empty documents within the API limit", () => {
  assert.equal(validateDocumentFile({ name: "guide.PDF", size: 12 }), null);
  assert.equal(validateDocumentFile({ name: "notes.txt", size: MAX_DOCUMENT_BYTES }), null);
  assert.match(validateDocumentFile({ name: "archive.zip", size: 12 }), /Format/);
  assert.match(validateDocumentFile({ name: "vide.txt", size: 0 }), /vide/);
  assert.match(validateDocumentFile({ name: "large.docx", size: MAX_DOCUMENT_BYTES + 1 }), /20 Mo/);
});

test("updates the local collection without duplicates", () => {
  const initial = [{ id: "a" }, { id: "b", status: "processing" }];
  assert.deepEqual(prependDocument(initial, { id: "b", status: "indexed" }), [
    { id: "b", status: "indexed" },
    { id: "a" },
  ]);
  assert.deepEqual(removeDocumentById(initial, "a"), [{ id: "b", status: "processing" }]);
});

test("formats document metadata for human-readable cards", () => {
  assert.equal(formatDocumentSize(900), "900 o");
  assert.equal(formatDocumentSize(1536), "2 Ko");
  assert.equal(formatDocumentSize(1572864), "1.5 Mo");
  assert.equal(documentStatusLabel("indexed"), "Prêt pour Nova");
  assert.equal(documentStatusLabel("failed"), "Indexation échouée");
});
