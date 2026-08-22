"""Central tenant context resolution; wired to HTTP authorization in AI-2."""

from dataclasses import dataclass
import uuid

from sqlalchemy.orm import Session

from app.database.genesis_models import Workspace
from app.identity.contracts import AuthenticatedPrincipal
from app.identity.contracts import VerifiedExternalIdentity
from app.identity.models import ExternalIdentity, User
from app.governance.audit import append_audit_event
from app.tenancy.models import Membership, MembershipRole, Organization

LEGACY_ORGANIZATION_ID = "00000000-0000-4000-8000-000000000001"
LEGACY_ORGANIZATION_NAME = "TRIDENT Genesis"
LEGACY_ORGANIZATION_SLUG = "trident-genesis"


class TenantAccessDenied(LookupError):
    """No tenant context may be inferred when ownership or membership is absent."""


class LegacyOrganizationClaimError(RuntimeError):
    """The one-time legacy adoption preconditions were not satisfied."""


PERSONAL_TENANT_NAMESPACE = uuid.UUID("a796d702-f399-4cd0-846f-e323fe2fc6fc")


@dataclass(frozen=True, slots=True)
class PersonalTenantOnboarding:
    organization: Organization
    membership: Membership
    workspace: Workspace
    created: bool


def _persisted_mapping_for_principal(
    db: Session, principal: AuthenticatedPrincipal
) -> tuple[ExternalIdentity, User]:
    mappings = (
        db.query(ExternalIdentity)
        .filter_by(issuer=principal.issuer.strip(), subject=principal.subject.strip())
        .all()
    )
    if len(mappings) != 1 or mappings[0].user_id != principal.user_id:
        raise LegacyOrganizationClaimError("Persisted verified identity is missing or ambiguous")
    user = db.get(User, principal.user_id)
    if user is None or user.status != "active":
        raise LegacyOrganizationClaimError("Internal User is inactive or missing")
    return mappings[0], user


@dataclass(frozen=True, slots=True)
class TenantContext:
    principal: AuthenticatedPrincipal
    organization_id: str
    membership_id: str
    role: MembershipRole
    workspace_id: str


