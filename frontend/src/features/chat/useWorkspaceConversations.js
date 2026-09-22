import { useCallback, useEffect, useRef, useState } from "react";
import { createConversation, createImage, getConversation, listConversations, sendWorkspaceMessage } from "../../services/api.js";
import {
  acceptsWorkspaceResult,
  acceptsConversationResult,
  activeConversationStorageKey,
  appendOptimisticMessage,
  conversationLifecycle,
  reconcileFailedConversation,
  reconcileSuccessfulMessages,
  runSingleFlight,
  upsertRecentConversation,
} from "./chatConversationState.js";

function readPersistedConversationId(workspaceId) {
  const key = activeConversationStorageKey(workspaceId);
  if (!key) return null;
  try {
    return window.localStorage.getItem(key);
  } catch {
    return null;
  }
}

function persistConversationId(workspaceId, conversationId) {
  const key = activeConversationStorageKey(workspaceId);
  if (!key) return;
  try {
    if (conversationId) window.localStorage.setItem(key, conversationId);
    else window.localStorage.removeItem(key);
  } catch {
    // Conversation persistence is a client preference, never authorization.
  }
}

export default function useWorkspaceConversations(workspaceId) {
  const [conversations, setConversations] = useState([]);
  const [activeConversation, setActiveConversationState] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [loadingConversationId, setLoadingConversationId] = useState(null);
  const [sendingConversationId, setSendingConversationId] = useState(null);
  const workspaceRef = useRef(workspaceId);
  const activeConversationIdRef = useRef(null);
  const listRequestRef = useRef(0);
  const detailRequestRef = useRef(0);
  const creationPromiseRef = useRef(null);
  const sendingRef = useRef(new Set());

  const setActiveConversation = useCallback((conversation, boundWorkspaceId = workspaceRef.current) => {
    activeConversationIdRef.current = conversation?.id ?? null;
    setActiveConversationState(conversation);
    persistConversationId(boundWorkspaceId, conversation?.id ?? null);
  }, []);

  useEffect(() => {
    workspaceRef.current = workspaceId;
    listRequestRef.current += 1;
    detailRequestRef.current += 1;
    setConversations([]);
    activeConversationIdRef.current = null;
    setActiveConversationState(null);
    setSendingConversationId(null);
    creationPromiseRef.current = null;
    sendingRef.current.clear();
    setLoading(true);
    setCreating(false);
    setLoadingConversationId(null);
    setError("");
  }, [workspaceId]);

  const refresh = useCallback(async () => {
    if (!workspaceId) return [];
    const request = ++listRequestRef.current;
    setLoading(true);
    setError("");
    try {
      const values = await listConversations(workspaceId);
      if (request !== listRequestRef.current || !acceptsWorkspaceResult(workspaceRef.current, workspaceId)) return [];
      setConversations(values);
      return values;
    } finally {
      if (request === listRequestRef.current && acceptsWorkspaceResult(workspaceRef.current, workspaceId)) setLoading(false);
    }
  }, [workspaceId]);

  const selectConversation = useCallback(async (conversation, { restoring = false } = {}) => {
    if (!workspaceId) return;
    const request = ++detailRequestRef.current;
    activeConversationIdRef.current = conversation.id;
    setActiveConversationState(null);
    setLoadingConversationId(conversation.id);
    if (!restoring) persistConversationId(workspaceId, conversation.id);
    try {
      const detail = await getConversation(workspaceId, conversation.id);
      if (request !== detailRequestRef.current
        || !acceptsConversationResult(workspaceRef.current, workspaceId, activeConversationIdRef.current, conversation.id)) return;
      setActiveConversation(detail, workspaceId);
      setError("");
      return detail;
    } catch (err) {
      if (request === detailRequestRef.current
        && acceptsConversationResult(workspaceRef.current, workspaceId, activeConversationIdRef.current, conversation.id)) {
        setActiveConversation(null, workspaceId);
        setError(err.status === 401 || err.status === 403 || err.status === 404
          ? "Cette conversation n’est plus disponible dans ce Workspace."
          : err.message);
      }
      return null;
    } finally {
      if (request === detailRequestRef.current && workspaceRef.current === workspaceId) {
        setLoadingConversationId((current) => current === conversation.id ? null : current);
      }
    }
  }, [workspaceId, setActiveConversation]);

  useEffect(() => {
    if (!workspaceId) return undefined;
    refresh().then((values) => {
      if (!acceptsWorkspaceResult(workspaceRef.current, workspaceId)) return;
      const persistedId = readPersistedConversationId(workspaceId);
      if (persistedId && values.some((conversation) => conversation.id === persistedId)) {
        selectConversation({ id: persistedId }, { restoring: true }).catch(() => {});
      } else if (persistedId) {
        persistConversationId(workspaceId, null);
      }
    }).catch((err) => {
      if (acceptsWorkspaceResult(workspaceRef.current, workspaceId)) setError(err.message);
    });
    return () => {
      listRequestRef.current += 1;
      detailRequestRef.current += 1;
    };
  }, [workspaceId, refresh, selectConversation]);

  const addConversation = useCallback(() => {
    if (!workspaceId) return Promise.resolve(null);
    const requestWorkspaceId = workspaceId;
    return runSingleFlight(creationPromiseRef, async () => {
      setCreating(true);
      setError("");
      try {
        const created = await createConversation(requestWorkspaceId);
        if (!acceptsWorkspaceResult(workspaceRef.current, requestWorkspaceId)) return null;
        setConversations((items) => upsertRecentConversation(items, created));
        return await selectConversation(created);
      } catch (err) {
        if (acceptsWorkspaceResult(workspaceRef.current, requestWorkspaceId)) setError(err.message);
        return null;
      } finally {
        if (acceptsWorkspaceResult(workspaceRef.current, requestWorkspaceId)) setCreating(false);
      }
    });
  }, [workspaceId, selectConversation]);

  const sendMessage = useCallback(async (content, imageOptions = null) => {
    const conversationId = activeConversationIdRef.current;
    if (!workspaceId || !conversationId || !content.trim() || sendingRef.current.has(conversationId)) return false;
    const pendingId = `pending-${Date.now()}`;
    sendingRef.current.add(conversationId);
    setSendingConversationId(conversationId);
    setError("");
    setActiveConversationState((current) => current?.id === conversationId ? {
      ...current,
      messages: appendOptimisticMessage(current.messages, pendingId, content.trim()),
    } : current);
    try {
      let reply;
      let detail;
      if (imageOptions) {
        await createImage(workspaceId, conversationId, content.trim(), imageOptions);
        detail = await getConversation(workspaceId, conversationId);
      } else {
        reply = await sendWorkspaceMessage(workspaceId, conversationId, content.trim());
      }
      if (!acceptsConversationResult(workspaceRef.current, workspaceId, activeConversationIdRef.current, conversationId)) return true;
      setActiveConversationState((current) => current?.id === conversationId ? {
        ...current,
        messages: detail ? detail.messages : reconcileSuccessfulMessages(current.messages, pendingId, reply),
      } : current);
      refresh().catch(() => {});
      return true;
    } catch (err) {
      if (acceptsConversationResult(workspaceRef.current, workspaceId, activeConversationIdRef.current, conversationId)) {
        // The user turn may already be durable; reload it instead of hiding backend truth.
        const detail = await getConversation(workspaceId, conversationId).catch(() => null);
        if (acceptsConversationResult(workspaceRef.current, workspaceId, activeConversationIdRef.current, conversationId)) {
          setError(err.message);
          setActiveConversationState((current) => {
            if (current?.id !== conversationId) return current;
            const failure = reconcileFailedConversation(current, pendingId, detail, err.message);
            activeConversationIdRef.current = failure.activeConversation?.id ?? null;
            return failure.activeConversation;
          });
        }
      }
      return false;
    } finally {
      sendingRef.current.delete(conversationId);
      if (acceptsWorkspaceResult(workspaceRef.current, workspaceId)) setSendingConversationId((current) => current === conversationId ? null : current);
    }
  }, [workspaceId, refresh]);

  const startConversationWithMessage = useCallback(async (content, imageOptions = null) => {
    const created = activeConversationIdRef.current
      ? activeConversation
      : await addConversation();
    if (!created) return false;
    return sendMessage(content, imageOptions);
  }, [activeConversation, addConversation, sendMessage]);

  const lifecycle = conversationLifecycle({
    workspaceId,
    activeConversation,
    creating,
    loadingConversation: Boolean(loadingConversationId),
    sending: sendingConversationId === activeConversation?.id,
    error,
  });

  return {
    conversations,
    activeConversation,
    error,
    loading,
    creating,
    isSending: sendingConversationId === activeConversation?.id,
    isLoadingConversation: Boolean(loadingConversationId),
    refresh,
    selectConversation,
    addConversation,
    sendMessage,
    startConversationWithMessage,
    lifecycle,
  };
}
