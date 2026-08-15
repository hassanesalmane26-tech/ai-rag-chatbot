import { useEffect, useMemo, useState } from "react";

const STORAGE_KEY = "trident-workspaces";

const DEFAULT_WORKSPACES = [
  {
    id: Date.now().toString() + Math.random().toString(36).slice(2),
    name: "TRIDENT AI",
  },
];

const DEFAULT_VIEW = "chat";

export default function useWorkspace() {
  const [workspaces, setWorkspaces] = useState(DEFAULT_WORKSPACES);

  const [activeWorkspaceId, setActiveWorkspaceId] = useState(
    DEFAULT_WORKSPACES[0].id
  );

  const [activeView, setActiveView] = useState(DEFAULT_VIEW);

  useEffect(() => {
    const saved = localStorage.getItem(STORAGE_KEY);

    if (!saved) return;

    const parsed = JSON.parse(saved);

    if (!Array.isArray(parsed) || parsed.length === 0) return;

    setWorkspaces(parsed);
    setActiveWorkspaceId(parsed[0].id);
  }, []);

  useEffect(() => {
    localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify(workspaces)
    );
  }, [workspaces]);

  function createWorkspace(name) {
    const workspace = {
      id: Date.now().toString() + Math.random().toString(36).slice(2),
      name,
    };

    setWorkspaces((old) => [...old, workspace]);
  }

  const activeWorkspace = useMemo(
    () =>
      workspaces.find((w) => w.id === activeWorkspaceId) ??
      workspaces[0],
    [workspaces, activeWorkspaceId]
  );

  return {
    workspaces,
    activeWorkspace,
    activeWorkspaceId,
    setActiveWorkspaceId,

    activeView,
    setActiveView,

    createWorkspace,
  };
}
