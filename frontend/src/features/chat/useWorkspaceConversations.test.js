import assert from "node:assert/strict";
import test from "node:test";

import {
  acceptsWorkspaceResult,
  appendOptimisticMessage,
  reconcileFailedConversation,
  reconcileSuccessfulMessages,
  rollbackPendingMessage,
} from "./chatConversationState.js";

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
