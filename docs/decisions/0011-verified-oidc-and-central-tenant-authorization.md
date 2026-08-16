# ADR 0011 — Verified OIDC and centralized tenant authorization

Status: accepted (Sprint AI-2)

## Decision

TRIDENT accepts an external identity only after asymmetric JWT verification at
the OIDC boundary. Configuration fixes the HTTPS issuer, audience and an
explicit asymmetric algorithm allowlist. Signing keys are obtained from an
explicit HTTPS JWKS URI or from issuer metadata whose `issuer` value must match
exactly. Signature, issuer, audience, `exp`, `iat`, optional `nbf`, and a
non-empty `sub` are validated before an `ExternalIdentity` can resolve a
TRIDENT `User`.

FastAPI dependencies then resolve one `AuthenticatedPrincipal` and a reusable
`TenantContext`. Workspace authorization joins `Workspace.organization_id` to
an active `Organization` and the principal's `Membership` before handlers read
business objects or call providers. Workspace administration requires `owner`
or `admin`; all three roles may use current Workspace capabilities. Unknown or
cross-tenant Workspace UUIDs return a generic denial.

## Security mode

`disabled` is the fail-closed default: health/root remain public and `/v1`
returns `AUTHENTICATION_UNAVAILABLE`. Staging and production configuration is
invalid unless the mode is `oidc` with an HTTPS issuer and audience. There is
no anonymous compatibility mode, identity header, unsigned-token path, or
runtime test bypass.

## Bootstrap ownership

The legacy Organization stays `legacy_unclaimed`. The internal
`claim_legacy_organization` service accepts only a `VerifiedExternalIdentity`,
atomically creates or links the internal identity and owner Membership, then
activates the Organization. It is deliberately not an HTTP endpoint. An owner
must configure a real issuer and run a controlled operator procedure in AI-3;
no authenticated user is assigned automatically.

## Consequences

- AI-2 adds no database migration; schema head remains `0004_identity_tenancy`.
- No profile claim, email address, browser UUID, or provider role grants access.
- Provider login/session acquisition remains AI-3.
- Immutable audit events, quotas and edge rate limiting remain AI-4.
