# TRIDENT AI transition architecture

## Frozen foundation

TRIDENT AI evolves from the tagged Genesis release. It does not replace the
Workspace shell or domain packages. Workspace remains the product aggregate;
Conversations, Knowledge, Memory and future modules remain capabilities inside
that boundary.

The following contracts are frozen unless superseded by an ADR: opaque IDs,
Workspace-nested `/api/v1` routes, PostgreSQL authority, derived vector indexes,
recoverable ingestion, explicit bounded Memory, the declarative module boundary,
and the existing visual/design system.

## Transition layers

```text
Experience: session bootstrap + existing Workspace shell
Control:    OIDC adapter + Principal + Organization + Membership + Roles
Domain:     AuthorizedWorkspace -> existing module services
AI:         provider adapters + prompt/retrieval policy + trace
Data:       PostgreSQL + object storage + derived vector index
Platform:   audit + telemetry + migrations + release controls
```

AI-1 adds the identity data model and provider-neutral interfaces. It stores
external `(issuer, subject)` identities separately from internal Users, creates
bounded Organization Memberships and exposes an internal tenant resolver. AI-2
makes that resolver mandatory before domain access. These are separate so the
data adoption can be verified before enforcement changes runtime behavior.

## Existing data adoption

AI-1 uses expand/backfill/contract migrations:

1. create identity, Organization and Membership tables;
2. create one initial migration Organization;
3. add a nullable `organization_id` to Workspaces;
4. attach every existing Workspace without changing its UUID;
5. verify row counts, foreign keys and ownership coverage;
6. represent the neutral bootstrap Organization as `legacy_unclaimed`, without
   inventing a User or Membership;
7. only in a later compatible revision make ownership mandatory.

No Genesis conversation, message, document, memory, original or vector is
rewritten during AI-0.

## Edition boundary

TRIDENT AI delivers identity, authorized Workspaces, secure Knowledge and
traceable AI orchestration. Entitlement interfaces and explicit module contracts
may prepare PRO/NOVA evolution, but governance suites, marketplaces, autonomous
agents and automations are not implemented in TRIDENT AI by anticipation.
