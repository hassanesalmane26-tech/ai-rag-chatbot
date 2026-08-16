# ADR 0007: Make GENESIS ingestion recoverable and idempotent

- **Status:** Accepted
- **Date:** 2026-08-16
- **Owner:** TRIDENT architecture

## Context

GENESIS currently writes document metadata, a local original, and Chroma chunks
inside one synchronous request. These systems cannot share one transaction. A
failure can therefore leave duplicate vectors, an orphaned file, or metadata
that no longer explains what happened.

## Decision

Keep synchronous execution for GENESIS, but introduce a durable ingestion state
machine behind the Knowledge service boundary. PostgreSQL remains authoritative.
Originals are written atomically, content is identified by SHA-256 within a
Workspace, vector chunk identifiers are deterministic, and every retry first
removes the document's derived chunks before indexing them again.

The states are `pending`, `processing`, `indexed`, `failed`, `deleting`, and
`delete_failed`. Failed ingestion preserves the original for retry. Failed
deletion preserves relational metadata until both derived vectors and the local
original have been removed. A retry endpoint is Workspace-scoped.

This is deliberately not a worker architecture. The service contract and
persistent attempt metadata provide the seam for a future queue without making
GENESIS depend on one.

## Consequences

- Duplicate uploads with the same Workspace/content hash return the existing
  document instead of creating duplicate metadata or vectors.
- Chroma remains rebuildable derived data and is never globally reset.
- Local disk remains the GENESIS storage adapter; managed object storage can
  replace it behind the same service boundary.
- An additive migration is required before deploying this code. Existing rows
  remain valid with nullable hashes and version `1`.
- Ordinary deletion can now return a dependency error instead of silently
  discarding authoritative metadata after a partial failure.

## Review trigger

Supersede this decision when ingestion moves to durable workers/object storage,
while retaining the state, idempotency, provenance, and Workspace contracts.
