"""Workspace-scoped module discovery API."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.database.genesis_models import Workspace
from app.modules.registry import modules_for_edition, serialize_module
from app.security.authorization import require_workspace_access
from app.security.dependencies import require_principal
from app.tenancy.service import TenantContext

router = APIRouter(
    prefix="/v1/workspaces/{workspace_id}/modules",
    tags=["Modules"],
    dependencies=[Depends(require_principal)],
)


@router.get("")
def list_workspace_modules(
    workspace_id: str,
    db: Session = Depends(get_db),
    _tenant: TenantContext = Depends(require_workspace_access),
):
    if not db.get(Workspace, workspace_id):
        raise HTTPException(status_code=404, detail="Workspace introuvable.")
    return {
        "data": [serialize_module(module) for module in modules_for_edition()],
        "meta": {"edition": "genesis"},
    }
