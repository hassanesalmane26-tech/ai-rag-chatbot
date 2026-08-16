# ADR 0002: Use typed, validated runtime configuration

- **Status:** Accepted — implemented by Sprint 7 Genesis
- **Date:** 2026-07-29
- **Owner:** TRIDENT architecture

## Context

Current configuration has unsafe defaults, no deployment-environment policy,
and process-wide direct access.

## Decision

Use one typed settings model with `TRIDENT_`-prefixed variables, secret-aware
fields, explicit validation, injected dependencies, and safe startup failure.
Production settings come from runtime environment or secret management, not
`.env` files.

## Consequences

Configuration becomes testable and auditable. Startup may reject settings the
prototype accepted; this is an intentional safety boundary.
