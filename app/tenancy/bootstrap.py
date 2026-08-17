"""Host-only, controlled adoption command for the Genesis Organization."""

import argparse
import json

from app.database.database import SessionLocal
from app.identity.contracts import AuthenticatedPrincipal
from app.identity.models import ExternalIdentity, User
from app.tenancy.models import Membership, Organization
from app.tenancy.service import (
    LEGACY_ORGANIZATION_ID,
    LegacyOrganizationClaimError,
    claim_persisted_legacy_organization,
)


def persisted_principal(db, issuer: str, subject: str) -> AuthenticatedPrincipal:
    mappings = db.query(ExternalIdentity).filter_by(
        issuer=issuer.strip(), subject=subject.strip()
    ).all()
    if len(mappings) != 1:
        raise LegacyOrganizationClaimError("Persisted identity mapping is missing or ambiguous")
    user = db.get(User, mappings[0].user_id)
    if user is None or user.status != "active":
        raise LegacyOrganizationClaimError("Internal User is inactive or missing")
    return AuthenticatedPrincipal(user.id, mappings[0].issuer, mappings[0].subject)


def main() -> None:
    parser = argparse.ArgumentParser(description="Controlled TRIDENT Genesis Organization claim")
    parser.add_argument("--issuer", required=True)
    parser.add_argument("--subject", required=True)
    parser.add_argument("--approval-reference")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    db = SessionLocal()
    try:
        principal = persisted_principal(db, args.issuer, args.subject)
        organization = db.get(Organization, LEGACY_ORGANIZATION_ID)
        membership = db.query(Membership).filter_by(
            user_id=principal.user_id, organization_id=LEGACY_ORGANIZATION_ID
        ).one_or_none()
        if args.apply:
            if not args.approval_reference:
                parser.error("--approval-reference is required with --apply")
            membership = claim_persisted_legacy_organization(
                db,
                principal=principal,
                approval_reference=args.approval_reference,
            )
            organization = db.get(Organization, LEGACY_ORGANIZATION_ID)
        print(json.dumps({
            "apply": args.apply,
            "user_id": principal.user_id,
            "issuer": principal.issuer,
            "subject": "[redacted]",
            "organization_id": LEGACY_ORGANIZATION_ID,
            "ownership_state": organization.ownership_state if organization else "missing",
            "membership_role": membership.role if membership else None,
        }, sort_keys=True))
    finally:
        db.close()


if __name__ == "__main__":
    main()
