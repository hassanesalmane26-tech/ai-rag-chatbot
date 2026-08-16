# Sprint 6 — Documents Engine

## Status

Implemented on the GENESIS branch after the validated Sprint 5 Chat Engine.

## Scope

Sprint 6 turns the existing Workspace-scoped Knowledge vertical slice into a
cohesive Documents Engine without changing the persistence or public API
boundaries established by GENESIS.

- Document state and mutations live in a dedicated Workspace-aware hook.
- Late list and mutation responses are ignored after a Workspace switch.
- Client-side validation mirrors the API contract for PDF, TXT and DOCX files
  up to 20 MiB; the server remains authoritative.
- Loading, upload, deletion, empty, error, indexed and failed states are visible.
- The upload surface supports file selection and drag-and-drop while remaining
  keyboard accessible through the native file control.
- Mobile Knowledge reserves the bottom-navigation safe area, keeps document
  actions touch-sized, and lets long source names wrap without hiding actions.
- Pure collection, validation and presentation helpers have deterministic tests.
- Existing local document files and derived vector data are never modified by
  frontend lifecycle behavior.

## Architecture boundary

The hook owns remote interaction state, the view owns presentation interaction,
and pure helpers own deterministic transformations. `WorkspaceContext` remains
the authority for the active Workspace; Documents never introduces parallel
global state.

Durable object storage, versioned document provenance, asynchronous ingestion,
malware inspection and reconciliation remain Phase 3 work. They are not hidden
inside this UI sprint.

## Validation

- Frontend production build.
- Frontend lint.
- Chat Engine regression tests.
- Documents Engine unit tests.
- Backend Genesis API and Knowledge service tests.
