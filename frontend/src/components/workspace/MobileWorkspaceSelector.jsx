import { useEffect, useRef, useState } from "react";
import { LoaderCircle, MessageSquare, MessageSquarePlus, X } from "lucide-react";
import IconButton from "../ui/IconButton";
import WorkspaceSelector from "./WorkspaceSelector";
import { workspaceModules } from "../../app/modules/registry";
import useWorkspaceContext from "../../hooks/useWorkspaceContext";
import useModalFocus from "../../hooks/useModalFocus";
import { listConversations } from "../../services/api";

export default function MobileWorkspaceSelector({ open, onClose }) {
  const { activeView, activeWorkspace, activeWorkspaceId, novaActiveConversationId, setActiveView, requestNovaConversation, openNovaConversation } = useWorkspaceContext();
  const [recentConversations, setRecentConversations] = useState([]);
  const [conversationState, setConversationState] = useState("loading");
  const closeButtonRef = useRef(null);
  const dialogRef = useRef(null);
  useModalFocus({ open, containerRef: dialogRef, initialRef: closeButtonRef, onClose });
  useEffect(() => {
    if (!open || !activeWorkspaceId) return undefined;
    let current = true;
    setRecentConversations([]);
    setConversationState("loading");
    listConversations(activeWorkspaceId).then((items) => {
      if (!current) return;
      setRecentConversations(items.slice(0, 5));
      setConversationState("ready");
    }).catch(() => {
      if (current) setConversationState("error");
    });
    return () => { current = false; };
  }, [open, activeWorkspaceId]);

  if (!open) return null;

  return <div className="mobile-workspace-sheet" role="presentation">
    <button className="mobile-workspace-sheet__backdrop" type="button" aria-label="Fermer le menu système" onClick={onClose} />
    <section ref={dialogRef} className="mobile-workspace-sheet__panel ds-glass-panel ds-glass-panel--elevated" role="dialog" aria-modal="true" aria-labelledby="mobile-workspace-sheet-title" tabIndex={-1}>
      <header><div><span>TRIDENT AI · SYSTÈME</span><h2 id="mobile-workspace-sheet-title">{activeWorkspace?.name || "Votre Workspace"}</h2><small>Workspace actif</small></div><IconButton ref={closeButtonRef} aria-label="Fermer le menu système" onClick={onClose}><X size={18} /></IconButton></header>
      <section className="mobile-workspace-sheet__nova" aria-label="Nova"><button type="button" onClick={() => { requestNovaConversation(); onClose(); }}><MessageSquarePlus size={18} /><span><strong>Nouvelle conversation</strong><small>Commencer avec Nova</small></span></button></section>
      <section className="mobile-workspace-sheet__recent" aria-labelledby="recent-conversations-title"><div><span id="recent-conversations-title">CONVERSATIONS RÉCENTES</span><small>{conversationState === "ready" ? recentConversations.length : ""}</small></div>{conversationState === "loading" && <p aria-live="polite"><LoaderCircle className="spin" size={14} /> Chargement…</p>}{conversationState === "error" && <p>Conversations indisponibles.</p>}{conversationState === "ready" && recentConversations.length === 0 && <p>Aucune conversation récente.</p>}{recentConversations.map((conversation) => <button key={conversation.id} type="button" aria-current={novaActiveConversationId === conversation.id ? "page" : undefined} onClick={() => { openNovaConversation(conversation); onClose(); }}><MessageSquare size={14} /><span>{conversation.title}</span></button>)}</section>
      <div className="mobile-workspace-sheet__divider"><span>SYSTÈMES</span></div>
      <nav className="mobile-workspace-sheet__modules" aria-label="Systèmes du Workspace">{workspaceModules.map(({ id, label, icon: Icon }) => <button key={id} type="button" aria-current={activeView === id ? "page" : undefined} onClick={() => { setActiveView(id); onClose(); }}><Icon size={18} />{label}</button>)}</nav>
      <div className="mobile-workspace-sheet__divider"><span>WORKSPACE ENGINE</span></div>
      <WorkspaceSelector showCreate onWorkspaceSelected={onClose} />
    </section>
  </div>;
}
