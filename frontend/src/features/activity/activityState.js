export function formatActivityTime(value) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "Date indisponible" : new Intl.DateTimeFormat("fr-FR", { dateStyle: "medium", timeStyle: "short" }).format(date);
}

export function acceptsActivityResult(activeWorkspaceId, requestWorkspaceId) {
  return Boolean(activeWorkspaceId) && activeWorkspaceId === requestWorkspaceId;
}

export function normalizeActivityEvents(values) {
  if (!Array.isArray(values)) return [];
  return values
    .filter((event) => event?.id && typeof event.label === "string")
    .map(({ id, action, label, resource_type, resource_id, created_at }) => ({
      id, action, label, resource_type, resource_id, created_at,
    }))
    .sort((left, right) => {
      const difference = Date.parse(right.created_at || 0) - Date.parse(left.created_at || 0);
      return difference || String(right.id).localeCompare(String(left.id));
    });
}

export function activityLifecycle({ workspaceId, loading, error, count }) {
  if (!workspaceId) return "unavailable";
  if (loading) return "loading";
  if (error) return "error";
  return count > 0 ? "ready" : "empty";
}
