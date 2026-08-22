import { useCallback, useEffect, useRef, useState } from "react";
import { createConversation, getConversation, listConversations, sendWorkspaceMessage } from "../../services/api.js";
import {
  acceptsWorkspaceResult,
  appendOptimisticMessage,
  reconcileFailedConversation,
  reconcileSuccessfulMessages,
} from "./chatConversationState.js";

export default function useWorkspaceConversations(workspaceId) {
  const [conversations, setConversations] = useState([]);
  const [activeConversation, setActiveConversationState] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [sendingConversationId, setSendingConversationId] = useState(null);
  const workspaceRef = useRef(workspaceId);
  const activeConversationIdRef = useRef(null);
  const listRequestRef = useRef(0);
  const detailRequestRef = useRef(0);

  const setActiveConversation = useCallback((conversation) => {
    activeConversationIdRef.current = conversation?.id ?? null;
    setActiveConversationState(conversation);
  }, []);

  useEffect(() => {
    workspaceRef.current = workspaceId;
    listRequestRef.current += 1;
    detailRequestRef.current += 1;
    setConversations([]);
    setActiveConversation(null);
    setSendingConversationId(null);
    setLoading(true);
    setCreating(false);
    setError("");
  }, [workspaceId, setActiveConversation]);

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

  const selectConversation = useCallback(async (conversation) => {
    if (!workspaceId) return;
    const request = ++detailRequestRef.current;
    setActiveConversation(null);
    try {
      const detail = await getConversation(workspaceId, conversation.id);
      if (request !== detailRequestRef.current || !acceptsWorkspaceResult(workspaceRef.current, workspaceId)) return;
      setActiveConversation(detail);
      setError("");
    } catch (err) {
      if (request === detailRequestRef.current && workspaceRef.current === workspaceId) setError(err.message);
    }
  }, [workspaceId, setActiveConversation]);

  useEffect(() => {
    if (!workspaceId) return undefined;
    refresh().catch((err) => {
      if (acceptsWorkspaceResult(workspaceRef.current, workspaceId)) setError(err.message);
    });
    return () => {
      listRequestRef.current += 1;
      detailRequestRef.current += 1;
    };
  }, [workspaceId, refresh]);

  const addConversation = useCallback(async () => {
    if (!workspaceId || creating) return;
    setCreating(true);
    setError("");
    try {
      const created = await createConversation(workspaceId);
      if (!acceptsWorkspaceResult(workspaceRef.current, workspaceId)) return;
      setConversations((items) => [created, ...items]);
      await selectConversation(created);
    } catch (err) {
      if (acceptsWorkspaceResult(workspaceRef.current, workspaceId)) setError(err.message);
    } finally {
      if (acceptsWorkspaceResult(workspaceRef.current, workspaceId)) setCreating(false);
    }
  }, [workspaceId, creating, selectConversation]);

  const sendMessage = useCallback(async (content) => {
    const conversationId = activeConversationIdRef.current;
    if (!workspaceId || !conversationId || !content.trim() || sendingConversationId === conversationId) return false;
    const pendingId = `pending-${Date.now()}`;
    setSendingConversationId(conversationId);
    setError("");
    setActiveConversationState((current) => current?.id === conversationId ? {
      ...current,
      messages: appendOptimisticMessage(current.messages, pendingId, content.trim()),
    } : current);
    try {
      const reply = await sendWorkspaceMessage(workspaceId, conversationId, content.trim());
      if (!acceptsWorkspaceResult(workspaceRef.current, workspaceId) || activeConversationIdRef.current !== conversationId) return true;
      setActiveConversationState((current) => current?.id === conversationId ? {
        ...current,
        messages: reconcileSuccessfulMessages(current.messages, pendingId, reply),
      } : current);
      refresh().catch(() => {});
      return true;
    } catch (err) {
      if (acceptsWorkspaceResult(workspaceRef.current, workspaceId) && activeConversationIdRef.current === conversationId) {
        // The user turn may already be durable; reload it instead of hiding backend truth.
        const detail = await getConversation(workspaceId, conversationId).catch(() => null);
        if (acceptsWorkspaceResult(workspaceRef.current, workspaceId) && activeConversationIdRef.current === conversationId) {
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
      if (acceptsWorkspaceResult(workspaceRef.current, workspaceId)) setSendingConversationId((current) => current === conversationId ? null : current);
    }
  }, [workspaceId, sendingConversationId, refresh]);

  return {
    conversations,
    activeConversation,
    error,
    loading,
    creating,
    isSending: sendingConversationId === activeConversation?.id,
    refresh,
    selectConversation,
    addConversation,
    sendMessage,
  };
}
