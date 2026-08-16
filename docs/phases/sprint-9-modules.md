# Sprint 9 — Module foundation

GENESIS now composes Workspace capabilities through explicit backend and
frontend registries. The registered set is deliberately limited to Home,
Conversations, Knowledge and Memory.

The backend exposes the resolved descriptors at
`GET /api/v1/workspaces/{workspace_id}/modules`. The frontend registry owns
navigation metadata and lazy view factories; `WorkspaceContext` still owns the
active Workspace and selected view.

This foundation does not implement entitlements, a marketplace, plugins,
automations, agents, or any PRO/NOVA-only capability.
