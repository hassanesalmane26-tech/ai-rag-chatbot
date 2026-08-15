import { useCallback, useEffect, useRef, useState } from "react";
import { MessageSquarePlus, Send } from "lucide-react";
import useWorkspaceContext from "../../hooks/useWorkspaceContext";
import { createConversation, getConversation, listConversations, sendWorkspaceMessage } from "../../services/api";

export default function ConversationsView() {
  const { activeWorkspaceId } = useWorkspaceContext();
  const [conversations, setConversations] = useState([]);
  const [active, setActive] = useState(null);
  const [text, setText] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const activeWorkspaceRef = useRef(activeWorkspaceId);
  const listRequestRef = useRef(0);
  const detailRequestRef = useRef(0);

  useEffect(() => {
    activeWorkspaceRef.current = activeWorkspaceId;
  }, [activeWorkspaceId]);

  const refresh = useCallback(async () => {
    if (!activeWorkspaceId) {
      setConversations([]);
      setActive(null);
      return;
    }
    const request = ++listRequestRef.current;
    const values = await listConversations(activeWorkspaceId);
    if (request !== listRequestRef.current || activeWorkspaceRef.current !== activeWorkspaceId) return;
    setConversations(values);
    setActive((current) => current?.workspace_id === activeWorkspaceId ? current : null);
  }, [activeWorkspaceId]);

  const select = useCallback(async (conversation) => {
    if (!activeWorkspaceId) return;
    const request = ++detailRequestRef.current;
    try {
      const detail = await getConversation(activeWorkspaceId, conversation.id);
      if (request !== detailRequestRef.current || activeWorkspaceRef.current !== activeWorkspaceId) return;
      setActive(detail);
      setError("");
    } catch (err) {
      if (request === detailRequestRef.current && activeWorkspaceRef.current === activeWorkspaceId) setError(err.message);
    }
  }, [activeWorkspaceId]);

  useEffect(() => {
    setActive(null);
    setError("");
    refresh().catch((err) => {
      if (activeWorkspaceRef.current === activeWorkspaceId) setError(err.message);
    });
    return () => {
      listRequestRef.current += 1;
      detailRequestRef.current += 1;
    };
  }, [activeWorkspaceId, refresh]);

  async function addConversation() {
    const workspaceId = activeWorkspaceId;
    if (!workspaceId) return;
    try {
      const created = await createConversation(workspaceId);
      if (activeWorkspaceRef.current !== workspaceId) return;
      setConversations((items) => [created, ...items]);
      await select(created);
    } catch (err) {
      if (activeWorkspaceRef.current === workspaceId) setError(err.message);
    }
  }

  async function submit(event) {
    event.preventDefault();
    if (!text.trim() || !active || loading || !activeWorkspaceId) return;
    const workspaceId = activeWorkspaceId;
    const conversationId = active.id;
    const content = text.trim();
    const pendingId = `pending-${Date.now()}`;
    setText("");
    setLoading(true);
    setError("");
    setActive((current) => current?.id === conversationId ? {
      ...current,
      messages: [...current.messages, { id: pendingId, role: "user", content, citations: [] }],
    } : current);
    try {
      const reply = await sendWorkspaceMessage(workspaceId, conversationId, content);
      if (activeWorkspaceRef.current !== workspaceId) return;
      setActive((current) => current?.id === conversationId ? {
        ...current,
        messages: [...current.messages.filter((message) => message.id !== pendingId), reply],
      } : current);
      refresh().catch(() => {});
    } catch (err) {
      if (activeWorkspaceRef.current === workspaceId) {
        setError(err.message);
        setActive((current) => current?.id === conversationId ? {
          ...current,
          messages: current.messages.filter((message) => message.id !== pendingId),
        } : current);
      }
    } finally {
      if (activeWorkspaceRef.current === workspaceId) setLoading(false);
    }
  }

  return <section className="conversation-layout">
    <aside className="conversation-list">
      <div><h2>Conversations</h2><button type="button" onClick={addConversation} aria-label="Nouvelle conversation"><MessageSquarePlus size={18} /></button></div>
      {conversations.length === 0 ? <p>Créez une première conversation.</p> : conversations.map((conversation) => <button type="button" key={conversation.id} className={active?.id === conversation.id ? "active" : ""} aria-pressed={active?.id === conversation.id} onClick={() => select(conversation)}>{conversation.title}</button>)}
    </aside>
    <section className="conversation-panel">
      {active ? <>
        <header><span>CONVERSATION ACTIVE</span><h2>{active.title}</h2></header>
        <div className="message-list">{active.messages.length === 0 && <p className="empty-state">Posez votre première question à Nova.</p>}{active.messages.map((message) => <article key={message.id} className={`workspace-message ${message.role}`}><span>{message.role === "user" ? "Vous" : "NOVA"}</span><p>{message.content}</p>{message.citations?.length > 0 && <div className="citations">{message.citations.map((citation, index) => <small key={`${citation.document_id}-${index}`}>Source · {citation.document_name}</small>)}</div>}</article>)}{loading && <article className="workspace-message assistant"><span>NOVA</span><p>Analyse du Workspace…</p></article>}</div>
        {error && <p className="inline-error" role="alert">{error}</p>}
        <form className="message-composer" onSubmit={submit}><input aria-label="Message à Nova" value={text} onChange={(event) => setText(event.target.value)} placeholder="Interrogez ce Workspace…" disabled={loading} /><button type="submit" aria-label="Envoyer le message" disabled={loading || !text.trim()}><Send size={18} /></button></form>
      </> : <div className="empty-state"><h2>Vos conversations</h2><p>Créez une conversation pour commencer à travailler avec ce Workspace.</p>{error && <p className="inline-error" role="alert">{error}</p>}<button type="button" onClick={addConversation}>Nouvelle conversation</button></div>}
    </section>
  </section>;
}
