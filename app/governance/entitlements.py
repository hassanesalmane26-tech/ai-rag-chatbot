"""Server-side entitlement resolution shared by editions and modules."""

from dataclasses import asdict, dataclass
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.governance.models import EntitlementGrant
from app.identity.contracts import AuthenticatedPrincipal
from app.tenancy.models import Membership, Organization

ECOSYSTEM_FULL_ACCESS = "ecosystem.full_access"
TRIDENT_AI = "TRIDENT_AI"
TRIDENT_PRO = "TRIDENT_PRO"
NOVA_TRIDENT = "NOVA_TRIDENT"

EDITION_ENTITLEMENTS = {
    TRIDENT_AI: "edition.trident_ai.access",
    TRIDENT_PRO: "edition.trident_pro.access",
    NOVA_TRIDENT: "edition.nova_trident.access",
}


@dataclass(frozen=True, slots=True)
class EditionAccess:
    edition: str
    allowed: bool
    source: str | None

    def public_dict(self) -> dict[str, str | bool | None]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class EditionResolution:
    founder: bool
    editions: tuple[EditionAccess, ...]

    def public_dict(self) -> dict:
        return {
            "founder": self.founder,
            "editions": [item.public_dict() for item in self.editions],
        }


def _active(query, now: datetime):
    return query.filter(EntitlementGrant.revoked_at.is_(None)).filter(
        (EntitlementGrant.expires_at.is_(None)) | (EntitlementGrant.expires_at > now)
    )


def _membership_exists(
    db: Session, principal: AuthenticatedPrincipal, organization_id: str
) -> bool:
    return (
        db.query(Membership.id)
        .join(Organization, Organization.id == Membership.organization_id)
        .filter(
            Membership.user_id == principal.user_id,
            Membership.organization_id == organization_id,
            Organization.ownership_state == "active",
        )
        .first()
        is not None
    )


def _grant_for_key(
    db: Session,
    principal: AuthenticatedPrincipal,
    organization_id: str,
    key: str,
    now: datetime,
) -> EntitlementGrant | None:
    user_grant = _active(
        db.query(EntitlementGrant).filter_by(user_id=principal.user_id, key=key), now
    ).one_or_none()
    if user_grant:
        return user_grant
    return _active(
        db.query(EntitlementGrant).filter_by(organization_id=organization_id, key=key), now
    ).one_or_none()


def entitlement_value(
    db: Session, principal: AuthenticatedPrincipal, organization_id: str, key: str
) -> int | None:
    """Resolve a grant only inside an explicit Membership boundary."""
    if not _membership_exists(db, principal, organization_id):
        return None
    now = datetime.now(timezone.utc)
    grant = _grant_for_key(db, principal, organization_id, key, now)
    return grant.integer_value if grant else None


def resolve_edition_access(
    db: Session, principal: AuthenticatedPrincipal, organization_id: str
) -> EditionResolution:
    """Resolve trusted edition access without changing tenant authorization."""
    if not _membership_exists(db, principal, organization_id):
        return EditionResolution(
            founder=False,
            editions=tuple(EditionAccess(edition, False, None) for edition in EDITION_ENTITLEMENTS),
        )

    now = datetime.now(timezone.utc)
    full_access = _grant_for_key(db, principal, organization_id, ECOSYSTEM_FULL_ACCESS, now)
    founder = bool(
        full_access
        and full_access.user_id == principal.user_id
        and full_access.source == "founder"
        and full_access.integer_value == 1
        and full_access.expires_at is None
    )
    resolved = []
    for edition, key in EDITION_ENTITLEMENTS.items():
        if founder:
            resolved.append(EditionAccess(edition, True, "founder"))
            continue
        if edition == TRIDENT_AI:
            resolved.append(EditionAccess(edition, True, "core"))
            continue
        grant = _grant_for_key(db, principal, organization_id, key, now)
        allowed = bool(grant and grant.integer_value == 1)
        resolved.append(EditionAccess(edition, allowed, grant.source if allowed else None))
    return EditionResolution(founder=founder, editions=tuple(resolved))


def can_access_edition(
    db: Session,
    principal: AuthenticatedPrincipal,
    organization_id: str,
    edition: str,
) -> bool:
    if edition not in EDITION_ENTITLEMENTS:
        return False
    resolution = resolve_edition_access(db, principal, organization_id)
    return next(item.allowed for item in resolution.editions if item.edition == edition)


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
