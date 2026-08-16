import { useCallback, useEffect, useRef, useState } from "react";
import { createMemory, deleteMemory, listMemories, updateMemory } from "../../services/api";
import { acceptsMemoryResult, upsertMemory } from "./memoryState";

export default function useWorkspaceMemories(workspaceId) {
  const [memories, setMemories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [mutationId, setMutationId] = useState(null);
  const [error, setError] = useState("");
  const workspaceRef = useRef(workspaceId);
  const requestVersion = useRef(0);

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
    workspaceRef.current = workspaceId; requestVersion.current += 1; setMemories([]); setError(""); refresh();
    return () => { requestVersion.current += 1; };
  }, [workspaceId, refresh]);

  const create = useCallback(async (payload) => {
    setMutationId("create"); setError("");
    try { const memory = await createMemory(workspaceId, payload); if (acceptsMemoryResult(workspaceRef.current, workspaceId)) setMemories((current) => upsertMemory(current, memory)); return true; }
    catch (err) { if (acceptsMemoryResult(workspaceRef.current, workspaceId)) setError(err.message); return false; }
    finally { if (acceptsMemoryResult(workspaceRef.current, workspaceId)) setMutationId(null); }
  }, [workspaceId]);

  const toggle = useCallback(async (memory) => {
    setMutationId(memory.id); setError("");
    try { const updated = await updateMemory(workspaceId, memory.id, { active: !memory.active }); if (acceptsMemoryResult(workspaceRef.current, workspaceId)) setMemories((current) => upsertMemory(current, updated)); }
    catch (err) { if (acceptsMemoryResult(workspaceRef.current, workspaceId)) setError(err.message); }
    finally { if (acceptsMemoryResult(workspaceRef.current, workspaceId)) setMutationId(null); }
  }, [workspaceId]);

  const remove = useCallback(async (memoryId) => {
    setMutationId(memoryId); setError("");
    try { await deleteMemory(workspaceId, memoryId); if (acceptsMemoryResult(workspaceRef.current, workspaceId)) setMemories((current) => current.filter((item) => item.id !== memoryId)); }
    catch (err) { if (acceptsMemoryResult(workspaceRef.current, workspaceId)) setError(err.message); }
    finally { if (acceptsMemoryResult(workspaceRef.current, workspaceId)) setMutationId(null); }
  }, [workspaceId]);

  return { memories, loading, mutationId, error, refresh, create, toggle, remove };
}
