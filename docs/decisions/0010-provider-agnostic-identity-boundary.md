# ADR 0010: Add provider-agnostic identity around the Workspace boundary

- **Status:** Accepted — persistence and internal boundary implemented in AI-1
- **Date:** 2026-08-16
- **Owner:** TRIDENT architecture

## Context

Genesis has an implicit local owner. Opaque Workspace identifiers and nested
routes provide domain scoping, but they are not authentication or authorization.
TRIDENT AI must become multi-user without changing existing Workspace IDs or
coupling the product to one commercial identity provider.

## Decision

TRIDENT AI introduces `User`, `Organization`, `Membership` and `Role` as an
additive control-plane boundary. Every Workspace will belong to exactly one
Organization. Initial roles are `owner`, `admin` and `member`.

Authentication uses a provider-agnostic OIDC adapter. The server resolves this
chain before any tenant-owned data access or AI provider call:

```text
OIDC adapter -> CurrentPrincipal -> Organization membership
             -> AuthorizedWorkspace -> domain service
```

The browser cannot assert ownership by supplying a user or owner UUID. A module
descriptor is capability metadata, never an authorization decision.

Existing Genesis rows are adopted additively in AI-1: create one initial
Organization, associate every existing Workspace with it while preserving all
UUIDs and business data, verify the backfill, then tighten nullability in a
later compatible step. AI-0 performs no business-data mutation.

The migration Organization has the stable slug `trident-genesis` and explicit
state `legacy_unclaimed`. It has no fabricated User, Membership, email,
credential or external identity. `Workspace.organization_id` remains nullable
during the expand phase, while the migration and Genesis creation path populate
it. AI-2 must refuse an unowned Workspace rather than infer ownership.

Provider identities are stored separately from internal Users using unique
`(issuer, subject)` identifiers. Only a cryptographically verifying OIDC adapter
may produce a verified external identity. AI-1 exposes no bearer-token route and
ships an unavailable verifier by default.

## Consequences

- Existing Workspace-scoped APIs remain the product contract and gain an
  authorization dependency in AI-2.
- OIDC provider choice remains deployment configuration, not domain logic.
- Cross-user, cross-Organization and cross-Workspace denial tests become
  mandatory.
- Genesis remains anonymous and is not suitable for sensitive public use.
- The AI-1 tenant resolver is an internal service seam; existing anonymous
  Genesis routes do not call it and therefore are not represented as protected.

## Review trigger

Review when enterprise federation, custom roles or Organization hierarchies are
required. Those capabilities are not part of the initial TRIDENT AI scope.
