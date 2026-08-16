export function canEnterWorkspace(state, session) {
  return state === "authenticated" && Boolean(session?.active_organization_id);
}

export function organizationChoices(session) {
  return Array.isArray(session?.organizations)
    ? session.organizations.filter((organization) => organization?.id && Array.isArray(organization.workspaces))
    : [];
}
