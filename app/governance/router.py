"""Organization-scoped, read-only audit API."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.contracts import PageParams, page_meta
from app.core.errors import AuthorizationError
from app.database.database import get_db
from app.governance.audit import serialize_audit_event
from app.governance.models import AuditEvent
from app.identity.contracts import AuthenticatedPrincipal
from app.security.dependencies import require_principal
from app.tenancy.models import Membership, MembershipRole, Organization

router = APIRouter(prefix="/v1/organizations", tags=["Governance"], dependencies=[Depends(require_principal)])


@router.get("/{organization_id}/audit-events")
def list_audit_events(
    organization_id: str,
    page: PageParams = Depends(),
    db: Session = Depends(get_db),
    principal: AuthenticatedPrincipal = Depends(require_principal),
):
    organization = db.get(Organization, organization_id)
    membership = db.query(Membership).filter_by(
        organization_id=organization_id, user_id=principal.user_id
    ).first()
    if not organization or not membership or MembershipRole(membership.role) not in {
        MembershipRole.OWNER, MembershipRole.ADMIN
    }:
        raise AuthorizationError()
    query = db.query(AuditEvent).filter_by(organization_id=organization_id)
    total = query.count()
    events = query.order_by(AuditEvent.created_at.desc(), AuditEvent.id.desc()).offset(page.offset).limit(page.limit).all()
    return {"data": [serialize_audit_event(event) for event in events], "meta": {"pagination": page_meta(page, total)}}
