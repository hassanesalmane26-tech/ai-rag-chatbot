# ADR 0014 — Durable Knowledge storage and leased jobs

Status: Accepted (AI-5)

## Context

PostgreSQL is authoritative, object originals must survive process restarts,
and Chroma is a derived Workspace-scoped index. A database transaction cannot
atomically commit PostgreSQL, object storage and Chroma together.

## Decision

- Originals are addressed by opaque, Workspace-prefixed storage keys behind an
  `ObjectStorage` boundary. The current local adapter writes atomically and is
  path-confined; S3-compatible activation requires an owner-configured client.
- `knowledge_jobs` is the durable idempotency and retry ledger. Workers claim a
  bounded lease; expired leases are recoverable after interruption.
- The existing synchronous API remains compatible by running the same durable
  job inline. `python -m app.knowledge.worker` is the external-worker seam.
- PostgreSQL records lifecycle and checksum metadata. Reconciliation only
  reports drift; it never silently deletes or rebuilds originals or vectors.
- Chroma stays derived, Workspace-filtered and replaceable behind its adapter.

## Consequences

Partial failure is visible and retryable. S3 cutover can migrate one verified
object at a time without changing document or Workspace UUIDs. Multi-worker
production needs PostgreSQL row-claim concurrency validation and a supervised
worker; the current deployment keeps inline processing until that is approved.

Downgrade is intentionally blocked because removing durable job state would
discard recovery evidence.
