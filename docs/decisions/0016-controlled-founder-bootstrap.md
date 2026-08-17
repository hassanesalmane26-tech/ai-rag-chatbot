# ADR 0016 — Controlled Founder entitlement bootstrap

Status: Accepted as preparation; activation deferred to Founder phase

## Decision

Founder is not a user type, magic superuser, email allowlist or authorization
bypass. It is an auditable entitlement source applied to an existing internal
User that is already linked to a cryptographically verified external identity.
Organization/Workspace access continues to require explicit Membership.

AI-7 provides only a read-only planner. It requires an exact issuer/subject
mapping, active internal User and explicit `owner` Membership, and returns the
candidate IDs and `ecosystem.full_access` grant key. It never creates a User,
Membership or grant.

The dedicated Founder phase must add a controlled, idempotent transaction that
requires operator authorization, appends an immutable audit event and verifies
postconditions. The real issuer, subject, creator identity and product-language
approval must be supplied then. No personal email, UUID or identity is stored in
source.

`ecosystem.full_access` affects quota/edition entitlements only. It never skips
OIDC, sessions, roles, tenant boundaries or audit.
