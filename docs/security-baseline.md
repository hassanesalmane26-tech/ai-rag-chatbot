# Security Baseline

## Current risk assessment

The Phase 0 prototype has critical production gaps: no authentication or tenant
isolation; arbitrary uploaded filenames are written beneath a local directory;
uploads are synchronously processed; data and indexes are local; database
configuration has no safe deployment contract; debug defaults to enabled; and
chat history is globally shared. Do not expose this implementation publicly or
use it with sensitive data.

## Mandatory controls by Phase 3

- OIDC authentication, server-side authorization, and workspace-scoped queries.
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
