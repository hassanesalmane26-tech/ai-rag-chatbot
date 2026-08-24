import { useRef } from "react";
import { X } from "lucide-react";
import IconButton from "../ui/IconButton";
import WorkspaceSelector from "./WorkspaceSelector";
import { workspaceModules } from "../../app/modules/registry";
import useWorkspaceContext from "../../hooks/useWorkspaceContext";
import useModalFocus from "../../hooks/useModalFocus";

export default function MobileWorkspaceSelector({ open, onClose }) {
  const { activeView, setActiveView } = useWorkspaceContext();
  const closeButtonRef = useRef(null);
  const dialogRef = useRef(null);
  useModalFocus({ open, containerRef: dialogRef, initialRef: closeButtonRef, onClose });

  if (!open) return null;

  return <div className="mobile-workspace-sheet" role="presentation">
    <button className="mobile-workspace-sheet__backdrop" type="button" aria-label="Fermer le sélecteur de Workspaces" onClick={onClose} />
    <section ref={dialogRef} className="mobile-workspace-sheet__panel ds-glass-panel ds-glass-panel--elevated" role="dialog" aria-modal="true" aria-labelledby="mobile-workspace-sheet-title" tabIndex={-1}>
      <header><div><span>WORKSPACE ENGINE</span><h2 id="mobile-workspace-sheet-title">Vos Workspaces</h2></div><IconButton ref={closeButtonRef} aria-label="Fermer le sélecteur de Workspaces" onClick={onClose}><X size={18} /></IconButton></header>
      <WorkspaceSelector showCreate onWorkspaceSelected={onClose} />
      <nav className="mobile-workspace-sheet__modules" aria-label="Autres modules du Workspace">{workspaceModules.filter((module) => !module.mobile).map(({ id, label, icon: Icon }) => <button key={id} type="button" aria-current={activeView === id ? "page" : undefined} onClick={() => { setActiveView(id); onClose(); }}><Icon size={18} />{label}</button>)}</nav>
    </section>
  </div>;
}