def onboard_personal_tenant(
    db: Session, principal: AuthenticatedPrincipal
) -> PersonalTenantOnboarding | None:
    """Create the minimum personal tenant for a user with no Membership.

    Locking the authoritative User serializes onboarding in PostgreSQL. Stable,
    user-derived identifiers provide an additional uniqueness boundary for
    retries and database engines that do not implement row-level locks.
    Existing members are deliberately left unchanged, including the controlled
    owner of the legacy Organization.
    """
    user = (
        db.query(User)
        .filter(User.id == principal.user_id, User.status == "active")
        .with_for_update()
        .one_or_none()
    )
    if user is None:
        raise TenantAccessDenied("Active principal User is unavailable")

    organization_id = str(
        uuid.uuid5(PERSONAL_TENANT_NAMESPACE, f"organization:{principal.user_id}")
    )
    workspace_id = str(
        uuid.uuid5(PERSONAL_TENANT_NAMESPACE, f"workspace:{principal.user_id}")
    )
    existing_membership = (
        db.query(Membership)
        .filter(Membership.user_id == principal.user_id)
        .order_by(Membership.created_at.asc())
        .first()
    )
    if existing_membership is not None:
        workspace = db.get(Workspace, workspace_id)
        organization = db.get(Organization, organization_id)
        if (
            existing_membership.organization_id == organization_id
            and organization is not None
            and workspace is not None
            and workspace.organization_id == organization_id
        ):
            return PersonalTenantOnboarding(
                organization, existing_membership, workspace, False
            )
        return None
    organization = Organization(
        id=organization_id,
        name="Organization personnelle",
        slug=f"personal-{principal.user_id}",
        ownership_state="active",
    )
    membership = Membership(
        user_id=principal.user_id,
        organization_id=organization_id,
        role=MembershipRole.OWNER.value,
    )
    workspace = Workspace(
        id=workspace_id,
        organization_id=organization_id,
        name="Mon Workspace",
        description="Votre Workspace personnel TRIDENT AI",
    )
    db.add_all([organization, membership, workspace])
    db.flush()
    return PersonalTenantOnboarding(organization, membership, workspace, True)


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
        .join(Organization, Organization.id == Workspace.organization_id)
        .filter(
            Workspace.id == workspace_id,
            Membership.user_id == principal.user_id,
            Organization.ownership_state == "active",
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


def claim_legacy_organization(
    db: Session, verified_identity: VerifiedExternalIdentity
) -> AuthenticatedPrincipal:
    """Atomically claim Genesis after an operator has cryptographically verified identity.

    This service is deliberately not exposed as an HTTP route. Calling code must pass the
    output of an IdentityVerifier; raw issuer/subject strings are not accepted.
    """

    organization = (
        db.query(Organization)
        .filter(Organization.id == LEGACY_ORGANIZATION_ID)
        .with_for_update()
        .first()
    )
    if not organization or organization.ownership_state != "legacy_unclaimed":
        raise LegacyOrganizationClaimError("Legacy Organization is not claimable")
    mapping = (
        db.query(ExternalIdentity)
        .filter_by(issuer=verified_identity.issuer, subject=verified_identity.subject)
        .first()
    )
    user = db.get(User, mapping.user_id) if mapping else None
    if not user:
        user = User()
        db.add(user)
        db.flush()
        db.add(
            ExternalIdentity(
                user_id=user.id,
                issuer=verified_identity.issuer,
                subject=verified_identity.subject,
            )
        )
    membership = (
        db.query(Membership)
        .filter_by(user_id=user.id, organization_id=organization.id)
        .first()
    )
    if not membership:
        db.add(
            Membership(
                user_id=user.id,
                organization_id=organization.id,
                role=MembershipRole.OWNER.value,
            )
        )
    organization.ownership_state = "active"
    db.commit()
    return AuthenticatedPrincipal(
        user_id=user.id,
        issuer=verified_identity.issuer,
        subject=verified_identity.subject,
    )


def claim_persisted_legacy_organization(
    db: Session,
    *,
    principal: AuthenticatedPrincipal,
    approval_reference: str,
) -> Membership:
    """Claim Genesis using only an identity already established by verified OIDC.

    This host-only operation is idempotent for the same owner and never accepts
    a browser claim, creates an identity, or changes Workspace identifiers.
    """
    approval = approval_reference.strip()
    if len(approval) < 8 or len(approval) > 128:
        raise LegacyOrganizationClaimError("A controlled approval reference is required")
    _persisted_mapping_for_principal(db, principal)
    organization = (
        db.query(Organization)
        .filter(Organization.id == LEGACY_ORGANIZATION_ID)
        .with_for_update()
        .first()
    )
    if organization is None:
        raise LegacyOrganizationClaimError("Legacy Organization is missing")
    membership = db.query(Membership).filter_by(
        user_id=principal.user_id,
        organization_id=organization.id,
    ).one_or_none()
    if organization.ownership_state == "active":
        if membership and membership.role == MembershipRole.OWNER.value:
            return membership
        raise LegacyOrganizationClaimError("Legacy Organization was claimed by another owner")
    if organization.ownership_state != "legacy_unclaimed":
        raise LegacyOrganizationClaimError("Legacy Organization is not claimable")
    if membership and membership.role != MembershipRole.OWNER.value:
        raise LegacyOrganizationClaimError("A conflicting Membership already exists")
    if membership is None:
        membership = Membership(
            user_id=principal.user_id,
            organization_id=organization.id,
            role=MembershipRole.OWNER.value,
        )
        db.add(membership)
        db.flush()
    organization.ownership_state = "active"
    append_audit_event(
        db,
        action="organization.legacy_claimed",
        resource_type="organization",
        resource_id=organization.id,
        principal=principal,
        organization_id=organization.id,
        metadata={"approval_reference": approval},
    )
    db.commit()
    db.refresh(membership)
    return membership
