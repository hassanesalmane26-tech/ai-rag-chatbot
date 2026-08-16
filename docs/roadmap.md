# TRIDENT Roadmap

## Phase 0 — Foundation and governance (complete)

Document the baseline, target architecture, security posture, standards, and
delivery sequence. No runtime changes are made in this phase.

**Exit criteria:** this documentation set and ADR 0001 exist; known prototype
risks are recorded; implementation order is explicit.

## Phase 1 — Production foundation (core runtime foundation implemented)

Establish configuration validation, application lifecycle, structured logging,
health/readiness endpoints, API versioning, database migrations, automated
tests, CI quality gates, and a local containerized development environment.

**Exit criteria:** a clean environment can run the stack with documented
configuration; migrations replace startup schema creation; CI runs tests and
lint; health contracts distinguish liveness from dependency readiness.

Typed configuration, lifecycle, structured errors/logging, health contracts,
dependency pins and Alembic are implemented. Container and CI delivery
artifacts remain future operational work.

## GENESIS 1 — Workspace vertical slice (implemented)

GENESIS delivers a persistent, Workspace-centric local experience with Home,
Conversations, Knowledge, Workspace-scoped retrieval, citations, explicit
bounded Memory and a declarative module registry. Durable/idempotent local
ingestion is implemented behind the Knowledge boundary. It remains the product
vertical slice that precedes multi-user identity.

**Known boundary:** GENESIS is single-user/local. It is not a public-production
deployment until the roadmap security and production-foundation phases are done.

## Phase 2 — Identity and workspace isolation

Implement OIDC-compatible authentication, organization/workspace membership,
role-based authorization, tenant-scoped persistence, audit events, and
conversation ownership.

**Exit criteria:** every protected operation is authorized and tenant scoped;
cross-tenant access tests are present; audit events record security-relevant
actions.

## Phase 3 — Durable knowledge ingestion

Move original documents to object storage, introduce versioned metadata and
asynchronous ingestion jobs, secure file processing, idempotency, per-document
indexing, provenance, and deletion workflows.

**Exit criteria:** ingestion survives retries and worker restarts; no full
collection rebuild occurs for ordinary uploads/deletions; each retrieval result
can identify its source version.

## Phase 4 — AI orchestration and trust

Create provider adapters, model/prompt policy, retrieval controls, citations,
content safeguards, quotas, evaluations, and request tracing.

**Exit criteria:** provider selection is configuration-driven; answers provide
grounding metadata; quality and safety regressions are measurable.

## Phase 5 — Deployment and resilience

Deliver infrastructure-as-code, isolated environments, managed backing stores,
autoscaling workers, monitoring/alerting, backup/restore drills, disaster
recovery objectives, and release controls.

**Exit criteria:** deployments are repeatable; SLOs and alerts operate;
restoration and rollback procedures have been exercised.

## Phase 6 — Scale and platform expansion

Add enterprise governance, advanced retrieval, usage metering, multi-region
strategy as justified, integration framework, and selectively extract services
whose documented boundaries demand it.

## TRIDENT AI delivery sequence

Genesis is frozen before this sequence begins. Each sprint is additive and must
preserve Workspace IDs and business data.

### AI-0 — Genesis freeze and immediate security preparation

Publish and tag the validated baseline, protect runtime artifacts, record the
anonymous-demo boundary and create the dedicated `trident-ai` branch.

### AI-1 — Identity architecture and tenant model (implemented)

Add provider-neutral OIDC interfaces plus User, Organization, Membership and
the initial `owner`, `admin`, `member` role vocabulary. Adopt existing
Workspaces through verified expand/backfill migrations.

The provider-neutral contracts, tenant persistence, bootstrap adoption and
internal tenant resolver are implemented. Real OIDC verification and route
enforcement remain AI-2 work.

### AI-2 — Systematic Workspace authorization (implemented)

Resolve `CurrentPrincipal`, membership and `AuthorizedWorkspace` before every
tenant-owned data access or provider call. Add complete cross-tenant tests.

Asymmetric OIDC verification, fail-closed route protection, centralized role
policy and cross-tenant Workspace/module isolation are implemented. Real
provider login/session and controlled legacy ownership claim remain AI-3.

### AI-3 — Session and entry experience (implemented)

Add session bootstrap, Organization/Workspace entry and expiry behavior without
displacing the Workspace as the primary application surface.

Authorization Code + PKCE, cryptographically verified ID-token/nonce handling,
opaque revocable sessions, CSRF protection and server-authorized tenant
selection are implemented. Real provider registration, the controlled legacy
claim, domain and TLS remain deployment-owner prerequisites.

### AI-4 — Audit, API protection and contracts (implemented)

Add immutable audit events, pagination, quotas/rate limits, security policy and
OpenAPI compatibility gates.

Append-only hash-chained audit events, database immutability triggers, bounded
pagination, explicit entitlements, durable quotas, stable v1 headers and an
application abuse boundary are implemented. Distributed edge enforcement and
automated OpenAPI breaking-change comparison remain release/operations work.

### AI-5 — Durable production Knowledge infrastructure

Replace local originals and request-bound ingestion with object storage,
versioned metadata and durable idempotent jobs behind existing boundaries.

### AI-6 — AI orchestration and trust

Introduce provider adapters, model/prompt/retrieval policy, traceable citations,
safeguards and evaluation fixtures.

### AI-7 — Quality, CI and release candidate

Add PostgreSQL integration, browser/E2E/accessibility coverage, CI, security
scans, immutable artifacts and complete release validation.

PRO governance/connectors and NOVA agents/automations remain outside this
sequence. Only stable extension seams may be prepared.
