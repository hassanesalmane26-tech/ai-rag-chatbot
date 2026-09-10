import { CornerDownLeft, Search, Sparkles, X } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { workspaceModules } from "../../app/modules/registry";
import useWorkspaceContext from "../../hooks/useWorkspaceContext";
import useModalFocus from "../../hooks/useModalFocus";

export default function CommandPalette({ open, onClose }) {
  const { workspaces, activeWorkspace, activeWorkspaceId, selectWorkspace, setActiveView } = useWorkspaceContext();
  const [query, setQuery] = useState("");
  const inputRef = useRef(null);
  const dialogRef = useRef(null);
  useModalFocus({ open, containerRef: dialogRef, initialRef: inputRef, onClose });
  useEffect(() => { if (open) setQuery(""); }, [open]);

  const normalized = query.trim().toLocaleLowerCase("fr");
  const modules = useMemo(() => workspaceModules.filter((module) => !normalized || `${module.label} ${module.id}`.toLocaleLowerCase("fr").includes(normalized)), [normalized]);
  const matchingWorkspaces = useMemo(() => workspaces.filter((workspace) => !normalized || workspace.name.toLocaleLowerCase("fr").includes(normalized)), [normalized, workspaces]);
  if (!open) return null;

  function navigate(moduleId) { setActiveView(moduleId); onClose(); }
  function switchWorkspace(workspaceId) { selectWorkspace(workspaceId); onClose(); }

  return <div className="command-overlay"><button className="command-backdrop" type="button" aria-label="Fermer les commandes" onClick={onClose} /><section ref={dialogRef} className="command-palette ds-glass-panel ds-glass-panel--elevated" role="dialog" aria-modal="true" aria-labelledby="command-title" tabIndex={-1}><header><div><span>TRIDENT COMMAND</span><h2 id="command-title">Rechercher ou demander à TRIDENT…</h2><small>Workspace actif · {activeWorkspace?.name || "Chargement"}</small></div><button type="button" aria-label="Fermer les commandes" onClick={onClose}><X size={18} /></button></header><label className="command-input"><Search size={18} /><input ref={inputRef} value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Module ou Workspace…" aria-label="Rechercher une commande TRIDENT" /></label><div className="command-results"><section className="command-results__primary"><h3>Action</h3><button type="button" onClick={() => navigate("conversations")}><Sparkles size={17} /><span><strong>Demander à Nova</strong><small>Ouvrir une conversation dans le Workspace actif</small></span><CornerDownLeft size={15} /></button></section>{modules.length > 0 && <section className="command-results__grid"><h3>Modules</h3><div>{modules.map(({ id, label, icon: Icon }) => <button key={id} type="button" onClick={() => navigate(id)}><Icon size={17} /><span><strong>{label}</strong><small>Ouvrir le module</small></span></button>)}</div></section>}{matchingWorkspaces.length > 0 && <section className="command-results__workspaces"><h3>Workspaces</h3>{matchingWorkspaces.map((workspace) => <button key={workspace.id} type="button" aria-current={workspace.id === activeWorkspaceId ? "true" : undefined} onClick={() => switchWorkspace(workspace.id)}><span className="command-workspace-mark" /><span><strong>{workspace.name}</strong><small>{workspace.description || "Workspace intelligent"}</small></span></button>)}</section>}{modules.length === 0 && matchingWorkspaces.length === 0 && <p className="command-empty">Aucun module ou Workspace correspondant.</p>}</div><footer><kbd>Échap</kbd> fermer <span>Navigation limitée aux données déjà autorisées.</span></footer></section></div>;
}
