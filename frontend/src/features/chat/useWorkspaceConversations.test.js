import assert from "node:assert/strict";
import test from "node:test";

import {
  acceptsWorkspaceResult,
  acceptsConversationResult,
  activeConversationStorageKey,
  appendOptimisticMessage,
  conversationLifecycle,
  reconcileFailedConversation,
  reconcileSuccessfulMessages,
  rollbackPendingMessage,
  runSingleFlight,
  uniqueDocumentCitations,
  upsertRecentConversation,
} from "./chatConversationState.js";

test("shows each cited document once while preserving distinct sources", () => {
  const result = uniqueDocumentCitations([
    { document_id: "doc-1", document_name: "guide.pdf", excerpt: "first" },
    { document_id: "doc-1", document_name: "guide.pdf", excerpt: "second" },
    { document_id: "doc-2", document_name: "notes.txt", excerpt: "third" },
  ]);
  assert.deepEqual(result.map((citation) => citation.document_id), ["doc-1", "doc-2"]);
});

test("adds an optimistic user message without changing persisted history", () => {
  const existing = [{ id: "old", role: "assistant", content: "Bonjour" }];
  const result = appendOptimisticMessage(existing, "pending-1", "Question");

  assert.deepEqual(existing, [{ id: "old", role: "assistant", content: "Bonjour" }]);
  assert.deepEqual(result.at(-1), {
    id: "pending-1", role: "user", content: "Question", citations: [],
  });
});

test("reconciles a successful turn with persisted user and assistant messages", () => {
  const messages = appendOptimisticMessage([], "pending-1", "Question");
  const reply = {
    id: "assistant-1",
    role: "assistant",
    content: "Réponse",
    citations: [],
    user_message: { id: "user-1", role: "user", content: "Question", citations: [] },
  };

  const result = reconcileSuccessfulMessages(messages, "pending-1", reply);

  assert.deepEqual(result.map(({ id, role }) => ({ id, role })), [
    { id: "user-1", role: "user" },
    { id: "assistant-1", role: "assistant" },
  ]);
  assert.equal(result[1].content, "Réponse");
  assert.equal("user_message" in result[1], false);
});

test("successful reconciliation removes stale duplicates by persisted identity", () => {
  const messages = [
    { id: "user-1", role: "user", content: "Question" },
    { id: "pending-1", role: "user", content: "Question" },
    { id: "assistant-1", role: "assistant", content: "Ancienne réponse" },
  ];
  const reply = {
    id: "assistant-1", role: "assistant", content: "Réponse persistée",
    user_message: { id: "user-1", role: "user", content: "Question" },
  };

  const result = reconcileSuccessfulMessages(messages, "pending-1", reply);

  assert.deepEqual(result.map((message) => message.id), ["user-1", "assistant-1"]);
  assert.equal(result[1].content, "Réponse persistée");
});

test("rolls back only the optimistic message when durable history cannot reload", () => {
  const messages = [
    { id: "persisted", role: "assistant", content: "Déjà présent" },
    { id: "pending-1", role: "user", content: "Question" },
  ];

  assert.deepEqual(rollbackPendingMessage(messages, "pending-1"), [messages[0]]);
});

test("keeps the backend truth and exposes the send error after a failed turn", () => {
  const current = {
    id: "conversation-1",
    messages: [{ id: "pending-1", role: "user", content: "Question" }],
  };
  const persistedDetail = {
    id: "conversation-1",
    messages: [{ id: "user-1", role: "user", content: "Question" }],
  };

  const result = reconcileFailedConversation(
    current, "pending-1", persistedDetail, "Service indisponible",
  );

  assert.equal(result.error, "Service indisponible");
  assert.deepEqual(result.activeConversation, persistedDetail);
});

test("rejects results from a workspace that is no longer active", () => {
  assert.equal(acceptsWorkspaceResult("workspace-b", "workspace-a"), false);
  assert.equal(acceptsWorkspaceResult("workspace-a", "workspace-a"), true);
});

test("rejects a late conversation response after rapid switching", () => {
  assert.equal(acceptsConversationResult("workspace-a", "workspace-a", "conversation-b", "conversation-a"), false);
  assert.equal(acceptsConversationResult("workspace-a", "workspace-a", "conversation-b", "conversation-b"), true);
  assert.equal(acceptsConversationResult("workspace-b", "workspace-a", "conversation-b", "conversation-b"), false);
});

test("keeps recent conversations unique and ordered by server timestamps", () => {
  const result = upsertRecentConversation([
    { id: "older", updated_at: "2026-01-01T00:00:00Z" },
    { id: "active", updated_at: "2026-01-02T00:00:00Z" },
  ], { id: "older", updated_at: "2026-01-03T00:00:00Z", title: "Updated" });
  assert.deepEqual(result.map((conversation) => conversation.id), ["older", "active"]);
  assert.equal(result[0].title, "Updated");
});

test("persists active conversation separately for each Workspace", () => {
  assert.equal(activeConversationStorageKey("workspace-a"), "trident.ai.nova.active_conversation.workspace-a");
  assert.equal(activeConversationStorageKey("workspace-b"), "trident.ai.nova.active_conversation.workspace-b");
  assert.equal(activeConversationStorageKey(null), null);
});

test("double submit shares one conversation creation operation", async () => {
  const ref = { current: null };
  let calls = 0;
  const operation = async () => {
    calls += 1;
    return { id: "conversation-1" };
  };
  const first = runSingleFlight(ref, operation);
  const second = runSingleFlight(ref, operation);
  assert.equal(first, second);
  assert.deepEqual(await first, { id: "conversation-1" });
  assert.equal(calls, 1);
  assert.equal(ref.current, null);
});

test("derives explicit Nova lifecycle states from real request state", () => {
  const base = { workspaceId: "workspace-a", activeConversation: null, creating: false, loadingConversation: false, sending: false, error: "" };
  assert.equal(conversationLifecycle(base), "draft");
  assert.equal(conversationLifecycle({ ...base, creating: true }), "creating");
  assert.equal(conversationLifecycle({ ...base, loadingConversation: true }), "messages_loading");
  assert.equal(conversationLifecycle({ ...base, activeConversation: { id: "conversation-a" } }), "ready");
  assert.equal(conversationLifecycle({ ...base, activeConversation: { id: "conversation-a" }, sending: true }), "sending");
  assert.equal(conversationLifecycle({ ...base, activeConversation: { id: "conversation-a" }, error: "offline" }), "send_failed");
  assert.equal(conversationLifecycle({ ...base, error: "missing" }), "load_failed");
  assert.equal(conversationLifecycle({ ...base, workspaceId: null }), "unavailable");
});
