"""Controlled Founder entitlement bootstrap and revocation service.

This module is deliberately not mounted as an HTTP route. Host-level operators
may use the dry-run CLI; activation requires an explicit approval reference.
"""

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.database.database import SessionLocal
from app.governance.audit import append_audit_event
from app.governance.models import EntitlementGrant
from app.identity.contracts import AuthenticatedPrincipal
from app.identity.models import ExternalIdentity, User
from app.tenancy.models import Membership, MembershipRole, Organization

FOUNDER_ENTITLEMENT = "ecosystem.full_access"
FOUNDER_ENTITLEMENT_VALUE = 1


class FounderBootstrapError(ValueError):
    """A controlled bootstrap invariant was not satisfied."""


@dataclass(frozen=True, slots=True)
class FounderBootstrapPlan:
    user_id: str
    issuer: str
    subject: str
    organization_id: str
    entitlement_key: str = FOUNDER_ENTITLEMENT
    entitlement_value: int = FOUNDER_ENTITLEMENT_VALUE
    already_active: bool = False


def _mapping_for_principal(db: Session, principal: AuthenticatedPrincipal) -> ExternalIdentity:
    mappings = (
        db.query(ExternalIdentity)
        .filter_by(issuer=principal.issuer.strip(), subject=principal.subject.strip())
        .all()
    )
    if len(mappings) != 1:
        raise FounderBootstrapError("Founder identity mapping is missing or ambiguous")
    mapping = mappings[0]
    if mapping.user_id != principal.user_id:
        raise FounderBootstrapError("Verified principal conflicts with the internal identity mapping")
    user = db.get(User, mapping.user_id)
    if user is None or user.status != "active":
        raise FounderBootstrapError("Founder internal User is inactive or missing")
    return mapping


def _require_owner(db: Session, user_id: str, organization_id: str) -> Membership:
    organization = db.get(Organization, organization_id)
    if organization is None or organization.ownership_state != "active":
        raise FounderBootstrapError("Founder Organization is unavailable or unclaimed")
    membership = db.query(Membership).filter_by(
        user_id=user_id, organization_id=organization_id
    ).one_or_none()
    if membership is None or membership.role != MembershipRole.OWNER.value:
        raise FounderBootstrapError("Explicit Organization owner Membership is required")
    return membership


def plan_founder_bootstrap(
    db: Session,
    *,
    principal: AuthenticatedPrincipal,
    organization_id: str,
    entitlement_key: str = FOUNDER_ENTITLEMENT,
) -> FounderBootstrapPlan:
    """Perform a read-only readiness check for one exact verified principal."""
    if entitlement_key != FOUNDER_ENTITLEMENT:
        raise FounderBootstrapError("Only the reserved Founder entitlement may be bootstrapped")
    mapping = _mapping_for_principal(db, principal)
    _require_owner(db, mapping.user_id, organization_id)
    grant = db.query(EntitlementGrant).filter_by(
        user_id=mapping.user_id, key=FOUNDER_ENTITLEMENT
    ).one_or_none()
    if grant and (
        grant.source != "founder"
        or grant.integer_value != FOUNDER_ENTITLEMENT_VALUE
        or grant.expires_at is not None
    ):
        raise FounderBootstrapError("A conflicting entitlement grant already exists")
    if grant and grant.revoked_at is not None:
        raise FounderBootstrapError("Founder entitlement was revoked; controlled recovery is required")
    return FounderBootstrapPlan(
        user_id=mapping.user_id,
        issuer=mapping.issuer,
        subject=mapping.subject,
        organization_id=organization_id,
        already_active=grant is not None,
    )


def assign_founder_entitlement(
    db: Session,
    *,
    principal: AuthenticatedPrincipal,
    organization_id: str,
    approval_reference: str,
    request_id: str | None = None,
    entitlement_key: str = FOUNDER_ENTITLEMENT,
) -> EntitlementGrant:
    """Idempotently assign the permanent grant and append immutable evidence."""
    approval = approval_reference.strip()
    if len(approval) < 8 or len(approval) > 128:
        raise FounderBootstrapError("A controlled approval reference is required")
    plan = plan_founder_bootstrap(
        db,
        principal=principal,
        organization_id=organization_id,
        entitlement_key=entitlement_key,
    )
    grant = db.query(EntitlementGrant).filter_by(
        user_id=plan.user_id, key=plan.entitlement_key
    ).one_or_none()
    if grant is not None:
        return grant
    grant = EntitlementGrant(
        user_id=plan.user_id,
        key=plan.entitlement_key,
        integer_value=plan.entitlement_value,
        source="founder",
        issued_by_user_id=principal.user_id,
        expires_at=None,
    )
    db.add(grant)
    db.flush()
    append_audit_event(
        db,
        action="founder.entitlement_granted",
        resource_type="entitlement_grant",
        resource_id=grant.id,
        principal=principal,
        organization_id=organization_id,
        request_id=request_id,
        metadata={
            "entitlement_key": plan.entitlement_key,
            "approval_reference": approval,
            "permanent": True,
        },
    )
    db.commit()
    db.refresh(grant)
    return grant


def revoke_founder_entitlement(
    db: Session,
    *,
    operator: AuthenticatedPrincipal,
    target_user_id: str,
    organization_id: str,
    approval_reference: str,
    request_id: str | None = None,
) -> EntitlementGrant:
    """Explicitly revoke Founder access; never delete its audit or grant record."""
    approval = approval_reference.strip()
    if len(approval) < 8 or len(approval) > 128:
        raise FounderBootstrapError("A controlled approval reference is required")
    _mapping_for_principal(db, operator)
    _require_owner(db, operator.user_id, organization_id)
    _require_owner(db, target_user_id, organization_id)
    grant = db.query(EntitlementGrant).filter_by(
        user_id=target_user_id, key=FOUNDER_ENTITLEMENT
    ).one_or_none()
    if grant is None or grant.source != "founder":
        raise FounderBootstrapError("Active Founder entitlement was not found")
    if grant.revoked_at is not None:
        return grant
    grant.revoked_at = datetime.now(timezone.utc)
    append_audit_event(
        db,
        action="founder.entitlement_revoked",
        resource_type="entitlement_grant",
        resource_id=grant.id,
        principal=operator,
        organization_id=organization_id,
        request_id=request_id,
        metadata={
            "target_user_id": target_user_id,
            "entitlement_key": FOUNDER_ENTITLEMENT,
            "approval_reference": approval,
        },
    )
    db.commit()
    db.refresh(grant)
    return grant


def _principal_from_persisted_mapping(db: Session, issuer: str, subject: str) -> AuthenticatedPrincipal:
    mappings = db.query(ExternalIdentity).filter_by(issuer=issuer, subject=subject).all()
    if len(mappings) != 1:
        raise FounderBootstrapError("Persisted identity mapping is missing or ambiguous")
    return AuthenticatedPrincipal(mappings[0].user_id, issuer, subject)


def main() -> None:
    parser = argparse.ArgumentParser(description="Read-only TRIDENT Founder readiness check")
    parser.add_argument("--issuer", required=True)
    parser.add_argument("--subject", required=True)
    parser.add_argument("--organization-id", required=True)
    args = parser.parse_args()
    db = SessionLocal()
    try:
        principal = _principal_from_persisted_mapping(db, args.issuer, args.subject)
        plan = plan_founder_bootstrap(
            db, principal=principal, organization_id=args.organization_id
        )
        output = asdict(plan)
        output["subject"] = "[redacted]"
        print(json.dumps(output, sort_keys=True))
    finally:
        db.close()


if __name__ == "__main__":
    main()
