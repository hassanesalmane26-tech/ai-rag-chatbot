# Sprint AI-6 — AI orchestration, trust and production resilience

## Implemented

- Provider-neutral model contracts and OpenAI Responses adapter.
- Workspace-scoped orchestration with bounded Knowledge/Memory context,
  explicit untrusted-data delimiters and traceable citations.
- Readiness checks PostgreSQL, exact Alembic head and original-storage access;
  liveness remains process-only.
- `python -m app.operations.preflight` provides a non-mutating schema, storage
  and production-artifact check.

## Production and recovery

Build the frontend once with `npm ci && npm run build`; deploy immutable
`frontend/dist` behind the edge. Run API and Knowledge worker as separate
least-privilege supervised processes from the same source/image and build SHA.
Apply migrations as a one-shot pre-deploy task, never at API startup.

For a restore drill: quiesce writes; capture an access-restricted custom-format
`pg_dump` plus original-object snapshot; record revision, UUIDs, counts and
checksums; restore only into an isolated database/bucket; run migrations and
preflight; compare evidence; then exercise one authorized vertical slice.
Never test recovery by overwriting live data.

## Reservations

The owner must define RPO/RTO, retention and encryption. Real OIDC registration,
domain/TLS, S3 credentials, managed telemetry, supervised units and edge WAF
remain owner actions. No Nginx, systemd, DNS, firewall or TLS change was made.
