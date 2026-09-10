import { useEffect, useRef, useState } from "react";
import { ArrowUpRight, BookOpen, Brain, Files, LoaderCircle, MessageSquarePlus, RefreshCw, Send } from "lucide-react";
import useWorkspaceConversations from "./useWorkspaceConversations";
import { uniqueDocumentCitations } from "./chatConversationState";
import useWorkspaceContext from "../../hooks/useWorkspaceContext";
import TridentMark from "../../components/visual/TridentMark";
import NovaContextRail from "./NovaContextRail";

export default function ConversationsView({ workspaceId }) {
  const [text, setText] = useState("");
  const [showContextRail, setShowContextRail] = useState(false);
  const { activeWorkspace, novaConversationRequest, novaConversationTarget, setNovaActiveConversationId } = useWorkspaceContext();
  const { conversations, activeConversation, error, loading, creating, isSending, refresh, selectConversation, addConversation, sendMessage } = useWorkspaceConversations(workspaceId);
  const handledNovaRequest = useRef(0);
  const handledNovaTarget = useRef(0);

  useEffect(() => {
    const media = window.matchMedia("(min-width: 1440px)");
    const synchronize = () => setShowContextRail(media.matches);
    synchronize();
    media.addEventListener("change", synchronize);
    return () => media.removeEventListener("change", synchronize);
  }, []);

  useEffect(() => {
    if (!novaConversationRequest || novaConversationRequest === handledNovaRequest.current) return;
    handledNovaRequest.current = novaConversationRequest;
    addConversation();
  }, [novaConversationRequest, addConversation]);

  useEffect(() => {
    if (!novaConversationTarget || novaConversationTarget.request === handledNovaTarget.current) return;
    handledNovaTarget.current = novaConversationTarget.request;
    selectConversation(novaConversationTarget.conversation);
  }, [novaConversationTarget, selectConversation]);

  useEffect(() => {
    setNovaActiveConversationId(activeConversation?.id ?? null);
  }, [activeConversation?.id, setNovaActiveConversationId]);

  async function submit(event) {
    event.preventDefault();
    if (!text.trim() || creating || isSending) return;
    if (!activeConversation) {
      const created = await addConversation();
      if (!created) return;
    }
    const sent = await sendMessage(text);
    if (sent) setText("");
  }

  return <section className="conversation-layout">
    <aside className="conversation-list">
      <div><h2>Nova</h2><button type="button" onClick={addConversation} aria-label="Nouvelle conversation avec Nova" disabled={creating}>{creating ? <LoaderCircle className="spin" size={18} /> : <MessageSquarePlus size={18} />}</button></div>
      {loading ? <p className="conversation-list__state" aria-live="polite"><LoaderCircle className="spin" size={16} /> Chargement…</p> : conversations.length === 0 ? <p className="conversation-list__state">Commencez une première conversation avec Nova.</p> : conversations.map((conversation) => <button type="button" key={conversation.id} className={activeConversation?.id === conversation.id ? "active" : ""} aria-pressed={activeConversation?.id === conversation.id} onClick={() => selectConversation(conversation)}>{conversation.title}</button>)}
      {error && !activeConversation ? <button className="conversation-list__retry" type="button" onClick={() => refresh().catch(() => {})}><RefreshCw size={15} /> Réessayer</button> : null}
    </aside>
    <section className={`conversation-panel ${activeConversation ? "conversation-panel--active" : "conversation-panel--ready"}`} aria-label="Nova">
      {activeConversation ? <>
        <header><span>CONVERSATION ACTIVE</span><h2>{activeConversation.title}</h2></header>
        <div className="message-list">{activeConversation.messages.length === 0 && <p className="empty-state">Posez votre première question à Nova.</p>}{activeConversation.messages.map((message) => { const citations = uniqueDocumentCitations(message.citations); return <article key={message.id} className={`workspace-message ${message.role}`}><span>{message.role === "user" ? "VOUS" : "NOVA · WORKSPACE AI"}</span><p>{message.content}</p>{citations.length > 0 && <div className="citations" aria-label="Sources utilisées">{citations.map((citation) => <small key={citation.document_id || `${citation.document_name}:${citation.excerpt || ""}`}>Source · {citation.document_name}</small>)}</div>}</article>; })}{isSending && <article className="workspace-message assistant"><span>NOVA · WORKSPACE AI</span><p>Analyse du Workspace…</p></article>}</div>
        {error && <p className="inline-error" role="alert">{error}</p>}
      </> : <div className="nova-ready"><div className="nova-ready__field" aria-hidden="true"><i /><i /><i /></div><div className="nova-ready__identity"><div className="nova-ready__core"><i /><i /><i /><TridentMark /></div><span>NOVA · INTELLIGENCE DU WORKSPACE</span><h2>Bienvenue dans {activeWorkspace?.name || "votre Workspace"}</h2><p>Nova est prête à travailler avec le contexte autorisé de cet environnement.</p></div><div className="nova-ready__context" role="list" aria-label="Systèmes de contexte disponibles dans le Workspace"><span role="listitem"><BookOpen size={16} />Knowledge</span><span role="listitem"><Brain size={16} />Memory</span><span role="listitem"><Files size={16} />Fichiers</span></div><div className="nova-ready__suggestions" aria-label="Suggestions"><button type="button" onClick={() => setText("Que peux-tu m’aider à accomplir dans ce Workspace ?")}><span>Explorer ce Workspace</span><ArrowUpRight size={14} /></button><button type="button" onClick={() => setText("Résume le contexte disponible dans Knowledge.")}><span>Interroger Knowledge</span><ArrowUpRight size={14} /></button><button type="button" onClick={() => setText("Démarrons une nouvelle conversation.")}><span>Parler avec Nova</span><ArrowUpRight size={14} /></button></div>{error && <p className="inline-error" role="alert">{error}</p>}</div>}
      <form className="message-composer" onSubmit={submit}><span className="message-composer__mark" aria-hidden="true"><TridentMark /></span><input aria-label="Message à Nova" value={text} onChange={(event) => setText(event.target.value)} placeholder="Demandez à Nova…" disabled={isSending || creating} /><button type="submit" aria-label="Envoyer le message" disabled={isSending || creating || !text.trim()}>{creating || isSending ? <LoaderCircle className="spin" size={18} /> : <Send size={18} />}</button></form>
    </section>
    {showContextRail && <NovaContextRail workspace={activeWorkspace} workspaceId={workspaceId} />}
  </section>;
}
