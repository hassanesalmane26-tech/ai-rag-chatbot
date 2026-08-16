# TRIDENT Genesis v1.0.0 frozen baseline

## Release contract

This release freezes the Workspace-centric Genesis engineering foundation.
Home, Conversations, Knowledge, explicit Memory and the module registry are
implemented around persistent Workspace IDs. PostgreSQL is authoritative;
local originals and Chroma remain Genesis adapters.

The exact tag and commit are recorded by Git release operations. The release
tag is `trident-genesis-v1.0.0` with annotation `TRIDENT Genesis frozen
baseline`.

## Security boundary

Genesis is a non-sensitive development/demo edition. `/api/v1` is anonymous,
HTTP is currently used, and no membership/authorization boundary exists. This
release is not approved for sensitive or multi-user production use.

## Preserved data

The freeze does not alter PostgreSQL business rows, Workspace UUIDs, runtime
originals under `documents/workspaces/`, or Chroma. The runtime directory is
ignored and must never be committed.

Two files under the legacy top-level `documents/` directory were already
tracked before the freeze. They are unused by current code and tests and are
classified as potentially historical runtime material. AI-0 retains them to
avoid history rewriting or unreviewed deletion. Their extraction requires a
later owner-approved data-classification operation.
