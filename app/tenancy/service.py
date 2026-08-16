"""Central tenant context resolution; wired to HTTP authorization in AI-2."""

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.database.genesis_models import Workspace
from app.identity.contracts import AuthenticatedPrincipal
from app.tenancy.models import Membership, MembershipRole, Organization

LEGACY_ORGANIZATION_ID = "00000000-0000-4000-8000-000000000001"
LEGACY_ORGANIZATION_NAME = "TRIDENT Genesis"
LEGACY_ORGANIZATION_SLUG = "trident-genesis"


class TenantAccessDenied(LookupError):
    """No tenant context may be inferred when ownership or membership is absent."""


@dataclass(frozen=True, slots=True)
class TenantContext:
    principal: AuthenticatedPrincipal
    organization_id: str
    membership_id: str
    role: MembershipRole
    workspace_id: str


def ensure_legacy_organization(db: Session) -> Organization:
    organization = db.get(Organization, LEGACY_ORGANIZATION_ID)
    if organization:
        return organization
    organization = Organization(
        id=LEGACY_ORGANIZATION_ID,
        name=LEGACY_ORGANIZATION_NAME,
        slug=LEGACY_ORGANIZATION_SLUG,
        ownership_state="legacy_unclaimed",
    )
    db.add(organization)
    db.flush()
    return organization


def tenant_context_for_workspace(
    db: Session, principal: AuthenticatedPrincipal, workspace_id: str
) -> TenantContext:
    resolved = (
        db.query(Workspace, Membership)
        .join(Membership, Membership.organization_id == Workspace.organization_id)
        .filter(
            Workspace.id == workspace_id,
            Membership.user_id == principal.user_id,
        )
        .first()
    )
    if not resolved:
        raise TenantAccessDenied("Principal is not a Workspace Organization member")
    workspace, membership = resolved
    return TenantContext(
        principal=principal,
        organization_id=workspace.organization_id,
        membership_id=membership.id,
        role=MembershipRole(membership.role),
        workspace_id=workspace.id,
    )
