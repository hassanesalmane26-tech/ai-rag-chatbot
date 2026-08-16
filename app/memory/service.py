"""Workspace Memory application service."""

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database.genesis_models import Conversation, WorkspaceMemory

MEMORY_KINDS = {"note", "preference", "fact"}
CONTEXT_RECORD_LIMIT = 12
CONTEXT_CHARACTER_LIMIT = 4000


def validate_conversation_scope(
    db: Session, workspace_id: str, conversation_id: str | None
) -> None:
    if not conversation_id:
        return
    conversation = db.get(Conversation, conversation_id)
    if not conversation or conversation.workspace_id != workspace_id:
        raise ValueError("conversation_scope")


def serialize_memory(memory: WorkspaceMemory) -> dict:
    return {
        "id": memory.id,
        "workspace_id": memory.workspace_id,
        "conversation_id": memory.conversation_id,
        "kind": memory.kind,
        "title": memory.title,
        "content": memory.content,
        "active": bool(memory.active),
        "created_at": memory.created_at.isoformat() if memory.created_at else None,
        "updated_at": memory.updated_at.isoformat() if memory.updated_at else None,
    }


def memory_context(
    db: Session, workspace_id: str, conversation_id: str | None
) -> str:
    query = db.query(WorkspaceMemory).filter_by(workspace_id=workspace_id, active=True)
    if conversation_id:
        query = query.filter(
            or_(
                WorkspaceMemory.conversation_id.is_(None),
                WorkspaceMemory.conversation_id == conversation_id,
            )
        )
    else:
        query = query.filter(WorkspaceMemory.conversation_id.is_(None))
    records = (
        query.order_by(WorkspaceMemory.updated_at.desc(), WorkspaceMemory.id.desc())
        .limit(CONTEXT_RECORD_LIMIT)
        .all()
    )
    lines = [f"[{memory.kind}] {memory.title}: {memory.content}" for memory in records]
    return "\n".join(lines)[:CONTEXT_CHARACTER_LIMIT]
