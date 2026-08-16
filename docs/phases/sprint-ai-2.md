# Sprint AI-2 — Security, authentication and authorization

AI-2 protects the existing Workspace-centered modular monolith without
redesigning its engines or UI.

## Implemented boundary

The runtime can construct a provider-neutral OIDC verifier using issuer
discovery or an explicit JWKS URL. Only asymmetric algorithms from a bounded
allowlist are accepted. Bearer extraction is strict; validation and public
errors fail closed without exposing verification details. Verified
issuer/subject pairs resolve through `external_identities` to an active internal
User.

Every `/v1` route requires a principal. Workspace routes additionally resolve
Membership and Organization before any Workspace, Conversation, Document,
Memory, Module or provider access. Workspace listing is membership-filtered;
creation targets one explicit or unambiguous active Organization and requires
owner/admin. Existing nested resource checks remain as defense in depth.

## Configuration

Use the safe names documented in `.env.example`: security mode, HTTPS issuer,
audience, optional JWKS URL, asymmetric algorithm allowlist, bounded clock skew
and timeout, and exact comma-separated CORS origins. Wildcard CORS origins and
symmetric OIDC algorithms are rejected. CORS is off when no cross-origin
browser origin is configured. API responses receive `nosniff`, frame denial
and no-referrer headers. OpenAPI/docs are disabled in staging/production.

## Current deployment condition

No real issuer, audience, domain or owner identity was supplied. Therefore the
current safe default is `disabled`: business APIs are unavailable, not
anonymous. The checked-in frontend has only an access-token provider seam; it
does not acquire, persist or fabricate a session. Public authenticated
production remains **NO-GO** until AI-3 configures a real OIDC client/session,
the owner claim is executed under a verified identity, and domain/TLS are
validated.

No PostgreSQL schema change, Chroma operation, re-embedding, document mutation,
or infrastructure change belongs to AI-2.

## Role policy

| Capability | owner | admin | member |
| --- | --- | --- | --- |
| Read/use Workspace modules | yes | yes | yes |
| Conversations, Knowledge, Memory | yes | yes | yes |
| Create/rename Workspace | yes | yes | no |

Membership and role administration have no public route in AI-2.

## AI-3 handoff

Select/configure a standards-compliant OIDC issuer, register the browser client
and callback origins, implement Authorization Code + PKCE/session expiry, then
perform the controlled legacy claim. Tokens must be delivered through
`setAccessTokenProvider`; they must not be put in URLs or treated as identity
without backend verification.
