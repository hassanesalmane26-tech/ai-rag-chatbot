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
