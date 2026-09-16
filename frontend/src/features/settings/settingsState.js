export function validateWorkspaceDescription(value) {
  return value.length <= 1000 ? "" : "La description ne peut pas dépasser 1 000 caractères.";
}

export async function persistSettingChange(operation, acceptResult) {
  try {
    const value = await operation();
    if (!acceptResult(value)) return { ok: false, stale: true };
    return { ok: true, value };
  } catch (error) {
    return { ok: false, error };
  }
}
