# ADR 0012 — Authorization Code + PKCE and opaque application sessions

Status: accepted (Sprint AI-3)

## Decision

TRIDENT uses the OIDC Authorization Code flow with PKCE (`S256`) through a
backend-for-frontend boundary. The backend creates unpredictable state, nonce
and verifier values, performs provider discovery and the code exchange, then
verifies the ID token cryptographically through the provider-neutral AI-2
verifier. The browser never receives OIDC tokens.

Successful verification creates or resolves an internal User and
ExternalIdentity, but never grants Membership. TRIDENT issues an opaque,
HttpOnly application-session cookie whose digest is persisted. Unsafe
cookie-authenticated requests also require a separate double-submit CSRF token.
Sessions have an absolute expiry, can be revoked by logout, and store only a
server-validated active Organization and Workspace selection.

## Security properties

- Login transactions are single-use, short-lived and bound to a browser cookie.
- Issuer metadata must match the configured issuer and expose HTTPS endpoints.
- State, signature, issuer, audience, nonce, expiry and subject are validated.
- Session and CSRF secrets are stored only as SHA-256 digests.
- OIDC access and ID tokens are not persisted.
- Existing bearer verification remains available for non-browser clients.
- An identity without Membership sees no Organization and cannot claim the
  legacy bootstrap Organization through an HTTP route.

The default `disabled` mode remains fail-closed. A real issuer, registered
client, callback URI, controlled bootstrap claim, domain and TLS configuration
remain deployment-owner actions.

## Consequences

Migration `0005_oidc_sessions` adds only login-transaction and application-
session tables. It does not alter Workspace or business rows. Expired-row
retention and immutable authentication audit events are deferred to AI-4.
