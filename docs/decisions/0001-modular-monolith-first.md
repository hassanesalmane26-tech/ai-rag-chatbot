# ADR 0001: Start with a modular monolith

- **Status:** Accepted
- **Date:** 2026-07-29
- **Owner:** TRIDENT architecture

## Context

The current application is a small prototype. Premature microservices would add
deployment and operational complexity before domain boundaries are stable.

## Decision

Build the next platform phases as a modular monolith with explicit domain
packages and dependency rules. Public API, worker, and database boundaries are
designed for later extraction. Services may be split only with a documented
operational or scaling reason.

## Consequences

This preserves development speed while preventing a new ball of mud. It demands
enforced package boundaries, domain ownership, and no cross-domain persistence
shortcuts. Future extraction will require contract tests and data migration.

## Review trigger

Review when a module needs independent deploys, materially different scaling,
or a dedicated owning team.
