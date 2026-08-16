# ADR 0008: Use explicit bounded Workspace memory in GENESIS

- **Status:** Accepted
- **Date:** 2026-08-16
- **Owner:** TRIDENT architecture

## Context

TRIDENT needs a Memory foundation that remains Workspace-centric and can evolve
without turning entire conversation histories into an opaque permanent store.
GENESIS has no identity layer or autonomous memory policy.

## Decision

GENESIS Memory consists only of explicit records created, edited, activated and
deleted by the local user. Every record belongs to a Workspace and may optionally
be narrowed to one conversation. Records have a small controlled kind, title and
bounded content.

Chat context assembly selects active Workspace records plus records scoped to
the current conversation, newest first, with strict record and character limits.
Memory is presented to the model as untrusted contextual data, never as system
instructions. No automatic extraction or silent persistence is performed.

## Consequences

- Workspace isolation is enforceable and testable at every Memory route.
- Deletion and updates are deterministic relational operations.
- Future editions can add policies, provenance, embeddings or approvals without
  changing the stable Workspace ownership contract.
- GENESIS intentionally does not infer, summarize or rank memories using AI.

## Review trigger

Review when identity/authorization, automated memory proposals or semantic
retrieval are introduced.
