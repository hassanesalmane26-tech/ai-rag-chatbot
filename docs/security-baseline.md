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
until a real issuer/client is configured, the controlled bootstrap claim is
performed, and an approved domain enables TLS. AI-3 implements the complete
Authorization Code + PKCE and opaque-session boundary, but does not invent
those deployment inputs.

AI-0 restricts owner-controlled local secret/data permissions and records the
required edge hardening. It does not add fake authentication or claim that a
Workspace UUID is an access control.

## Mandatory controls by Phase 3

- Real OIDC deployment (AI-2 verification/authorization and AI-3 session
  architecture are implemented; provider registration is pending).
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

AI-4 implements append-only hash-chained audit persistence, tenant-scoped audit
reads, explicit quota entitlements and an immediate application rate boundary.
Database triggers reject audit mutation. Distributed edge limiting, external
audit export/retention and alerting remain required for scaled production.

AI-5 confines local object keys, writes originals atomically and records leased,
idempotent Knowledge work in PostgreSQL. A production S3-compatible adapter,
malware scanning and worker service identity remain mandatory before accepting
sensitive uploads at scale.

Founder/Lifetime Access must be issued only as an explicit entitlement to a
cryptographically verified internal User. It never creates Membership or
bypasses Organization/Workspace authorization, and no Founder identity is
hardcoded or pre-created.

AI-7 adds a read-only Founder planner that additionally requires explicit owner
Membership. The separate bootstrap must be operator-authorized, idempotent and
immutably audited; it has not been executed.

## AI-specific controls

Treat retrieved documents and user input as untrusted. Isolate instructions from
data, restrict tool permissions, minimize prompt data, apply output policy, log
only privacy-safe traces, and test prompt-injection and cross-tenant retrieval
resistance.

AI-6 implements bounded prompt assembly, untrusted Knowledge/Memory delimiters,
Workspace metadata filtering and a provider-neutral invocation adapter. It does
not log prompt or retrieved content. External red-team evaluation, DLP/content
classification and provider retention configuration remain required.

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
