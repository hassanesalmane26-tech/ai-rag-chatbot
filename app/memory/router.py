"""Workspace-scoped public Memory API."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.database.genesis_models import Workspace, WorkspaceMemory
from app.memory.service import MEMORY_KINDS, serialize_memory, validate_conversation_scope

router = APIRouter(prefix="/v1/workspaces/{workspace_id}/memories", tags=["Memory"])


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


def data(value):
    return {"data": value, "meta": {}}


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
def list_memories(workspace_id: str, db: Session = Depends(get_db)):
    require_workspace(db, workspace_id)
    memories = (
        db.query(WorkspaceMemory)
        .filter_by(workspace_id=workspace_id)
        .order_by(WorkspaceMemory.updated_at.desc(), WorkspaceMemory.id.desc())
        .all()
    )
    return data([serialize_memory(memory) for memory in memories])


@router.post("", status_code=201)
def create_memory(
    workspace_id: str, payload: MemoryCreateInput, db: Session = Depends(get_db)
):
    require_workspace(db, workspace_id)
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
    return data(serialize_memory(memory))


@router.patch("/{memory_id}")
def update_memory(
    workspace_id: str,
    memory_id: str,
    payload: MemoryUpdateInput,
    db: Session = Depends(get_db),
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
    return data(serialize_memory(memory))


@router.delete("/{memory_id}")
def delete_memory(
    workspace_id: str, memory_id: str, db: Session = Depends(get_db)
):
    memory = require_memory(db, workspace_id, memory_id)
    db.delete(memory)
    db.commit()
    return data({"id": memory_id, "deleted": True})
