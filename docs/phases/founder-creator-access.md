# Founder / Creator Access phase

## Canonical attribution

Creator: **Salmane Hassan**

Canonical attribution: **Created by Salmane Hassan**

Ecosystem mark: **A TRIDENT Project**

`app.core.product.TRIDENT_PRODUCT` is the single application metadata source.
It may feed later product surfaces through the public build metadata. It is
strictly presentation metadata and never identifies or authorizes a User.

## Entitlement semantics

`ecosystem.full_access=1`, source `founder`, is a permanent User entitlement.
The Membership-aware resolver allows it to unlock TRIDENT AI, TRIDENT PRO, NOVA
TRIDENT and future capability policies only inside Organizations the principal
can already access. It never creates Membership or bypasses Workspace checks.
Billing may add plan grants independently; a Founder grant remains explicit and
auditable rather than being encoded as a special subscription.

## Readiness and activation

No claim is active. Once the real OIDC identity has completed cryptographic
authentication and has been mapped to an active internal User with explicit
Organization `owner` Membership, run the read-only check locally:

```bash
venv/bin/python -m app.governance.founder \
  --issuer 'OWNER_APPROVED_HTTPS_ISSUER' \
  --subject 'OWNER_SUPPLIED_SUBJECT' \
  --organization-id 'EXISTING_ORGANIZATION_UUID'
```

The command never assigns a grant and redacts the subject in output. Activation
must call `assign_founder_entitlement` from an owner-controlled maintenance task
using the verified `AuthenticatedPrincipal`, exact Organization UUID and a
durable approval reference. Validate the resulting grant and
`founder.entitlement_granted` audit event before ending maintenance.

## Idempotency and conflicts

Repeated assignment returns the same active grant and creates no duplicate.
Unknown, inactive, conflicting or non-owner identities fail closed. A grant with
the wrong source/value, an expiry, or prior revocation blocks activation instead
of being overwritten.

## Revocation and recovery

`revoke_founder_entitlement` requires a verified active operator who is an owner
of the same Organization, the target remains an explicit owner, and a separate
approval reference. It sets `revoked_at`, retains the row and appends
`founder.entitlement_revoked`. It does not delete identity, Membership, business
data or audit evidence.

A revoked Founder grant cannot be automatically restored. Recovery requires
human review of the immutable chain, renewed OIDC and ownership verification,
and an explicit future recovery procedure. Direct SQL edits are prohibited.

## Remaining prerequisite

The verified OIDC issuer/subject and controlled ownership claim have not been
provided. Therefore Founder access remains intentionally unclaimed. No email,
UUID, password, token or provider credential is embedded in source.
