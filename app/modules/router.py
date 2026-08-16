"""Workspace-scoped module discovery API."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.database.genesis_models import Workspace
from app.modules.registry import modules_for_edition, serialize_module

router = APIRouter(prefix="/v1/workspaces/{workspace_id}/modules", tags=["Modules"])


@router.get("")
def list_workspace_modules(workspace_id: str, db: Session = Depends(get_db)):
    if not db.get(Workspace, workspace_id):
        raise HTTPException(status_code=404, detail="Workspace introuvable.")
    return {
        "data": [serialize_module(module) for module in modules_for_edition()],
        "meta": {"edition": "genesis"},
    }
