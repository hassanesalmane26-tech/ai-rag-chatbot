"""Read-only planning boundary for the separately authorized Founder phase."""

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.identity.models import ExternalIdentity, User
from app.tenancy.models import Membership, MembershipRole


@dataclass(frozen=True, slots=True)
class FounderBootstrapPlan:
    user_id: str
    issuer: str
    subject: str
    owner_organization_ids: tuple[str, ...]
    entitlement_keys: tuple[str, ...] = ("ecosystem.full_access",)


def plan_founder_bootstrap(db: Session, *, issuer: str, subject: str) -> FounderBootstrapPlan:
    """Resolve verified persisted identity and ownership without mutating grants."""
    identity = db.query(ExternalIdentity).filter_by(issuer=issuer, subject=subject).one_or_none()
    if identity is None:
        raise ValueError("Verified external identity is not provisioned")
    user = db.get(User, identity.user_id)
    if user is None or user.status != "active":
        raise ValueError("Internal user is inactive or missing")
    ownerships = (
        db.query(Membership.organization_id)
        .filter_by(user_id=user.id, role=MembershipRole.OWNER.value)
        .order_by(Membership.organization_id)
        .all()
    )
    if not ownerships:
        raise ValueError("Founder candidate must hold explicit Organization ownership")
    return FounderBootstrapPlan(
        user_id=user.id,
        issuer=issuer,
        subject=subject,
        owner_organization_ids=tuple(row[0] for row in ownerships),
    )
