# ADR 0016 — Controlled Founder entitlement bootstrap

Status: Implemented; entitlement intentionally unclaimed

## Decision

Founder is not a user type, magic superuser, email allowlist or authorization
bypass. It is an auditable entitlement source applied to an existing internal
User that is already linked to a cryptographically verified external identity.
Organization/Workspace access continues to require explicit Membership.

The Founder service requires an exact issuer/subject mapping, matching
`AuthenticatedPrincipal`, active internal User, explicit active Organization and
`owner` Membership. Its planner is read-only. Assignment accepts only the
reserved `ecosystem.full_access` key and an explicit approval reference. It is
idempotent, permanent by default and appends an immutable audit event.

No HTTP/bootstrap route exists. The CLI is dry-run only and redacts the subject.
Activation is a host-level controlled operation after real OIDC verification.
Revocation requires an authenticated owner of the same Organization, an approval
reference, preserves the grant row and appends immutable evidence. A revoked
grant is never silently reactivated; recovery requires a reviewed procedure.

`ecosystem.full_access` affects quota/edition entitlements only. It never skips
OIDC, sessions, roles, tenant boundaries or audit.

Canonical creator attribution lives in `app.core.product` and is exposed as
public product metadata. Presentation attribution has no dependency on, and no
effect on, authorization.
