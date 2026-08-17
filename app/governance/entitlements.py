"""Server-side entitlement resolution shared by editions and modules."""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.governance.models import EntitlementGrant
from app.identity.contracts import AuthenticatedPrincipal
from app.tenancy.models import Membership, Organization

ECOSYSTEM_FULL_ACCESS = "ecosystem.full_access"


def _active(query, now: datetime):
    return query.filter(EntitlementGrant.revoked_at.is_(None)).filter(
        (EntitlementGrant.expires_at.is_(None)) | (EntitlementGrant.expires_at > now)
    )


def entitlement_value(
    db: Session, principal: AuthenticatedPrincipal, organization_id: str, key: str
) -> int | None:
    """Resolve a grant only inside an explicit Membership boundary."""
    membership = (
        db.query(Membership.id)
        .join(Organization, Organization.id == Membership.organization_id)
        .filter(
            Membership.user_id == principal.user_id,
            Membership.organization_id == organization_id,
            Organization.ownership_state == "active",
        )
        .first()
    )
    if membership is None:
        return None
    now = datetime.now(timezone.utc)
    user_grant = _active(
        db.query(EntitlementGrant).filter_by(user_id=principal.user_id, key=key), now
    ).one_or_none()
    if user_grant:
        return user_grant.integer_value
    organization_grant = _active(
        db.query(EntitlementGrant).filter_by(organization_id=organization_id, key=key), now
    ).one_or_none()
    return organization_grant.integer_value if organization_grant else None


def has_capability(
    db: Session,
    principal: AuthenticatedPrincipal,
    organization_id: str,
    capability_key: str,
) -> bool:
    """Full access unlocks capability policy, never tenant authorization."""
    return (
        entitlement_value(db, principal, organization_id, ECOSYSTEM_FULL_ACCESS) == 1
        or entitlement_value(db, principal, organization_id, capability_key) == 1
    )
