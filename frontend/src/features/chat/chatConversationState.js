export function appendOptimisticMessage(messages, pendingId, content) {
  return [...messages, { id: pendingId, role: "user", content, citations: [] }];
}

export function uniqueDocumentCitations(citations = []) {
  const seen = new Set();
  return citations.filter((citation) => {
    const identity = citation.document_id || `${citation.document_name}:${citation.excerpt || ""}`;
    if (seen.has(identity)) return false;
    seen.add(identity);
    return true;
  });
}

export function reconcileSuccessfulMessages(messages, pendingId, reply) {
  const { user_message: userMessage, ...assistantMessage } = reply;
  const persistedIds = new Set([userMessage?.id, assistantMessage.id].filter(Boolean));
  const retained = messages.filter((message) => message.id !== pendingId && !persistedIds.has(message.id));
  return [...retained, ...(userMessage ? [userMessage] : []), assistantMessage];
}

export function rollbackPendingMessage(messages, pendingId) {
  return messages.filter((message) => message.id !== pendingId);
}

export function reconcileFailedConversation(current, pendingId, persistedDetail, error) {
  return {
    activeConversation: persistedDetail ?? (current ? {
      ...current,
      messages: rollbackPendingMessage(current.messages, pendingId),
    } : null),
    error,
  };
}

export function acceptsWorkspaceResult(currentWorkspaceId, requestWorkspaceId) {
  return currentWorkspaceId === requestWorkspaceId;
}

export function acceptsConversationResult(
  currentWorkspaceId,
  requestWorkspaceId,
  currentConversationId,
  requestConversationId,
) {
  return acceptsWorkspaceResult(currentWorkspaceId, requestWorkspaceId)
    && currentConversationId === requestConversationId;
}

export function upsertRecentConversation(conversations, conversation) {
  if (!conversation?.id) return conversations;
  return [conversation, ...conversations.filter((item) => item.id !== conversation.id)]
    .sort((left, right) => {
      const dateDifference = Date.parse(right.updated_at || right.created_at || 0)
        - Date.parse(left.updated_at || left.created_at || 0);
      return dateDifference || right.id.localeCompare(left.id);
    });
}

export function activeConversationStorageKey(workspaceId) {
  return workspaceId ? `trident.ai.nova.active_conversation.${workspaceId}` : null;
}

export function runSingleFlight(ref, operation) {
  if (ref.current) return ref.current;
  const pending = Promise.resolve().then(operation).finally(() => {
    if (ref.current === pending) ref.current = null;
  });
  ref.current = pending;
  return pending;
}

export function conversationLifecycle({ workspaceId, activeConversation, creating, loadingConversation, sending, error }) {
  if (!workspaceId) return "unavailable";
  if (creating) return "creating";
  if (loadingConversation) return "messages_loading";
  if (sending) return "sending";
  if (error && activeConversation) return "send_failed";
  if (error) return "load_failed";
  if (activeConversation) return "ready";
  return "draft";
}
