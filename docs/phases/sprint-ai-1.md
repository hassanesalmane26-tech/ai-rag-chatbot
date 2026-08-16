# Sprint AI-1 — Identity architecture and tenant model

## Implemented boundary

AI-1 adds provider-neutral Identity and tenant persistence without presenting
Genesis as authenticated. Internal Users are independent from external OIDC
subjects. Organizations own Workspaces through a staged nullable foreign key,
and Memberships bind Users to Organizations with the bounded roles `owner`,
`admin` and `member`.

```text
IdentityVerifier -> VerifiedExternalIdentity -> IdentityService
                 -> AuthenticatedPrincipal -> TenantContext
                 -> Organization/Membership -> Workspace
```

No HTTP Identity or Organization administration endpoint is added. The default
verifier always reports that authentication is unavailable; it does not decode
or trust JWT claims. AI-2 will provide a verified OIDC adapter and wire the
tenant resolver before every protected domain access.

## Persistence

Revision `0004_identity_tenancy` creates `users`, `external_identities`,
`organizations` and `memberships`, then adds nullable
`workspaces.organization_id`. The schema constrains Organization slugs,
external issuer/subject uniqueness, one Membership per User/Organization and
the initial role vocabulary.

For a database containing Genesis Workspaces, the migration creates one neutral
Organization:

```text
name: TRIDENT Genesis
slug: trident-genesis
ownership_state: legacy_unclaimed
```

Every existing Workspace is associated with it without changing a Workspace
UUID. No User, Membership, email, password or external identity is fabricated.
The same bootstrap service assigns this Organization to Workspaces created by
the still-anonymous Genesis compatibility API.

The runtime never silently adopts a pre-existing unowned Workspace. Such a row
causes an explicit failure and must be reconciled through the reviewed migration
or a later administrative adoption workflow.

The revision refuses downgrade because removing tenant ownership and Identity
tables after adoption would be destructive. Application rollback keeps the
expanded schema; database recovery uses the pre-migration backup.

## Security boundary

`organization_id` expresses tenancy, not authorization. `/api/v1` remains
anonymous during AI-1 and the public demo remains unsuitable for sensitive
data. Knowledge vector metadata stays Workspace-scoped and is not rewritten.
AI-2 must resolve `CurrentPrincipal`, Membership and `AuthorizedWorkspace`
before any business-data read, write or provider call.

## Validation contract

- clean-database migration to head;
- staged upgrade from Genesis revision `0003` with UUID/data preservation;
- downgrade refusal without schema/data loss;
- model constraints and Membership uniqueness;
- external identity mapping without provider coupling;
- internal tenant-context resolution and cross-Organization denial;
- full Genesis backend/frontend regression gates;
- real database backup, SQL review, migration and before/after evidence.

## Development database adoption record

Before applying revision `0004`, AI-1 created and validated the custom-format
backup `/home/administrator/trident-backups/trident-ai1-before-0004-20260816.dump`.
Its SHA-256 is
`0371884046cbe43602e42840b5e006a0473a6ff429fb324506a6154b2e886319`.
The PostgreSQL offline SQL contained no `DROP`, `TRUNCATE` or `DELETE`.

Revision `0004_identity_tenancy` then completed transactionally. Both existing
Workspace UUIDs were preserved and no historical row digest changed when
computed over its pre-migration columns. Final adoption counts were one
`legacy_unclaimed` Organization, zero Users, zero Memberships and zero external
identities; every existing Workspace had a non-null Organization reference.

The isolated migration suite validates empty-database upgrade, adoption from
revision `0003`, preservation of a representative Workspace and Conversation,
and explicit refusal of destructive downgrade. The full backend suite contains
40 passing tests after AI-1.
