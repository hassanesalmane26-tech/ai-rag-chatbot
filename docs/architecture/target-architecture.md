# TRIDENT Architecture

## Purpose

TRIDENT is a modular, multi-tenant AI platform for grounded knowledge work. It
must support independently deployable capabilities, provider portability,
auditable data handling, and reliable operation as usage grows.

## Phase 0 baseline (2026-07-29)

The repository currently contains a React/Vite client and a FastAPI process.
The API synchronously handles chat, document upload, document deletion, and
full vector-index rebuilds. It uses OpenAI directly, SQLAlchemy for one global
`chat_messages` table, and a local Chroma directory for embeddings. Documents
are stored on the local filesystem. There is no identity, tenancy, migration
tooling, test suite, health/readiness contract, worker queue, or deployment
definition.

This is appropriate only as a local prototype. It is not a production platform
or a safe multi-user foundation.

## Target logical architecture

```text
Web / API clients
        |
Edge: TLS, WAF, rate limits, OIDC token validation
        |
API gateway / BFF
        |
  +-----+------+------+-------+---------+
  | Identity | Workspace | Conversation | Knowledge |
  +-----+------+------+-------+---------+
        |                 |              |
        |          AI orchestration       |
        |          (policy, retrieval,    |
        |           prompts, citations)   |
        +-------+---------+---------------+
                |         |
          relational DB   vector store
          object storage  queue + workers
                |
        observability / audit / secrets
```

## Architectural boundaries

- **Experience:** web and future clients use versioned HTTP APIs; they never
  access databases or AI providers directly.
- **Control plane:** identity, organizations/workspaces, authorization,
  configuration, billing/entitlements, and audit events.
- **Knowledge plane:** object ingestion, malware/type validation, extraction,
  chunking, embedding, indexing, retrieval, deletion, and provenance.
- **AI orchestration:** provider adapters, model policy, prompt assembly,
  retrieval policy, output controls, and evaluation telemetry.
- **Data plane:** relational system of record; object storage for original
  files; vector index derived from approved, versioned source content.
- **Operations plane:** deployment, secrets, telemetry, backups, incident
  response, and infrastructure policy.

Modules may begin as packages in a modular monolith. They become services only
when independent scaling, ownership, reliability isolation, or release cadence
requires it. Shared database access across future services is prohibited.

## Core data ownership

| Domain | System of record | Derived data |
| --- | --- | --- |
| Organizations, users, memberships, roles | Relational database | Authorization cache |
| Workspaces, conversations, messages | Relational database | Search/evaluation traces |
| Documents and versions | Object storage + relational metadata | Extracted text, chunks, embeddings |
| Retrieval index | Vector store | Rebuildable from approved document versions |
| Audit events | Append-only audit store | Operational dashboards |

Every tenant-owned record must include organization and workspace scope where
applicable. Every retrieval result must carry document-version provenance.

## Quality attributes

- Tenant isolation is enforced at the authorization and query layers.
- A provider outage must fail one capability gracefully, not corrupt data.
- Ingestion is asynchronous, idempotent, observable, and safe to retry.
- APIs are backward-compatible within a documented version lifecycle.
- Production data can be restored from tested backups and reconstructed
  indexes.
- AI answers surface citations and preserve an auditable request trace.
