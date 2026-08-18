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
