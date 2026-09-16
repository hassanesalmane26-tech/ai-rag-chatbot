export function normalizeCommandQuery(value) {
  return value.trim().toLocaleLowerCase("fr");
}

function matches(query, ...values) {
  return !query || values.some((value) => value?.toLocaleLowerCase("fr").includes(query));
}

export function commandResults({ query, modules, workspaces, activeWorkspaceId }) {
  const normalized = normalizeCommandQuery(query);
  const results = [];
  if (matches(normalized, "Nova", "conversation", "demander")) {
    results.push({ key: "action:nova", type: "action", id: "conversations", title: "Demander à Nova", subtitle: "Ouvrir une conversation dans le Workspace actif" });
  }
  for (const module of modules) {
    if (matches(normalized, module.label, module.id)) {
      results.push({ key: `module:${module.id}`, type: "module", id: module.id, title: module.label, subtitle: "Ouvrir le module", icon: module.icon });
    }
  }
  for (const workspace of workspaces) {
    if (matches(normalized, workspace.name, workspace.description)) {
      results.push({ key: `workspace:${workspace.id}`, type: "workspace", id: workspace.id, title: workspace.name, subtitle: workspace.description || "Workspace intelligent", active: workspace.id === activeWorkspaceId });
    }
  }
  return results;
}

export function nextCommandIndex(current, direction, count) {
  if (count <= 0) return -1;
  if (direction === "first") return 0;
  if (direction === "last") return count - 1;
  return (current + (direction === "previous" ? -1 : 1) + count) % count;
}

export function commandSurfaceState({ loading, error, resultCount }) {
  if (loading) return "loading";
  if (error) return "error";
  return resultCount > 0 ? "ready" : "empty";
}

export function executeCommandResult(result, { navigate, switchWorkspace }) {
  if (!result) return false;
  if (result.type === "workspace") switchWorkspace(result.id);
  else if (result.type === "action" || result.type === "module") navigate(result.id);
  else return false;
  return true;
}

export function commandKeyAction({ key, selectedIndex, resultCount, inputFocused }) {
  const directions = { ArrowDown: "next", ArrowUp: "previous", Home: "first", End: "last" };
  if (directions[key]) return { handled: true, selectedIndex: nextCommandIndex(selectedIndex, directions[key], resultCount), execute: false };
  if (key === "Enter" && inputFocused) return { handled: true, selectedIndex, execute: resultCount > 0 };
  return { handled: false, selectedIndex, execute: false };
}
