import { useEffect, useRef, useState } from "react";
import { ArrowUpRight, BookOpen, Brain, Files, ImagePlus, LoaderCircle, MessageSquarePlus, PanelRight, RefreshCw, Send, X } from "lucide-react";
import ReactMarkdown from "react-markdown";
import useWorkspaceConversations from "./useWorkspaceConversations";
import { uniqueDocumentCitations } from "./chatConversationState";
import useWorkspaceContext from "../../hooks/useWorkspaceContext";
import TridentMark from "../../components/visual/TridentMark";
import NovaContextRail from "./NovaContextRail";
import ImageCard from "../images/ImageCard";
import useWorkspaceImages from "../images/useWorkspaceImages";
import { validateImageFile } from "../images/imageState";

const safeMarkdown = {
  a: ({ href, children }) => <a href={href} target="_blank" rel="noreferrer">{children}</a>,
  img: ({ alt }) => <span>{alt || "Image externe non chargée"}</span>,
};

export default function ConversationsView({ workspaceId }) {
  const [text, setText] = useState("");
  const [showContextRail, setShowContextRail] = useState(false);
  const [imageMode, setImageMode] = useState(false);
  const [source, setSource] = useState(null);
  const [file, setFile] = useState(null);
  const [aspectRatio, setAspectRatio] = useState("1:1");
  const [fileError, setFileError] = useState("");
  const composer = useRef(null);
  const messages = useRef(null);
  const submitLock = useRef(false);
  const requestKey = useRef(null);
  const { activeWorkspace, novaConversationRequest, novaConversationTarget, setNovaActiveConversationId } = useWorkspaceContext();
  const { conversations, activeConversation, error, loading, creating, isSending, isLoadingConversation, refresh, selectConversation, addConversation, startConversationWithMessage, lifecycle } = useWorkspaceConversations(workspaceId);
  const images = useWorkspaceImages(workspaceId, activeConversation?.id ?? null, activeConversation?.messages.length || 0);
  const handledNovaRequest = useRef(0);
  const handledNovaTarget = useRef(0);
  const busy = creating || isSending || isLoadingConversation;

  useEffect(() => {
    const media = window.matchMedia("(min-width: 1440px)");
    const synchronize = () => setShowContextRail(media.matches);
    synchronize(); media.addEventListener("change", synchronize);
    return () => media.removeEventListener("change", synchronize);
  }, []);
  useEffect(() => {
    if (!novaConversationRequest || novaConversationRequest === handledNovaRequest.current) return;
    handledNovaRequest.current = novaConversationRequest; addConversation();
  }, [novaConversationRequest, addConversation]);
  useEffect(() => {
    if (!novaConversationTarget || novaConversationTarget.request === handledNovaTarget.current) return;
    handledNovaTarget.current = novaConversationTarget.request; selectConversation(novaConversationTarget.conversation);
  }, [novaConversationTarget, selectConversation]);
  useEffect(() => {
    setNovaActiveConversationId(activeConversation?.id ?? null);
    setSource(null); setFile(null);
  }, [activeConversation?.id, setNovaActiveConversationId]);
  useEffect(() => {
    if (messages.current) messages.current.scrollTop = messages.current.scrollHeight;
  }, [activeConversation?.id, activeConversation?.messages.length, isSending]);

  async function submit(event) {
    event.preventDefault();
    if (!text.trim() || busy || submitLock.current || fileError) return;
    submitLock.current = true;
    if (!requestKey.current) requestKey.current = crypto.randomUUID();
    const submittedText = text;
    try {
      const sent = await startConversationWithMessage(text, imageMode ? { requestKey: requestKey.current, aspectRatio, sourceId: source?.id, file } : null);
      if (sent) {
        setText((value) => value === submittedText ? "" : value);
        setFile(null); setSource(null); requestKey.current = null; images.refresh();
      }
    } finally { submitLock.current = false; }
  }
  function prepareImage(image, edit) {
    setImageMode(true); setSource(edit ? image : null); setFile(null);
    setText(edit ? "" : image.prompt); setAspectRatio(image.aspect_ratio); requestKey.current = null;
    composer.current?.focus();
  }
  return <section className={`conversation-layout ${showContextRail ? "conversation-layout--context" : ""}`} data-conversation-state={lifecycle} aria-busy={busy}>
    <aside className="conversation-list">
      <div><h2>Nova</h2><button type="button" onClick={addConversation} aria-label="Nouvelle conversation avec Nova" disabled={creating}>{creating ? <LoaderCircle className="spin" size={18} /> : <MessageSquarePlus size={18} />}</button></div>
      {loading ? <p className="conversation-list__state" aria-live="polite">Chargement…</p> : conversations.length === 0 ? <p className="conversation-list__state">Votre prochaine idée commence ici.</p> : conversations.map((conversation) => <button type="button" key={conversation.id} className={activeConversation?.id === conversation.id ? "active" : ""} aria-pressed={activeConversation?.id === conversation.id} onClick={() => selectConversation(conversation)}>{conversation.title}</button>)}
      {error && !activeConversation && <button type="button" onClick={() => refresh().catch(() => {})}><RefreshCw size={15} /> Réessayer</button>}
    </aside>
    <section className={`conversation-panel ${activeConversation ? "conversation-panel--active" : "conversation-panel--ready"}`} aria-label="Nova">
      <header className="nova-toolbar"><div><span>{activeConversation ? "NOVA · CONVERSATION" : "INTELLIGENT WORKSPACE"}</span><h2>{activeConversation?.title || activeWorkspace?.name || "Nova"}</h2></div><button type="button" className="nova-context-toggle" aria-label="Afficher le contexte du Workspace" aria-expanded={showContextRail} onClick={() => setShowContextRail(!showContextRail)}><PanelRight size={18} /></button></header>
      {activeConversation ? <div className="message-list" ref={messages} aria-label="Messages">
        {activeConversation.messages.length === 0 && <p className="empty-state">Posez votre première question à Nova.</p>}
        {activeConversation.messages.map((message) => {
          const citations = uniqueDocumentCitations(message.citations);
          const image = images.images.find((item) => item.message_id === message.id) || message.image;
          return <article key={message.id} className={`workspace-message ${message.role}`}><span>{message.role === "user" ? "VOUS" : "NOVA"}</span>
            <div className="nova-markdown"><ReactMarkdown skipHtml components={safeMarkdown}>{message.content}</ReactMarkdown></div>
            {image && <ImageCard key={`${workspaceId}:${image.id}`} image={image} workspaceId={workspaceId} available={images.capability?.available} onChange={images.refresh} onEdit={(item) => prepareImage(item, true)} onRegenerate={(item) => prepareImage(item, false)} />}
            {citations.length > 0 && <div className="citations" aria-label="Sources utilisées">{citations.map((citation) => <small key={citation.document_id || citation.document_name}>Source · {citation.document_name}</small>)}</div>}
          </article>;
        })}
        {isSending && <p className="nova-pending" role="status"><LoaderCircle size={16} className="spin" /> Nova travaille…</p>}
      </div> : isLoadingConversation ? <div className="nova-ready" role="status">Chargement de la conversation…</div> : <div className="nova-ready">
        <div className="nova-ready__identity"><div className="nova-ready__core" aria-hidden="true"><i /><i /><TridentMark /></div><span>NOVA · INTELLIGENCE DU WORKSPACE</span><h2>Donnez forme<br />à votre prochaine idée.</h2><p>Bienvenue dans {activeWorkspace?.name || "votre Workspace"}. Un lieu pour penser, créer et avancer avec Nova.</p></div>
        <div className="nova-ready__context" aria-label="Contexte du Workspace"><span><BookOpen size={15} />Knowledge</span><span><Brain size={15} />Memory</span><span><Files size={15} />Fichiers</span></div>
        <div className="nova-ready__suggestions"><button type="button" onClick={() => { setImageMode(false); setText("Que peux-tu m’aider à accomplir dans ce Workspace ?"); composer.current?.focus(); }}>Explorer le Workspace <ArrowUpRight size={14} /></button><button type="button" onClick={() => { setImageMode(false); setText("Résume le contexte disponible dans Knowledge."); composer.current?.focus(); }}>Interroger Knowledge <ArrowUpRight size={14} /></button>{images.capability?.available && <button type="button" onClick={() => { setImageMode(true); composer.current?.focus(); }}>Créer une image <ImagePlus size={14} /></button>}</div>
      </div>}
      {error && <p className="inline-error" role="alert">{error}</p>}
      {images.error && activeConversation && <p className="inline-error" role="alert">Images indisponibles. <button type="button" onClick={images.refresh}>Réessayer</button></p>}
      <form className="message-composer" onSubmit={submit}>
        {imageMode && <div className="nova-image-options"><span>{source ? "Modifier cette image" : "Créer avec Nova"}</span><label>Format <select aria-label="Format d’image" value={aspectRatio} onChange={(event) => { setAspectRatio(event.target.value); requestKey.current = null; }}><option>1:1</option><option>3:2</option><option>2:3</option></select></label><label className="nova-attach">Image source<input type="file" accept="image/png,image/jpeg,image/webp" disabled={!images.capability?.available || busy} onChange={(event) => { const value = event.target.files?.[0]; setFileError(validateImageFile(value)); setFile(value); setSource(null); requestKey.current = null; }} /></label><button type="button" aria-label="Fermer le mode image" onClick={() => { setImageMode(false); setSource(null); setFile(null); setFileError(""); }}><X size={16} /></button>{file && <small>{file.name}</small>}{fileError && <p role="alert">{fileError}</p>}</div>}
        <div className="message-composer__row"><span className="message-composer__mark" aria-hidden="true"><TridentMark /></span><textarea ref={composer} rows={2} aria-label="Message à Nova" value={text} onChange={(event) => { setText(event.target.value); requestKey.current = null; }} placeholder={source ? "Décrivez les modifications…" : imageMode ? "Décrivez votre image…" : "Demandez à Nova…"} disabled={busy} onKeyDown={(event) => { if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing && window.matchMedia("(pointer:fine)").matches) submit(event); }} /><button type="submit" aria-label="Envoyer le message" disabled={busy || !text.trim() || Boolean(fileError) || (imageMode && !images.capability?.available)}>{busy ? <LoaderCircle className="spin" size={18} /> : <Send size={18} />}</button></div>
        <div className="message-composer__tools"><button type="button" aria-pressed={imageMode} disabled={!images.capability?.available} title={images.capability?.available ? "Créer ou modifier une image" : "Création d’images non configurée"} onClick={() => setImageMode(!imageMode)}><ImagePlus size={15} /> Image</button><small>{imageMode ? "Création liée à ce Workspace" : "Nova · contexte autorisé du Workspace"}</small></div>
      </form>
    </section>
    {showContextRail && <NovaContextRail workspace={activeWorkspace} workspaceId={workspaceId} />}
  </section>;
}
