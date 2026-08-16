# Sprint 7 — Durable GENESIS ingestion

## Scope

The Knowledge module keeps synchronous execution in GENESIS while gaining a
recoverable, idempotent lifecycle. PostgreSQL owns document state; the local
original is durable input; Chroma is Workspace-filtered derived data.

## State and retry contract

```text
pending -> processing -> indexed
                    \-> failed -> processing (retry)
indexed/failed -> deleting -> removed
                         \-> delete_failed -> deleting (retry)
```

Uploads are content-addressed by SHA-256 within one Workspace. Chunk IDs are
deterministic from document ID, version and position. A retry removes only that
document's vectors before re-indexing; no collection-wide reset is used.

`POST /api/v1/workspaces/{workspace_id}/documents/{document_id}/retry` retries a
failed or interrupted document. Repeating deletion is safe while metadata still
exists. API serialization adds provenance and attempt fields without removing
existing fields.

`audit_workspace_knowledge` provides a read-only reconciliation report for
missing or inconsistent originals, missing vectors, and orphaned files/vectors.
It never repairs automatically: recovery is an explicit operation through the
document retry/deletion contracts, preserving PostgreSQL authority.

## Deployment safety

Revision `0002_durable_document_ingestion` is additive. Do not run it on the
existing VPS database until the baseline adoption protocol is completed and a
recoverable backup exists. The application never migrates automatically.

The real database and Chroma collection were inspected read-only during
development. Neither was stamped, migrated, reset, or rebuilt.
