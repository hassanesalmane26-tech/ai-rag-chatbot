import { useEffect, useMemo, useState } from "react";
import { createWorkspace as createWorkspaceRequest, listWorkspaces } from "../services/api";
import { WorkspaceContext } from "./workspaceContext";


export function WorkspaceProvider({ children }) {
  const [workspaces, setWorkspaces] = useState([]);
  const [activeWorkspaceId, setActiveWorkspaceId] = useState(null);
  const [activeView, setActiveView] = useState("home");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  async function refreshWorkspaces() {
    setLoading(true);
    try {
      const values = await listWorkspaces();
      setWorkspaces(values);
      setActiveWorkspaceId((current) => current && values.some((item) => item.id === current) ? current : values[0]?.id ?? null);
      setError(null);
    } catch (err) { setError(err.message); } finally { setLoading(false); }
  }

  useEffect(() => { refreshWorkspaces(); }, []);

  async function createWorkspace(name) {
    const workspace = await createWorkspaceRequest({ name });
    setWorkspaces((current) => [workspace, ...current]);
    setActiveWorkspaceId(workspace.id);
    setActiveView("home");
    return workspace;
  }

  const activeWorkspace = useMemo(() => workspaces.find((item) => item.id === activeWorkspaceId) ?? null, [workspaces, activeWorkspaceId]);
  return <WorkspaceContext.Provider value={{ workspaces, activeWorkspace, activeWorkspaceId, setActiveWorkspaceId, activeView, setActiveView, createWorkspace, refreshWorkspaces, loading, error }}>{children}</WorkspaceContext.Provider>;
}
