# Sprint 4 — Workspace Engine

## Decision

Sprint 4 establishes Workspace as the authoritative GENESIS runtime boundary. The relational database remains the source of truth for Workspace identity and ownership; `workspace_id` remains mandatory at every Workspace-scoped backend route. The browser persists only an active Workspace preference and validates it against the backend list at boot.

## Scope delivered

- Workspace list, read, create, rename/update and selection are supported. Deletion and archiving are intentionally deferred.
- `WorkspaceProvider` owns the active selection, loading, error and mutation states. There is no independent selector-local active state.
- Boot selects a valid persisted Workspace when present, otherwise the backend-provided default. A stale stored identifier falls back safely to the first returned Workspace.
- Workspace switches invalidate stale list/detail responses in Conversations and Documents. Late responses cannot replace data belonging to the newly active Workspace.
- Conversations and documents keep using nested Workspace routes. Backend ownership checks remain the isolation authority.

## API contract

| Method | Route | Responsibility |
| --- | --- | --- |
| GET | `/api/v1/workspaces` | Lists authoritative Workspaces; bootstraps GENESIS default when none exists. |
| POST | `/api/v1/workspaces` | Creates a Workspace with server-generated opaque identity. |
| GET | `/api/v1/workspaces/{workspace_id}` | Reads one Workspace. |
| PATCH | `/api/v1/workspaces/{workspace_id}` | Renames or updates description; rejects an empty patch or blank name. |
| GET/POST | `/api/v1/workspaces/{workspace_id}/conversations` | Keeps conversations within their owner Workspace. |
| GET/POST/DELETE | `/api/v1/workspaces/{workspace_id}/documents...` | Keeps document metadata and operations within their owner Workspace. |

## Invariants

1. `workspace_id` is a stable business boundary, not a frontend filter.
2. A conversation or document requested through another Workspace returns `404` and is never exposed.
3. Vector retrieval used by conversations filters `workspace_id`; the vector store is derived data, while relational metadata is authoritative.
4. No Workspace can be selected until it exists in the latest authoritative list.
5. A rejected/stale browser preference cannot make the application request resources for an invalid Workspace.

## Deferred deliberately

- Delete/archive semantics and cascade policy.
- URL-addressable Workspace routes and browser history integration.
- Collaboration, roles, editions, quotas, Projects, Agents, Memory and Automations.
- Sprint 5 conversation behavior and Sprint 6 document workflow expansion.
- Database migrations: no schema change was required; the existing Workspace table and foreign keys support the approved scope.

## Roadmap compatibility

TRIDENT AI, PRO and NOVA can extend a Workspace through capability/module metadata and ownership-bound resources without changing the stable `workspace_id` boundary or nesting contract. Any future multi-user authorization must be enforced before the existing Workspace ownership checks, never replaced by frontend visibility rules.
