from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.database.genesis_models import (
    Conversation,
    Workspace,
    WorkspaceDocument,
    WorkspaceMemory,
    WorkspaceMessage,
)
from app.modules.registry import modules_for_edition, serialize_module
from app.tenancy.service import ensure_legacy_organization


def ensure_genesis_workspace(db: Session) -> Workspace:
    workspace = db.query(Workspace).order_by(Workspace.created_at.asc()).first()
    if workspace:
        if not workspace.organization_id:
            raise RuntimeError(
                "Workspace tenancy adoption is required before application startup"
            )
        return workspace
    workspace = Workspace(
        name="TRIDENT GENESIS",
        description="Votre espace de travail IA",
        organization_id=ensure_legacy_organization(db).id,
    )
    db.add(workspace)
    db.commit()
    db.refresh(workspace)
    return workspace


def create_genesis_workspace(db: Session, name: str, description: str | None) -> Workspace:
    workspace = Workspace(
        name=name,
        description=description,
        organization_id=ensure_legacy_organization(db).id,
    )
    db.add(workspace)
    db.commit()
    db.refresh(workspace)
    return workspace


def workspace_activity(db: Session, workspace: Workspace) -> dict:
    conversation_count = db.query(Conversation).filter_by(workspace_id=workspace.id).count()
    document_count = db.query(WorkspaceDocument).filter_by(workspace_id=workspace.id).count()
    message_count = (
        db.query(WorkspaceMessage)
        .join(Conversation, WorkspaceMessage.conversation_id == Conversation.id)
        .filter(Conversation.workspace_id == workspace.id)
        .count()
    )
    memory_count = db.query(WorkspaceMemory).filter_by(workspace_id=workspace.id).count()
    return {
        "workspace": serialize_workspace(workspace),
        "metrics": {
            "conversations": conversation_count,
            "documents": document_count,
            "messages": message_count,
            "memories": memory_count,
        },
        "modules": [serialize_module(module) for module in modules_for_edition()],
    }


def serialize_workspace(workspace: Workspace) -> dict:
    return {
        "id": workspace.id,
        "name": workspace.name,
        "description": workspace.description,
        "created_at": workspace.created_at.isoformat() if workspace.created_at else None,
        "updated_at": workspace.updated_at.isoformat() if workspace.updated_at else None,
    }
