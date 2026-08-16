"""Workspace-scoped public Memory API."""

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.database.genesis_models import Workspace, WorkspaceMemory
from app.api.contracts import PageParams, page_meta
from app.governance.audit import append_audit_event
from app.governance.quotas import enforce_resource_quota
from app.identity.contracts import AuthenticatedPrincipal
from app.memory.service import MEMORY_KINDS, serialize_memory, validate_conversation_scope
from app.security.authorization import require_workspace_access
from app.security.dependencies import require_principal
from app.tenancy.service import TenantContext

router = APIRouter(
    prefix="/v1/workspaces/{workspace_id}/memories",
    tags=["Memory"],
    dependencies=[Depends(require_principal)],
)


class MemoryCreateInput(BaseModel):
    kind: str = Field(default="note", max_length=24)
    title: str = Field(min_length=1, max_length=160)
    content: str = Field(min_length=1, max_length=4000)
    conversation_id: str | None = Field(default=None, max_length=36)


class MemoryUpdateInput(BaseModel):
    kind: str | None = Field(default=None, max_length=24)
    title: str | None = Field(default=None, max_length=160)
    content: str | None = Field(default=None, max_length=4000)
    active: bool | None = None


def data(value, meta: dict | None = None):
    return {"data": value, "meta": meta or {}}


def require_workspace(db: Session, workspace_id: str) -> None:
    if not db.get(Workspace, workspace_id):
        raise HTTPException(status_code=404, detail="Workspace introuvable.")


def require_memory(db: Session, workspace_id: str, memory_id: str) -> WorkspaceMemory:
    memory = db.get(WorkspaceMemory, memory_id)
    if not memory or memory.workspace_id != workspace_id:
        raise HTTPException(status_code=404, detail="Mémoire introuvable.")
    return memory


def normalized(value: str, field: str) -> str:
    result = value.strip()
    if not result:
        raise HTTPException(status_code=422, detail=f"Le champ {field} est requis.")
    return result


@router.get("")
def list_memories(
    workspace_id: str,
    page: PageParams = Depends(),
    db: Session = Depends(get_db),
    _tenant: TenantContext = Depends(require_workspace_access),
):
    require_workspace(db, workspace_id)
    query = db.query(WorkspaceMemory).filter_by(workspace_id=workspace_id)
    total = query.count()
    memories = (
        query
        .order_by(WorkspaceMemory.updated_at.desc(), WorkspaceMemory.id.desc())
        .offset(page.offset).limit(page.limit)
        .all()
    )
    return data([serialize_memory(memory) for memory in memories], {"pagination": page_meta(page, total)})


@router.post("", status_code=201)
def create_memory(
    workspace_id: str,
    payload: MemoryCreateInput,
    request: Request,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(require_workspace_access),
    principal: AuthenticatedPrincipal = Depends(require_principal),
):
    require_workspace(db, workspace_id)
    current = db.query(WorkspaceMemory).filter_by(workspace_id=workspace_id).count()
    enforce_resource_quota(db, principal, tenant.organization_id, "memories.per_workspace", current)
    if payload.kind not in MEMORY_KINDS:
        raise HTTPException(status_code=422, detail="Type de mémoire invalide.")
    try:
        validate_conversation_scope(db, workspace_id, payload.conversation_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Conversation introuvable.") from exc
    memory = WorkspaceMemory(
        workspace_id=workspace_id,
        conversation_id=payload.conversation_id,
        kind=payload.kind,
        title=normalized(payload.title, "titre"),
        content=normalized(payload.content, "contenu"),
    )
    db.add(memory)
    db.commit()
    db.refresh(memory)
    append_audit_event(db, action="memory.created", resource_type="memory", resource_id=memory.id,
                       principal=principal, organization_id=tenant.organization_id, workspace_id=workspace_id,
                       request_id=request.state.request_id)
    db.commit()
    return data(serialize_memory(memory))


@router.patch("/{memory_id}")
def update_memory(
    workspace_id: str,
    memory_id: str,
    payload: MemoryUpdateInput,
    request: Request,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(require_workspace_access),
    principal: AuthenticatedPrincipal = Depends(require_principal),
):
    memory = require_memory(db, workspace_id, memory_id)
    fields = payload.model_fields_set
    if not fields:
        raise HTTPException(status_code=422, detail="Aucune modification fournie.")
    if "kind" in fields:
        if payload.kind not in MEMORY_KINDS:
            raise HTTPException(status_code=422, detail="Type de mémoire invalide.")
        memory.kind = payload.kind
    if "title" in fields:
        memory.title = normalized(payload.title or "", "titre")
    if "content" in fields:
        memory.content = normalized(payload.content or "", "contenu")
    if "active" in fields:
        memory.active = bool(payload.active)
    db.commit()
    db.refresh(memory)
    append_audit_event(db, action="memory.updated", resource_type="memory", resource_id=memory.id,
                       principal=principal, organization_id=tenant.organization_id, workspace_id=workspace_id,
                       request_id=request.state.request_id, metadata={"fields": sorted(fields)})
    db.commit()
    return data(serialize_memory(memory))


@router.delete("/{memory_id}")
def delete_memory(
    workspace_id: str,
    memory_id: str,
    request: Request,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(require_workspace_access),
    principal: AuthenticatedPrincipal = Depends(require_principal),
):
    memory = require_memory(db, workspace_id, memory_id)
    db.delete(memory)
    db.commit()
    append_audit_event(db, action="memory.deleted", resource_type="memory", resource_id=memory_id,
                       principal=principal, organization_id=tenant.organization_id, workspace_id=workspace_id,
                       request_id=request.state.request_id)
    db.commit()
    return data({"id": memory_id, "deleted": True})
