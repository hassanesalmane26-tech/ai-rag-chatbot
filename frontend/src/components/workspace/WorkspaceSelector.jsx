import { useEffect, useState } from "react";
import useWorkspaceContext from "../../hooks/useWorkspaceContext";

export default function WorkspaceSelector({ showCreate = false, onWorkspaceSelected }) {
  const {
    workspaces, activeWorkspace, activeWorkspaceId, selectWorkspace, loading, error, mutation,
    createWorkspace, refreshWorkspaces, updateWorkspace,
  } = useWorkspaceContext();
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState("");
  const [creating, setCreating] = useState(false);
  const [newWorkspaceName, setNewWorkspaceName] = useState("");
  const isDisabled = loading || Boolean(mutation);

  useEffect(() => {
    setEditing(false);
    setName(activeWorkspace?.name ?? "");
  }, [activeWorkspaceId, activeWorkspace?.name]);

  async function renameWorkspace(event) {
    event.preventDefault();
    if (!activeWorkspace || !name.trim() || mutation) return;
    try {
      await updateWorkspace(activeWorkspace.id, { name: name.trim() });
      setEditing(false);
    } catch {
      // The request error is surfaced in this selector without losing the active Workspace.
    }
  }

  async function createNewWorkspace(event) {
    event.preventDefault();
    if (!newWorkspaceName.trim() || mutation) return;
    try {
      await createWorkspace(newWorkspaceName.trim());
      setNewWorkspaceName("");
      setCreating(false);
      onWorkspaceSelected?.();
    } catch {
      // The recoverable request error remains visible in this shared selector.
    }
  }

  return <section className="workspace-selector" aria-busy={loading}>
    <div className="workspace-selector-header"><h2>Workspaces</h2><span>{workspaces.length}</span></div>
    {error && <div className="workspace-selector-state" role="alert"><span>Synchronisation impossible.</span><button type="button" onClick={() => refreshWorkspaces().catch(() => {})}>Réessayer</button></div>}
    {loading && workspaces.length === 0 ? <p className="workspace-selector-state">Chargement des Workspaces…</p> : null}
    {!loading && !error && workspaces.length === 0 ? <p className="workspace-selector-state">Aucun Workspace disponible.</p> : null}
    <div className="workspace-list">{workspaces.map((workspace) => <button key={workspace.id} type="button" disabled={isDisabled} onClick={() => { selectWorkspace(workspace.id); onWorkspaceSelected?.(); }} aria-pressed={activeWorkspaceId === workspace.id} className={`workspace-card ${activeWorkspaceId === workspace.id ? "active" : ""}`}><strong>{workspace.name}</strong><span>{workspace.description || "Espace intelligent"}</span></button>)}</div>
    {activeWorkspace && <div className="workspace-rename">{editing ? <form onSubmit={renameWorkspace}><label htmlFor="workspace-rename-input">Nom du Workspace actif</label><input id="workspace-rename-input" aria-label="Nouveau nom du Workspace" value={name} onChange={(event) => setName(event.target.value)} maxLength="120" disabled={Boolean(mutation)} /><div><button className="ds-button" type="submit" disabled={!name.trim() || Boolean(mutation)}>{mutation === "updating" ? "Mise à jour…" : "Enregistrer"}</button><button className="ds-button ds-button--secondary" type="button" onClick={() => { setEditing(false); setName(activeWorkspace.name); }} disabled={Boolean(mutation)}>Annuler</button></div></form> : <button className="workspace-rename__trigger ds-button ds-button--secondary" type="button" onClick={() => setEditing(true)} disabled={isDisabled}>Renommer</button>}</div>}
    {showCreate && <div className="workspace-create">{creating ? <form onSubmit={createNewWorkspace}><label htmlFor="mobile-workspace-name">Nouveau Workspace</label><input id="mobile-workspace-name" autoFocus value={newWorkspaceName} onChange={(event) => setNewWorkspaceName(event.target.value)} placeholder="Nom du Workspace" maxLength="120" disabled={Boolean(mutation)} /><div><button type="submit" disabled={!newWorkspaceName.trim() || Boolean(mutation)}>{mutation === "creating" ? "Création…" : "Créer"}</button><button type="button" onClick={() => { setCreating(false); setNewWorkspaceName(""); }} disabled={Boolean(mutation)}>Annuler</button></div></form> : <button type="button" className="ds-button ds-button--secondary" onClick={() => setCreating(true)} disabled={isDisabled}>Nouveau Workspace</button>}</div>}
  </section>;
}
