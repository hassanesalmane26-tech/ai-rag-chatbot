# ADR 0004: Version product APIs in the path

- **Status:** Accepted — implemented by the Genesis Workspace API
- **Date:** 2026-07-29
- **Owner:** TRIDENT architecture

## Context

Prototype routes are unversioned and will evolve as tenancy and durable
ingestion are introduced.

## Decision

Expose product endpoints below `/api/v1`; retain separate stable health
endpoints. Manage compatibility through OpenAPI contracts and deprecation policy.

## Consequences

Route and frontend-base changes require a later implementation phase. Breaking
changes use a new API version rather than silently changing client behavior.
