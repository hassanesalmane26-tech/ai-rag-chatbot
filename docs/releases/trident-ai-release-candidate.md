# TRIDENT AI release candidate

Status: V1 owner review candidate

TRIDENT AI is the Workspace-centric AI Operating System release candidate built
additively on the frozen Genesis engineering baseline. The active product
surface is branded TRIDENT AI; Genesis names remain only in immutable historical
records, migration compatibility, and the frozen baseline tag.

The V1 candidate preserves the declarative module registry and presents Home,
Nova, Knowledge, Memory, Files, Artifacts, Activity and Settings as capabilities
inside the authorized Workspace. The command palette provides module navigation,
Workspace switching and a direct path to Nova without pretending to offer a
cross-domain search backend. Product onboarding is presentation-only local state;
it has no authorization or tenant-selection role.

Files is a presentation/service layer over authoritative Knowledge document
originals, with a server-authorized Workspace-nested download route. Activity is
a sanitized, allowlisted Workspace projection of immutable audit events; actor,
request, hash and metadata internals are never returned. Artifacts intentionally
defines a truthful empty V1 surface because no durable generation contract exists.
OIDC Authorization Code with PKCE, opaque sessions, CSRF enforcement,
database-authoritative tenant authorization, and controlled Founder entitlement
boundaries remain unchanged.

Release acceptance requires the supported backend unit/integration suite,
frontend lint and tests, a production frontend build, and a clean diff check.
Infrastructure changes, deployment, release tagging, and production operations
remain separate owner-controlled actions.

## V1 acceptance checklist

- [x] Workspace remains the primary product object on desktop, tablet and mobile.
- [x] Nova, Knowledge and explicit Memory retain their existing service boundaries.
- [x] Files, Activity, Settings and the command surface are useful and recoverable.
- [x] Artifacts distinguishes future generated outputs from uploaded Files without fake data.
- [x] OIDC, PKCE, CSRF, opaque sessions, Founder isolation and database authorization are unchanged.
- [x] New read endpoints are Workspace-scoped and covered by cross-tenant tests.
- [x] No schema migration, infrastructure change, deployment or production mutation is required.

## Deliberately deferred

Multi-model NOVA CORE, agent runtime, Deep Research, connectors, artifact
generation/persistence, unified full-text Workspace search, notification delivery,
and PRO/NOVA governance systems remain outside TRIDENT AI V1.

Created by Salmane Hassan

A TRIDENT Project
