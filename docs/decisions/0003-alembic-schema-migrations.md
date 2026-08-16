# ADR 0003: Use Alembic for schema migrations

- **Status:** Accepted — implemented by Sprint 7 Genesis
- **Date:** 2026-07-29
- **Owner:** TRIDENT architecture

## Context

The application creates schema at process startup, with no history, review, or
safe rollout path.

## Decision

Manage relational schema through immutable Alembic revisions run as a singleton
deployment migration job. Application startup will never mutate schema.

## Consequences

Deployments gain a schema step and migration tests. Every schema change needs a
reviewed revision and unsafe changes follow expand–migrate–contract.
