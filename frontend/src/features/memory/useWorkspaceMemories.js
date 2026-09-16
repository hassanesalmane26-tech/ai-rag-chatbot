import { useCallback, useEffect, useRef, useState } from "react";
import { createMemory, deleteMemory, listMemories, updateMemory } from "../../services/api";
import { acceptsMemoryResult, memoryLifecycle, persistMemoryChange, upsertMemory } from "./memoryState";

export default function useWorkspaceMemories(workspaceId) {
  const [memories, setMemories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [mutationId, setMutationId] = useState(null);
  const [error, setError] = useState("");
  const workspaceRef = useRef(workspaceId);
  const requestVersion = useRef(0);
  const mutationRef = useRef(null);

  const beginMutation = useCallback((identity) => {
    if (!workspaceId || mutationRef.current) return false;
    mutationRef.current = identity;
    setMutationId(identity);
    setError("");
    return true;
  }, [workspaceId]);

  const finishMutation = useCallback((identity, requestWorkspaceId) => {
    if (mutationRef.current === identity) mutationRef.current = null;
    if (acceptsMemoryResult(workspaceRef.current, requestWorkspaceId)) {
      setMutationId((current) => current === identity ? null : current);
    }
  }, []);

  const refresh = useCallback(async () => {
    if (!workspaceId) return [];
    const version = ++requestVersion.current;
    setLoading(true); setError("");
    try {
      const values = await listMemories(workspaceId);
      if (version === requestVersion.current && acceptsMemoryResult(workspaceRef.current, workspaceId)) setMemories(values);
      return values;
    } catch (err) {
      if (version === requestVersion.current) setError(err.message);
      return [];
    } finally {
      if (version === requestVersion.current) setLoading(false);
    }
  }, [workspaceId]);

  useEffect(() => {
    workspaceRef.current = workspaceId; requestVersion.current += 1; mutationRef.current = null; setMutationId(null); setMemories([]); setError(""); refresh();
    return () => { requestVersion.current += 1; };
  }, [workspaceId, refresh]);

  const create = useCallback(async (payload) => {
    const identity = "create"; const requestWorkspaceId = workspaceId;
    if (!beginMutation(identity)) return false;
    try { const result = await persistMemoryChange(() => createMemory(requestWorkspaceId, payload), (memory) => { if (!acceptsMemoryResult(workspaceRef.current, requestWorkspaceId)) return false; setMemories((current) => upsertMemory(current, memory)); return true; }); if (result.error && acceptsMemoryResult(workspaceRef.current, requestWorkspaceId)) setError(result.error.message); return result.ok; }
    finally { finishMutation(identity, requestWorkspaceId); }
  }, [workspaceId, beginMutation, finishMutation]);

  const toggle = useCallback(async (memory) => {
    const identity = memory.id; const requestWorkspaceId = workspaceId;
    if (!beginMutation(identity)) return false;
    try { const result = await persistMemoryChange(() => updateMemory(requestWorkspaceId, memory.id, { active: !memory.active }), (updated) => { if (!acceptsMemoryResult(workspaceRef.current, requestWorkspaceId)) return false; setMemories((current) => upsertMemory(current, updated)); return true; }); if (result.error && acceptsMemoryResult(workspaceRef.current, requestWorkspaceId)) setError(result.error.message); return result.ok; }
    finally { finishMutation(identity, requestWorkspaceId); }
  }, [workspaceId, beginMutation, finishMutation]);

  const update = useCallback(async (memoryId, payload) => {
    const requestWorkspaceId = workspaceId;
    if (!beginMutation(memoryId)) return false;
    try { const result = await persistMemoryChange(() => updateMemory(requestWorkspaceId, memoryId, payload), (updated) => { if (!acceptsMemoryResult(workspaceRef.current, requestWorkspaceId)) return false; setMemories((current) => upsertMemory(current, updated)); return true; }); if (result.error && acceptsMemoryResult(workspaceRef.current, requestWorkspaceId)) setError(result.error.message); return result.ok; }
    finally { finishMutation(memoryId, requestWorkspaceId); }
  }, [workspaceId, beginMutation, finishMutation]);

  const remove = useCallback(async (memoryId) => {
    const requestWorkspaceId = workspaceId;
    if (!beginMutation(memoryId)) return false;
    try { const result = await persistMemoryChange(() => deleteMemory(requestWorkspaceId, memoryId), () => { if (!acceptsMemoryResult(workspaceRef.current, requestWorkspaceId)) return false; setMemories((current) => current.filter((item) => item.id !== memoryId)); return true; }); if (result.error && acceptsMemoryResult(workspaceRef.current, requestWorkspaceId)) setError(result.error.message); return result.ok; }
    finally { finishMutation(memoryId, requestWorkspaceId); }
  }, [workspaceId, beginMutation, finishMutation]);

  return { memories, loading, mutationId, error, lifecycle: memoryLifecycle({ workspaceId, loading, mutationId, error, count: memories.length }), refresh, create, update, toggle, remove };
}
