# TRIDENT GENESIS Blueprint

## Product boundary

GENESIS is the single-user, local edition of the TRIDENT AI Operating System.
Its primary object is a **Workspace**; chat is one Workspace capability beside
Knowledge. The product exposes only three functional modules: Home,
Conversations, and Knowledge.

```text
Workspace
  ├─ Home: real counts and entry points
  ├─ Conversations: conversation history and AI messages
  └─ Knowledge: Workspace-scoped source documents
```

Every conversation, message, document, retrieval query, and citation is scoped
by an opaque Workspace UUID. GENESIS has an implicit local owner only; that is
not an authorization model and it must not be deployed publicly.

## Public API

Product routes are nested below `/api/v1/workspaces/{workspace_id}`. The public
resources are Workspace, Conversation, Message, Document, Citation, and an
Overview projection. API responses use `{ "data": ..., "meta": {} }`; errors
use a stable `{ "error": { "code", "message", "request_id" } }` envelope.

## Data and component ownership

The relational database is authoritative for Workspace metadata, conversations,
messages, and document metadata. Workspace files are held behind a storage
boundary; local disk is the GENESIS implementation. The vector index is derived
from approved document content and can be rebuilt. The browser only owns
presentation state and calls the API through one client module.

## GENESIS flow

1. The first list request bootstraps the `TRIDENT GENESIS` Workspace.
2. A document is validated, stored beneath its Workspace directory, indexed with
   Workspace and Document metadata, and shown in Knowledge.
3. A message is persisted, retrieves chunks filtered by Workspace ID, invokes
   the AI provider through the conversation application flow, then stores the
   assistant response with citations.
4. Home reads real counts from the same persisted resources.

## Evolution contracts

TRIDENT AI adds Organizations, Users, Memberships, and authorization around the
existing Workspace IDs. TRIDENT PRO adds governance, quotas, connectors, and
advanced Knowledge without bypassing the Workspace boundary. NOVA adds agents,
automations, and auditability; every execution remains Workspace-scoped and
acts through explicit permissions.
