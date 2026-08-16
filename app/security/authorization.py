"""Centralized Organization, role and Workspace authorization policies."""

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.errors import AuthorizationError, ConflictError
from app.database.database import get_db
from app.database.genesis_models import Workspace
from app.identity.contracts import AuthenticatedPrincipal
from app.governance.audit import append_audit_event
from app.security.dependencies import require_principal
from app.tenancy.models import Membership, MembershipRole, Organization
from app.tenancy.service import TenantAccessDenied, TenantContext, tenant_context_for_workspace

WORKSPACE_ADMIN_ROLES = {MembershipRole.OWNER, MembershipRole.ADMIN}


def authorized_organizations(
    db: Session, principal: AuthenticatedPrincipal
) -> list[tuple[Organization, Membership]]:
    return (
        db.query(Organization, Membership)
        .join(Membership, Membership.organization_id == Organization.id)
        .filter(
            Membership.user_id == principal.user_id,
            Organization.ownership_state == "active",
        )
        .order_by(Organization.created_at.asc())
        .all()
    )


def organization_for_workspace_creation(
    db: Session, principal: AuthenticatedPrincipal, organization_id: str | None
) -> tuple[Organization, Membership]:
    memberships = authorized_organizations(db, principal)
    if organization_id:
        memberships = [item for item in memberships if item[0].id == organization_id]
    if not memberships:
        raise AuthorizationError()
    if len(memberships) != 1:
        raise ConflictError("Une Organization explicite est requise.")
    organization, membership = memberships[0]
    if MembershipRole(membership.role) not in WORKSPACE_ADMIN_ROLES:
        raise AuthorizationError()
    return organization, membership


def require_workspace_access(
    workspace_id: str,
    request: Request,
    principal: AuthenticatedPrincipal = Depends(require_principal),
    db: Session = Depends(get_db),
) -> TenantContext:
    try:
        return tenant_context_for_workspace(db, principal, workspace_id)
    except TenantAccessDenied as exc:
        workspace = db.get(Workspace, workspace_id)
        append_audit_event(
            db, action="authorization.workspace_denied", resource_type="workspace",
            resource_id=workspace_id, principal=principal,
            organization_id=workspace.organization_id if workspace else None,
            workspace_id=workspace_id if workspace else None,
            outcome="denied",
            request_id=getattr(request.state, "request_id", None),
        )
        db.commit()
        raise AuthorizationError() from exc


def require_workspace_admin(
    context: TenantContext = Depends(require_workspace_access),
) -> TenantContext:
    if context.role not in WORKSPACE_ADMIN_ROLES:
        raise AuthorizationError()
    return context


def visible_workspaces_query(
    db: Session, principal: AuthenticatedPrincipal, organization_id: str | None = None
):
    query = (
        db.query(Workspace)
        .join(Membership, Membership.organization_id == Workspace.organization_id)
        .filter(Membership.user_id == principal.user_id)
    )
    if organization_id:
        query = query.filter(Workspace.organization_id == organization_id)
    return query


def visible_workspaces(
    db: Session, principal: AuthenticatedPrincipal, organization_id: str | None = None
) -> list[Workspace]:
    return visible_workspaces_query(db, principal, organization_id).order_by(
        Workspace.updated_at.desc(), Workspace.id.desc()
    ).all()
