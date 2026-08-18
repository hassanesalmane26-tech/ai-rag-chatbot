import { useState } from "react";
import { MessageSquarePlus, Send } from "lucide-react";
import useWorkspaceConversations from "./useWorkspaceConversations";
import { uniqueDocumentCitations } from "./chatConversationState";

export default function ConversationsView({ workspaceId }) {
  const [text, setText] = useState("");
  const { conversations, activeConversation, error, isSending, selectConversation, addConversation, sendMessage } = useWorkspaceConversations(workspaceId);

  async function submit(event) {
    event.preventDefault();
    if (!text.trim() || !activeConversation || isSending) return;
    const sent = await sendMessage(text);
    if (sent) setText("");
  }

  return <section className="conversation-layout">
    <aside className="conversation-list">
      <div><h2>Conversations</h2><button type="button" onClick={addConversation} aria-label="Nouvelle conversation"><MessageSquarePlus size={18} /></button></div>
      {conversations.length === 0 ? <p>Créez une première conversation.</p> : conversations.map((conversation) => <button type="button" key={conversation.id} className={activeConversation?.id === conversation.id ? "active" : ""} aria-pressed={activeConversation?.id === conversation.id} onClick={() => selectConversation(conversation)}>{conversation.title}</button>)}
    </aside>
    <section className="conversation-panel">
      {activeConversation ? <>
        <header><span>CONVERSATION ACTIVE</span><h2>{activeConversation.title}</h2></header>
        <div className="message-list">{activeConversation.messages.length === 0 && <p className="empty-state">Posez votre première question à Nova.</p>}{activeConversation.messages.map((message) => { const citations = uniqueDocumentCitations(message.citations); return <article key={message.id} className={`workspace-message ${message.role}`}><span>{message.role === "user" ? "VOUS" : "NOVA · WORKSPACE AI"}</span><p>{message.content}</p>{citations.length > 0 && <div className="citations" aria-label="Sources utilisées">{citations.map((citation) => <small key={citation.document_id || `${citation.document_name}:${citation.excerpt || ""}`}>Source · {citation.document_name}</small>)}</div>}</article>; })}{isSending && <article className="workspace-message assistant"><span>NOVA · WORKSPACE AI</span><p>Analyse du Workspace…</p></article>}</div>
        {error && <p className="inline-error" role="alert">{error}</p>}
        <form className="message-composer" onSubmit={submit}><input aria-label="Message à Nova" value={text} onChange={(event) => setText(event.target.value)} placeholder="Interrogez ce Workspace…" disabled={isSending} /><button type="submit" aria-label="Envoyer le message" disabled={isSending || !text.trim()}><Send size={18} /></button></form>
      </> : <div className="empty-state"><h2>Vos conversations</h2><p>Créez une conversation pour commencer à travailler avec ce Workspace.</p>{error && <p className="inline-error" role="alert">{error}</p>}<button type="button" onClick={addConversation}>Nouvelle conversation</button></div>}
    </section>
  </section>;
}
