import { useRef } from "react";
import { MessageSquarePlus, X } from "lucide-react";
import IconButton from "../ui/IconButton";
import WorkspaceSelector from "./WorkspaceSelector";
import { workspaceModules } from "../../app/modules/registry";
import useWorkspaceContext from "../../hooks/useWorkspaceContext";
import useModalFocus from "../../hooks/useModalFocus";

export default function MobileWorkspaceSelector({ open, onClose }) {
  const { activeView, activeWorkspace, setActiveView, requestNovaConversation } = useWorkspaceContext();
  const closeButtonRef = useRef(null);
  const dialogRef = useRef(null);
  useModalFocus({ open, containerRef: dialogRef, initialRef: closeButtonRef, onClose });

  if (!open) return null;

  return <div className="mobile-workspace-sheet" role="presentation">
    <button className="mobile-workspace-sheet__backdrop" type="button" aria-label="Fermer le menu système" onClick={onClose} />
    <section ref={dialogRef} className="mobile-workspace-sheet__panel ds-glass-panel ds-glass-panel--elevated" role="dialog" aria-modal="true" aria-labelledby="mobile-workspace-sheet-title" tabIndex={-1}>
      <header><div><span>TRIDENT AI · SYSTÈME</span><h2 id="mobile-workspace-sheet-title">{activeWorkspace?.name || "Votre Workspace"}</h2><small>Workspace actif</small></div><IconButton ref={closeButtonRef} aria-label="Fermer le menu système" onClick={onClose}><X size={18} /></IconButton></header>
      <section className="mobile-workspace-sheet__nova" aria-label="Nova"><button type="button" onClick={() => { requestNovaConversation(); onClose(); }}><MessageSquarePlus size={18} /><span><strong>Nouvelle conversation</strong><small>Commencer avec Nova</small></span></button></section>
      <nav className="mobile-workspace-sheet__modules" aria-label="Systèmes du Workspace">{workspaceModules.map(({ id, label, icon: Icon }) => <button key={id} type="button" aria-current={activeView === id ? "page" : undefined} onClick={() => { setActiveView(id); onClose(); }}><Icon size={18} />{label}</button>)}</nav>
      <div className="mobile-workspace-sheet__divider"><span>WORKSPACE ENGINE</span></div>
      <WorkspaceSelector showCreate onWorkspaceSelected={onClose} />
    </section>
  </div>;
}
