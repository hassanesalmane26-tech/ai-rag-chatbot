import { CornerDownLeft, Search, Sparkles, X } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { workspaceModules } from "../../app/modules/registry";
import useWorkspaceContext from "../../hooks/useWorkspaceContext";

export default function CommandPalette({ open, onClose }) {
  const { workspaces, activeWorkspaceId, selectWorkspace, setActiveView } = useWorkspaceContext();
  const [query, setQuery] = useState("");
  const inputRef = useRef(null);

  useEffect(() => {
    if (!open) return undefined;
    setQuery(""); inputRef.current?.focus();
    const escape = (event) => { if (event.key === "Escape") onClose(); };
    window.addEventListener("keydown", escape);
    return () => window.removeEventListener("keydown", escape);
  }, [open, onClose]);

  const normalized = query.trim().toLocaleLowerCase("fr");
  const modules = useMemo(() => workspaceModules.filter((module) => !normalized || `${module.label} ${module.id}`.toLocaleLowerCase("fr").includes(normalized)), [normalized]);
  const matchingWorkspaces = useMemo(() => workspaces.filter((workspace) => !normalized || workspace.name.toLocaleLowerCase("fr").includes(normalized)), [normalized, workspaces]);
  if (!open) return null;

  function navigate(moduleId) { setActiveView(moduleId); onClose(); }
  function switchWorkspace(workspaceId) { selectWorkspace(workspaceId); onClose(); }

  return <div className="command-overlay"><button className="command-backdrop" type="button" aria-label="Fermer les commandes" onClick={onClose} /><section className="command-palette ds-glass-panel ds-glass-panel--elevated" role="dialog" aria-modal="true" aria-labelledby="command-title"><header><div><span>TRIDENT COMMAND</span><h2 id="command-title">Search or ask TRIDENT…</h2></div><button type="button" aria-label="Fermer les commandes" onClick={onClose}><X size={18} /></button></header><label className="command-input"><Search size={18} /><input ref={inputRef} value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Module ou Workspace…" aria-label="Rechercher une commande TRIDENT" /></label><div className="command-results"><section><h3>Actions</h3><button type="button" onClick={() => navigate("conversations")}><Sparkles size={17} /><span><strong>Ask Nova</strong><small>Ouvrir une conversation dans le Workspace actif</small></span><CornerDownLeft size={15} /></button></section>{modules.length > 0 && <section><h3>Modules</h3>{modules.map(({ id, label, icon: Icon }) => <button key={id} type="button" onClick={() => navigate(id)}><Icon size={17} /><span><strong>{label}</strong><small>Ouvrir le module</small></span></button>)}</section>}{matchingWorkspaces.length > 0 && <section><h3>Workspaces</h3>{matchingWorkspaces.map((workspace) => <button key={workspace.id} type="button" aria-current={workspace.id === activeWorkspaceId ? "true" : undefined} onClick={() => switchWorkspace(workspace.id)}><span className="command-workspace-mark" /><span><strong>{workspace.name}</strong><small>{workspace.description || "Workspace intelligent"}</small></span></button>)}</section>}{modules.length === 0 && matchingWorkspaces.length === 0 && <p className="command-empty">Aucun module ou Workspace correspondant.</p>}</div><footer><kbd>Esc</kbd> fermer <span>Navigation limitée aux données déjà autorisées.</span></footer></section></div>;
}
