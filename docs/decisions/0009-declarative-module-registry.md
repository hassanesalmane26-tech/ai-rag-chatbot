# ADR 0009: Use declarative edition-aware module registries

- **Status:** Accepted
- **Date:** 2026-08-16
- **Owner:** TRIDENT architecture

## Context

TRIDENT is a Workspace Operating System, but GENESIS navigation and overview
hardcode feature lists in multiple components. Adding future capabilities this
way would couple the Workspace shell to every module and invite edition checks
throughout presentation code.

## Decision

Define small declarative registries at the backend contract and frontend
composition boundaries. A descriptor owns stable identity, label, route/view,
edition availability, order and status. The Workspace shell consumes the
registry; domain modules continue to own their own state and persistence.

GENESIS registers only Home, Conversations, Knowledge and the approved explicit
Memory foundation. It does not ship dormant PRO/NOVA implementations. Frontend
module views are lazy-loaded through registry factories. Backend descriptors are
immutable and exposed through a Workspace-scoped read endpoint.

## Consequences

- Future editions can add descriptors without rewriting WorkspaceContext or the
  shell router.
- A registry is metadata/composition, not a service locator and not permission
  enforcement. Future authorization remains server-side.
- Modules may not import each other's persistence internals.

## Review trigger

Review when entitlements, user-installable modules or remote module packages are
introduced.
