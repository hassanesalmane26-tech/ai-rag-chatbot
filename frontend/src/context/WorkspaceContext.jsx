import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  createWorkspace as createWorkspaceRequest,
  listWorkspaces,
  updateWorkspace as updateWorkspaceRequest,
} from "../services/api";
import { WorkspaceContext } from "./workspaceContext";

const ACTIVE_WORKSPACE_STORAGE_KEY = "trident.ai.active_workspace_id";
const LEGACY_ACTIVE_WORKSPACE_STORAGE_KEY = "trident.genesis.active_workspace_id";

function readPersistedWorkspaceId() {
  try {
    const current = window.localStorage.getItem(ACTIVE_WORKSPACE_STORAGE_KEY);
    if (current) return current;
    const legacy = window.localStorage.getItem(LEGACY_ACTIVE_WORKSPACE_STORAGE_KEY);
    if (legacy) {
      window.localStorage.setItem(ACTIVE_WORKSPACE_STORAGE_KEY, legacy);
      window.localStorage.removeItem(LEGACY_ACTIVE_WORKSPACE_STORAGE_KEY);
    }
    return legacy;
  } catch {
    return null;
  }
}

function persistWorkspaceId(workspaceId) {
  try {
    if (workspaceId) window.localStorage.setItem(ACTIVE_WORKSPACE_STORAGE_KEY, workspaceId);
    else window.localStorage.removeItem(ACTIVE_WORKSPACE_STORAGE_KEY);
  } catch {
    // Storage is a presentation preference, never an authoritative dependency.
  }
}

export function WorkspaceProvider({ children }) {
  const [workspaces, setWorkspaces] = useState([]);
  const [activeWorkspaceId, setActiveWorkspaceIdState] = useState(null);
  const [activeView, setActiveView] = useState("home");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [mutation, setMutation] = useState(null);
  const activeWorkspaceIdRef = useRef(null);
  const persistedWorkspaceIdRef = useRef(readPersistedWorkspaceId());
  const refreshVersionRef = useRef(0);

  const selectWorkspace = useCallback((workspaceId, availableWorkspaces = workspaces) => {
    const selected = availableWorkspaces.find((workspace) => workspace.id === workspaceId) || null;
    const nextId = selected?.id ?? null;
    activeWorkspaceIdRef.current = nextId;
    setActiveWorkspaceIdState(nextId);
    persistWorkspaceId(nextId);
    return selected;
  }, [workspaces]);

  const refreshWorkspaces = useCallback(async ({ preferredWorkspaceId } = {}) => {
    const requestVersion = ++refreshVersionRef.current;
    setLoading(true);
    try {
      const values = await listWorkspaces();
      if (requestVersion !== refreshVersionRef.current) return values;

      setWorkspaces(values);
      const candidateId = preferredWorkspaceId
        ?? activeWorkspaceIdRef.current
        ?? persistedWorkspaceIdRef.current;
      const next = values.find((workspace) => workspace.id === candidateId) || values[0] || null;
      activeWorkspaceIdRef.current = next?.id ?? null;
      setActiveWorkspaceIdState(next?.id ?? null);
      persistWorkspaceId(next?.id ?? null);
      persistedWorkspaceIdRef.current = null;
      setError(null);
      return values;
    } catch (err) {
      if (requestVersion === refreshVersionRef.current) setError(err.message);
      throw err;
    } finally {
      if (requestVersion === refreshVersionRef.current) setLoading(false);
    }
  }, []);

  useEffect(() => {
    refreshWorkspaces().catch(() => {});
    return () => { refreshVersionRef.current += 1; };
  }, [refreshWorkspaces]);

  const createWorkspace = useCallback(async (name, description) => {
    refreshVersionRef.current += 1;
    setMutation("creating");
    try {
      const workspace = await createWorkspaceRequest({ name, description });
      setWorkspaces((current) => [workspace, ...current.filter((item) => item.id !== workspace.id)]);
      activeWorkspaceIdRef.current = workspace.id;
      setActiveWorkspaceIdState(workspace.id);
      persistWorkspaceId(workspace.id);
      setActiveView("home");
      setError(null);
      return workspace;
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setMutation(null);
    }
  }, []);

  const updateWorkspace = useCallback(async (workspaceId, payload) => {
    refreshVersionRef.current += 1;
    setMutation("updating");
    try {
      const workspace = await updateWorkspaceRequest(workspaceId, payload);
      setWorkspaces((current) => current.map((item) => item.id === workspace.id ? workspace : item));
      setError(null);
      return workspace;
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setMutation(null);
    }
  }, []);

  const activeWorkspace = useMemo(
    () => workspaces.find((item) => item.id === activeWorkspaceId) ?? null,
    [workspaces, activeWorkspaceId],
  );
  const state = loading ? (workspaces.length ? "loading" : "boot") : error ? "error" : activeWorkspace ? "ready" : "empty";
  const value = useMemo(() => ({
    workspaces,
    activeWorkspace,
    activeWorkspaceId,
    activeView,
    loading,
    error,
    mutation,
    state,
    setActiveView,
    selectWorkspace,
    createWorkspace,
    updateWorkspace,
    refreshWorkspaces,
  }), [workspaces, activeWorkspace, activeWorkspaceId, activeView, loading, error, mutation, state, selectWorkspace, createWorkspace, updateWorkspace, refreshWorkspaces]);

  return <WorkspaceContext.Provider value={value}>{children}</WorkspaceContext.Provider>;
}
