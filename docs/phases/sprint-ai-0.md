# Sprint AI-0 — Genesis freeze and security preparation

## Scope

AI-0 validates and publishes the Genesis baseline, records its immutable tag,
creates the `trident-ai` development branch and prepares the Identity boundary.
It makes no schema or business-data change and implements no authentication.

Repository protections exclude Workspace originals, vector state, local
backups, database dumps and environment variants. Owner-controlled runtime
files are restricted locally. System-level TLS, Nginx and supervisor changes
require privileged deployment access and remain explicit follow-up operations.

## Release gates

- full backend tests, Python compilation and dependency consistency;
- Alembic revision and read-only schema compatibility;
- frontend tests, lint and production build;
- repository diff/secret/runtime-artifact review;
- safe HTTP health and read-only API smoke tests;
- before/after PostgreSQL counts and filesystem/vector hashes.

## Exit boundary

The public endpoint remains a non-sensitive demo until AI-1 Identity and AI-2
authorization are complete. AI-0 stops after creating `trident-ai`; it does not
start Identity implementation.

## Freeze validation

The pre-freeze gate completed with 34 backend tests and 13 frontend tests
passing, clean frontend lint, a successful Vite production build, successful
Python compilation and dependency consistency, and no Git whitespace error.
Alembic reported `0003_workspace_memory (head)` and the read-only PostgreSQL
schema verifier reported no issue.

Existing business-table counts were 15 legacy chat messages, two Workspaces,
one conversation, zero Workspace messages, one Workspace document and zero
Workspace memories. Chroma contained eight records. Content hashes were captured
before hardening so the post-freeze check can prove that no original or vector
content changed.

Local `.env`, document and vector permissions were reduced to owner-only access.
The executing account did not have non-interactive privileged access, so no
Nginx or systemd change was attempted. The precise privileged transition is
documented in the edge hardening plan.
