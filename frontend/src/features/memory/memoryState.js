export function acceptsMemoryResult(activeWorkspaceId, requestWorkspaceId) {
  return Boolean(requestWorkspaceId) && activeWorkspaceId === requestWorkspaceId;
}

export function upsertMemory(memories, memory) {
  return [memory, ...memories.filter((item) => item.id !== memory.id)];
}

export function validateMemory(title, content) {
  if (!title.trim()) return "Donnez un titre à cette mémoire.";
  if (!content.trim()) return "Ajoutez un contenu à mémoriser.";
  if (title.trim().length > 160) return "Le titre dépasse 160 caractères.";
  if (content.trim().length > 4000) return "La mémoire dépasse 4 000 caractères.";
  return "";
}
