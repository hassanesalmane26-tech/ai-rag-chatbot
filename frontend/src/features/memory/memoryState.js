export function acceptsMemoryResult(activeWorkspaceId, requestWorkspaceId) {
  return Boolean(requestWorkspaceId) && activeWorkspaceId === requestWorkspaceId;
}

export function upsertMemory(memories, memory) {
  return [memory, ...memories.filter((item) => item.id !== memory.id)].sort((left, right) => {
    const difference = Date.parse(right.updated_at || right.created_at || 0)
      - Date.parse(left.updated_at || left.created_at || 0);
    return difference || right.id.localeCompare(left.id);
  });
}

export function memoryLifecycle({ workspaceId, loading, mutationId, error, count }) {
  if (!workspaceId) return "unavailable";
  if (loading) return "loading";
  if (mutationId) return "saving";
  if (error) return "error";
  return count > 0 ? "ready" : "empty";
}

export async function persistMemoryChange(operation, commit) {
  try {
    const value = await operation();
    if (commit(value) === false) return { ok: false, stale: true };
    return { ok: true, value };
  } catch (error) {
    return { ok: false, error };
  }
}

export function validateMemory(title, content) {
  if (!title.trim()) return "Donnez un titre à cette mémoire.";
  if (!content.trim()) return "Ajoutez un contenu à mémoriser.";
  if (title.trim().length > 160) return "Le titre dépasse 160 caractères.";
  if (content.trim().length > 4000) return "La mémoire dépasse 4 000 caractères.";
  return "";
}
