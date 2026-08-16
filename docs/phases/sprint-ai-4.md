# Sprint AI-4 — Audit, contracts, quotas and abuse protection

AI-4 adds governance around the existing Workspace-centered engines without
moving Identity, tenant authorization or product state out of their established
boundaries.

## Implemented

- additive migrations `0006_governance_controls` and
  `0007_audit_truncate_guard`;
- append-only, hash-chained Organization audit events with database triggers;
- owner/admin-only paginated audit read API;
- success events for sessions and Workspace mutations plus denied Workspace
  authorization events;
- bounded pagination for Workspaces, Conversations, Documents and Memory;
- stable API version, pagination and rate-limit headers;
- AI edition quota defaults, explicit Organization/User entitlements and
  durable hourly usage counters;
- resource quotas for Workspaces, Conversations, Documents and Memory;
- hourly message quota;
- bounded application fixed-window protection with health-check exemption.

Audit metadata never stores message, document or memory content. Entitlements
do not confer Membership or tenant access. The future Founder mechanism is an
explicit grant to a verified User, not an account name, email allowlist or
super-user role.

## Operational boundary

The in-process limiter is effective for the current single backend process. It
is not a distributed global limiter and intentionally does not trust
`X-Forwarded-For`. A trusted-proxy/edge policy and shared limiter are required
before horizontal production scaling. Audit export, retention, alerting and
database-administrator controls remain operational follow-up.

## Migration safety

A PostgreSQL custom-format backup was created before migration. Offline SQL
contained only new tables, indexes, the immutability trigger/function and the
Alembic revision update. Pre/post business row fingerprints and Workspace UUIDs
were identical. Governance tables started empty; no Founder grant was created.

## AI-5 handoff

AI-5 may replace local originals and request-bound ingestion behind the existing
Knowledge service. It must audit durable job transitions, apply storage/worker
quotas through this entitlement boundary, and preserve Workspace isolation and
current document UUIDs.
