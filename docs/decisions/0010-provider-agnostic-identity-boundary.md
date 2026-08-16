# ADR 0010: Add provider-agnostic identity around the Workspace boundary

- **Status:** Accepted for TRIDENT AI architecture; implementation begins in AI-1
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

## Consequences

- Existing Workspace-scoped APIs remain the product contract and gain an
  authorization dependency in AI-2.
- OIDC provider choice remains deployment configuration, not domain logic.
- Cross-user, cross-Organization and cross-Workspace denial tests become
  mandatory.
- Genesis remains anonymous and is not suitable for sensitive public use.

## Review trigger

Review when enterprise federation, custom roles or Organization hierarchies are
required. Those capabilities are not part of the initial TRIDENT AI scope.
