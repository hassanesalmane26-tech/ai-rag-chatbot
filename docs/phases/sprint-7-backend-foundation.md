# Sprint 7 — Backend Foundation

## Scope

This tranche adds typed configuration, a deterministic FastAPI lifecycle,
structured error correlation, reproducible direct dependencies, and an Alembic
baseline. It does not change product data, ingestion behavior, Chroma, frontend
contracts, or infrastructure.

## Existing PostgreSQL adoption

`0001_genesis_baseline` creates the complete GENESIS schema only for an empty
database. It must never be upgraded against the populated VPS database because
those tables already exist.

Adoption is an explicit deployment operation, not application startup:

1. Back up PostgreSQL using the established operational procedure.
2. Run the read-only `verify_genesis_schema(engine)` check and inspect any issue.
3. Confirm the five GENESIS tables and row counts are unchanged.
4. Run `alembic stamp 0001_genesis_baseline` once. Stamping creates only the
   Alembic version marker; it runs no baseline DDL.
5. Run `alembic upgrade head` to apply only the reviewed additive revisions.
6. Run `alembic current`, the read-only schema verifier, row-count checks and
   the application integration tests.

The application does not stamp or migrate automatically. In this implementation
session the real VPS database was initially inspected only. Any later adoption
must be recorded in the final operational report with its backup and checks.
The baseline downgrade intentionally refuses to drop tables.

## Compatibility

Legacy environment variables (`DATABASE_URL`, `OPENAI_API_KEY`, `DEBUG`, and
related optional names) remain accepted while `TRIDENT_` names become canonical.
The existing `/v1` product routes and error envelope remain compatible.
