# Sprint 8 — Explicit Workspace Memory

GENESIS Memory is a Workspace module for a small set of user-controlled notes,
preferences and facts. It is relational, Workspace-scoped, optionally scoped to
a conversation, and never populated automatically.

The API supports list, create, update and delete below
`/api/v1/workspaces/{workspace_id}/memories`. Cross-Workspace access returns
`404`. Context assembly includes at most 12 active records and 4,000 characters,
and labels the content as untrusted data.

The frontend module owns only presentation/request state. `WorkspaceContext`
continues to own Workspace selection and navigation. Memory does not import Chat
or Knowledge persistence internals.
