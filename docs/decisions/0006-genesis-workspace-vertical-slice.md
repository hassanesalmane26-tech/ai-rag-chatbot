# ADR 0006: Deliver GENESIS as a Workspace vertical slice

- **Status:** Accepted
- **Date:** 2026-07-30
- **Owner:** TRIDENT architecture

## Context

TRIDENT’s visible prototype exposed a global chat and a global document folder.
This contradicted the product direction: Workspace is the core product and chat
is one capability.

## Decision

GENESIS introduces persistent Workspaces, Workspace-scoped conversations,
messages, documents, retrieval, citations, and a real Workspace cockpit. It is
explicitly single-user/local, but uses opaque IDs and domain boundaries that
support later identity and tenancy.

## Consequences

The browser can no longer be the source of truth for Workspaces or
conversations. Local file and synchronous indexing remain temporary GENESIS
implementations behind the Knowledge boundary; Phase 3 replaces them with
object storage and asynchronous jobs.
