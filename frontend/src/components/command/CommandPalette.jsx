import { CornerDownLeft, Search, Sparkles, X } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { workspaceModules } from "../../app/modules/registry";
import useWorkspaceContext from "../../hooks/useWorkspaceContext";
import useModalFocus from "../../hooks/useModalFocus";
import { commandKeyAction, commandResults, commandSurfaceState, executeCommandResult } from "./commandState";

export default function CommandPalette({ open, onClose }) {
  const { workspaces, activeWorkspace, activeWorkspaceId, loading, error, selectWorkspace, setActiveView } = useWorkspaceContext();
  const [query, setQuery] = useState("");
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef(null);
  const dialogRef = useRef(null);
  useModalFocus({ open, containerRef: dialogRef, initialRef: inputRef, onClose });
  useEffect(() => { if (open) { setQuery(""); setSelectedIndex(0); } }, [open]);

  const results = useMemo(() => commandResults({ query, modules: workspaceModules, workspaces, activeWorkspaceId }), [query, workspaces, activeWorkspaceId]);
  const actions = results.filter((result) => result.type === "action");
  const modules = results.filter((result) => result.type === "module");
  const matchingWorkspaces = results.filter((result) => result.type === "workspace");
  const surfaceState = commandSurfaceState({ loading, error, resultCount: results.length });
  if (!open) return null;

  function navigate(moduleId) { setActiveView(moduleId); onClose(); }
  function switchWorkspace(workspaceId) { selectWorkspace(workspaceId); onClose(); }
  function execute(result) {
    executeCommandResult(result, { navigate, switchWorkspace });
  }
  function focusResult(index) {
    setSelectedIndex(index);
    dialogRef.current?.querySelectorAll("[data-command-result]")[index]?.focus();
  }
  function handleKeyDown(event) {
    const action = commandKeyAction({ key: event.key, selectedIndex, resultCount: results.length, inputFocused: event.target === inputRef.current });
    if (!action.handled) return;
    event.preventDefault();
    if (action.execute) execute(results[action.selectedIndex]);
    else focusResult(action.selectedIndex);
  }

  return <div className="command-overlay" data-command-state={surfaceState}><button className="command-backdrop" type="button" aria-label="Fermer les commandes" onClick={onClose} /><section ref={dialogRef} className="command-palette ds-glass-panel ds-glass-panel--elevated" role="dialog" aria-modal="true" aria-labelledby="command-title" aria-busy={loading} tabIndex={-1} onKeyDown={handleKeyDown}><header><div><span>TRIDENT COMMAND</span><h2 id="command-title">Rechercher ou demander à TRIDENT…</h2><small>Workspace actif · {activeWorkspace?.name || "Chargement"}</small></div><button type="button" aria-label="Fermer les commandes" onClick={onClose}><X size={18} /></button></header><label className="command-input"><Search size={18} /><input ref={inputRef} value={query} onChange={(event) => { setQuery(event.target.value); setSelectedIndex(0); }} placeholder="Module ou Workspace…" aria-label="Rechercher une commande TRIDENT" aria-controls="trident-command-results" /></label><div className="command-results" id="trident-command-results">{loading ? <p className="command-empty" aria-live="polite">Chargement des commandes autorisées…</p> : error ? <p className="command-empty" role="alert">Les Workspaces sont temporairement indisponibles.</p> : <>{actions.length > 0 && <section className="command-results__primary"><h3>Action</h3>{actions.map((result) => <button data-command-result key={result.key} type="button" onFocus={() => setSelectedIndex(results.indexOf(result))} onClick={() => execute(result)}><Sparkles size={17} /><span><strong>{result.title}</strong><small>{result.subtitle}</small></span><CornerDownLeft size={15} /></button>)}</section>}{modules.length > 0 && <section className="command-results__grid"><h3>Modules</h3><div>{modules.map((result) => { const Icon = result.icon; return <button data-command-result key={result.key} type="button" onFocus={() => setSelectedIndex(results.indexOf(result))} onClick={() => execute(result)}><Icon size={17} /><span><strong>{result.title}</strong><small>{result.subtitle}</small></span></button>; })}</div></section>}{matchingWorkspaces.length > 0 && <section className="command-results__workspaces"><h3>Workspaces</h3>{matchingWorkspaces.map((result) => <button data-command-result key={result.key} type="button" aria-current={result.active ? "true" : undefined} onFocus={() => setSelectedIndex(results.indexOf(result))} onClick={() => execute(result)}><span className="command-workspace-mark" /><span><strong>{result.title}</strong><small>{result.subtitle}</small></span></button>)}</section>}{results.length === 0 && <p className="command-empty">Aucun module ou Workspace correspondant.</p>}</>}</div><footer><kbd>↑ ↓</kbd> naviguer <kbd>Entrée</kbd> ouvrir <kbd>Échap</kbd> fermer <span>Navigation limitée aux données déjà autorisées.</span></footer></section></div>;
}
