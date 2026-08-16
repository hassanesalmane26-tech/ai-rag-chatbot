# Security Baseline

## Current Genesis freeze risk assessment

Genesis validates upload names/types/sizes, generates storage names, scopes
current resources by Workspace, uses Alembic and has a recoverable ingestion
lifecycle. These are domain-integrity controls, not a tenant security boundary.

The current development/demo endpoint is HTTP and no real OIDC issuer is
configured. AI-1 added internal User/Organization/Membership persistence and
AI-2 added cryptographic OIDC verification plus systematic tenant
authorization. With the safe `disabled` default, `/api/v1` now fails closed
instead of exposing business data anonymously. The deployment still proxies a
Vite development server and uses local disk for originals and Chroma. It must
not receive sensitive or private data. TRIDENT AI production remains NO-GO
until AI-3 supplies a real issuer/session and controlled bootstrap claim, and
an approved domain enables TLS.

AI-0 restricts owner-controlled local secret/data permissions and records the
required edge hardening. It does not add fake authentication or claim that a
Workspace UUID is an access control.

## Mandatory controls by Phase 3

- Real OIDC deployment/session (AI-2 verification and Workspace authorization are implemented).
- Runtime secrets from a managed secret store; rotation and no secret logging.
- TLS in transit and managed encryption at rest for database/object/vector data.
- File size/type allowlists, generated object names, malware scanning, isolated
  extraction, and content safety limits.
- Request quotas, rate limits, timeouts, dependency circuit breakers, and abuse
  monitoring.
- Security headers/CORS policy, dependency and secret scanning, SBOMs, patch
  process, and least-privilege identities.
- Immutable audit events for authentication, authorization, data access,
  document operations, configuration changes, and administrative actions.

## AI-specific controls

Treat retrieved documents and user input as untrusted. Isolate instructions from
data, restrict tool permissions, minimize prompt data, apply output policy, log
only privacy-safe traces, and test prompt-injection and cross-tenant retrieval
resistance.

## Immediate operational controls before production

- Serve a production frontend artifact rather than Vite's development server.
- Terminate TLS at the edge after an owner-approved domain is available.
- Add `X-Content-Type-Options`, frame protection, a referrer policy and a tested
  Content Security Policy at the edge.
- Run backend and frontend through one documented supervisor; do not rely on a
  manually attached terminal session.
- Restrict runtime environment files, originals and vector data to the service
  identity and keep them outside Git.
- Protect or remove public OpenAPI documentation according to environment.
