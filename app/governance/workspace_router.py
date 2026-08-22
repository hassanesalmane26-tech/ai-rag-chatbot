"""Sanitized, Workspace-scoped product activity feed."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.contracts import PageParams, page_meta
from app.database.database import get_db
from app.governance.audit import serialize_workspace_activity, workspace_activity_query
from app.security.authorization import require_workspace_access
from app.security.dependencies import require_principal
from app.tenancy.service import TenantContext

router = APIRouter(
    prefix="/v1/workspaces/{workspace_id}/activity",
    tags=["Workspace Activity"],
    dependencies=[Depends(require_principal)],
)


@router.get("")
def list_workspace_activity(
    workspace_id: str,
    page: PageParams = Depends(),
    db: Session = Depends(get_db),
    _tenant: TenantContext = Depends(require_workspace_access),
):
    query = workspace_activity_query(db, workspace_id)
    total = query.count()
    events = query.offset(page.offset).limit(page.limit).all()
    return {
        "data": [serialize_workspace_activity(event) for event in events],
        "meta": {"pagination": page_meta(page, total)},
    }
