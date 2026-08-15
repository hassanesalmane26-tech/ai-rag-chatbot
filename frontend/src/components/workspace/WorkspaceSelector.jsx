import useWorkspaceContext from "../../hooks/useWorkspaceContext";

export default function WorkspaceSelector() {
  const { workspaces, activeWorkspaceId, setActiveWorkspaceId } = useWorkspaceContext();
  return <section className="workspace-selector"><div className="workspace-selector-header"><h2>Workspaces</h2><span>{workspaces.length}</span></div><div className="workspace-list">{workspaces.map((workspace) => <button key={workspace.id} onClick={() => setActiveWorkspaceId(workspace.id)} className={`workspace-card ${activeWorkspaceId === workspace.id ? "active" : ""}`}><strong>{workspace.name}</strong><span>{workspace.description || "Espace intelligent"}</span></button>)}</div></section>;
}
