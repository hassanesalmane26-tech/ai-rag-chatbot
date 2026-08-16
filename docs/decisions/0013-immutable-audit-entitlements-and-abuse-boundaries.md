# ADR 0013 — Immutable audit, entitlements and abuse boundaries

Status: accepted (Sprint AI-4)

## Decision

TRIDENT records security and business mutations in an append-only
`audit_events` table. Events are partitioned logically by Organization, carry
the verified internal actor, optional Workspace/resource, request correlation,
outcome and privacy-safe metadata, and form a SHA-256 predecessor chain. SQL
triggers reject `UPDATE`, `DELETE` and PostgreSQL `TRUNCATE`; there is no mutation API. Only owner and
admin Memberships can read their Organization's bounded audit feed.

Quotas are resolved through edition defaults plus explicit Organization or User
`entitlement_grants`. A future verified Founder may receive the
`ecosystem.full_access` entitlement with source `founder`; this changes quota
resolution only. It never creates Membership, bypasses Organization isolation,
or acts as a super-user. No Founder identity or grant is created by AI-4.

Durable hourly counters protect metered capabilities. Count-based resource
limits protect Workspaces, Documents and Memory. A bounded in-process fixed-
window limiter provides an immediate coarse abuse boundary; a distributed edge
limiter remains required for horizontally scaled production.

## API contract

List contracts use `limit`/`offset`, bounded to 1–100 items and an offset of at
most 100000. Responses preserve `{data, meta}` and expose total, limit, offset
and `has_more`. Responses carry `X-TRIDENT-API-Version: 1`; errors retain stable
codes and request IDs. Future cursor pagination may be added as a new contract,
not by silently changing v1 semantics.

## Threat model and consequences

Controls address audit tampering through application APIs, cross-tenant audit
disclosure, unbounded list extraction, direct resource exhaustion, quota
bypass and implicit privileged identities. Database administrators remain a
trusted operational boundary; backups and external log export are still
required. The current limiter deliberately ignores forwarded client-IP headers
because the proxy trust boundary is not configured in application code.
