# Sprint AI-5 — Durable production Knowledge infrastructure

## Result

AI-5 preserves the Documents API while introducing provider-neutral original
storage metadata and a durable, idempotent ingestion ledger. Workspace and
Organization IDs are carried by every job. Local writes are atomic and confined
under `documents/workspaces`; the existing directory remains untracked.

Migration `0008_durable_knowledge_jobs` adds storage metadata and the job table.
Migration `0009_audit_guard_reconciliation` idempotently restores the AI-4
PostgreSQL append-only guards after a verified schema adoption.

## Operations

- Inline processing remains the compatibility default.
- `python -m app.knowledge.worker --once` claims at most one available job.
- Omitting `--once` polls continuously and is intended for a supervisor.
- Reconciliation is read-only. Operators investigate checksum, missing-object
  and vector drift before any repair.

## Production reservation

No S3 provider, endpoint, bucket or credentials were supplied. The S3 boundary
therefore fails explicitly rather than falling back or pretending durability.
Production object-storage activation, malware scanning and a separately
supervised worker remain deployment actions. Existing Chroma content was not
rebuilt or re-embedded.

## Recovery note

During implementation, a legacy test module was found to bind the application
engine before setting its SQLite URL. It affected the development PostgreSQL
data. The backend was stopped immediately; the exact known test rows were
removed and the previously verified AI-4 logical backup restored. Counts,
Workspace UUIDs and pre-existing row fingerprints were then revalidated. The
test now owns a process-unique SQLite engine through a dependency override, so
the suite cannot target the runtime database.
