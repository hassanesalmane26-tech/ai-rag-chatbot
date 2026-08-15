import { X } from "lucide-react";
import IconButton from "../ui/IconButton";
import WorkspaceSelector from "./WorkspaceSelector";

export default function MobileWorkspaceSelector({ open, onClose }) {
  if (!open) return null;

  return <div className="mobile-workspace-sheet" role="presentation">
    <button className="mobile-workspace-sheet__backdrop" type="button" aria-label="Fermer le sélecteur de Workspaces" onClick={onClose} />
    <section className="mobile-workspace-sheet__panel ds-glass-panel ds-glass-panel--elevated" role="dialog" aria-modal="true" aria-labelledby="mobile-workspace-sheet-title">
      <header><div><span>WORKSPACE ENGINE</span><h2 id="mobile-workspace-sheet-title">Vos Workspaces</h2></div><IconButton aria-label="Fermer le sélecteur de Workspaces" onClick={onClose}><X size={18} /></IconButton></header>
      <WorkspaceSelector showCreate onWorkspaceSelected={onClose} />
    </section>
  </div>;
}
