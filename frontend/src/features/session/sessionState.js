export function canEnterWorkspace(state, session) {
  return state === "authenticated" && Boolean(session?.active_organization_id);
}

export function organizationChoices(session) {
  return Array.isArray(session?.organizations)
    ? session.organizations.filter((organization) => organization?.id && Array.isArray(organization.workspaces))
    : [];
}

export function needsPersonalOnboarding(session) {
  return organizationChoices(session).length === 0;
}

export function membershipRoleLabel(role) {
  return ({ owner: "Propriétaire", admin: "Administrateur", member: "Membre" })[role] || "Membre";
}
