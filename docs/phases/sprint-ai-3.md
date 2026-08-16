# Sprint AI-3 — Session and entry experience

AI-3 adds a real provider-neutral browser entry boundary while preserving the
Workspace as TRIDENT's primary product surface.

## Implemented flow

`POST /v1/session/login` creates a one-time login transaction and returns the
provider authorization URL. The OIDC callback exchanges the code with PKCE,
verifies the ID token and nonce, resolves the internal identity, and creates an
opaque application session. `GET /v1/session` returns only server-authorized
Organization/Workspace choices. `POST /v1/session/context` records that
selection after Membership validation. `POST /v1/session/logout` revokes the
session locally before optionally returning a provider logout URL.

The frontend entry gate represents disabled, anonymous, error, no-membership
and selection states. It does not contain provider branding, tokens, test
users, or a fake login. Once a tenant is selected, the existing Workspace-first
application is mounted unchanged.

## Persistence and migration

Alembic `0005_oidc_sessions` additively creates `oidc_login_transactions` and
`application_sessions`. It does not modify existing business tables or UUIDs.
The downgrade intentionally refuses destructive removal of session history.

During validation, the additive migration was inadvertently executed against
the development PostgreSQL database before the planned pre-migration backup.
Inspection confirmed that only the two empty session tables and their
constraints/indexes were created. All recorded business counts, UUIDs and
content fingerprints remained identical. A post-migration `pg_dump` was then
created and verified. No rollback or destructive correction was attempted.

## Deployment boundary

No real OIDC issuer/client/domain was supplied. Runtime configuration therefore
remains `disabled`; session login is unavailable and business APIs fail closed.
Production activation requires an owner-selected issuer, registered callback
and logout URIs, a controlled legacy Organization claim, and HTTPS. The current
HTTP/Vite demo environment remains unsuitable for sensitive data.

## AI-4 handoff

Add immutable authentication/authorization audit events, cleanup/retention for
expired sessions and login transactions, rate-limit/abuse controls, pagination,
quotas and OpenAPI contract gates. Do not move these responsibilities into the
Workspace engines.
