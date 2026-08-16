from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.database.genesis_models import (
    Conversation,
    Workspace,
    WorkspaceDocument,
    WorkspaceMemory,
    WorkspaceMessage,
)


def ensure_genesis_workspace(db: Session) -> Workspace:
    workspace = db.query(Workspace).order_by(Workspace.created_at.asc()).first()
    if workspace:
        return workspace
    workspace = Workspace(name="TRIDENT GENESIS", description="Votre espace de travail IA")
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
        "modules": [
            {"id": "home", "label": "Accueil", "status": "ready"},
            {"id": "conversations", "label": "Conversations", "status": "ready"},
            {"id": "knowledge", "label": "Knowledge", "status": "ready"},
            {"id": "memory", "label": "Memory", "status": "ready"},
        ],
    }


def serialize_workspace(workspace: Workspace) -> dict:
    return {
        "id": workspace.id,
        "name": workspace.name,
        "description": workspace.description,
        "created_at": workspace.created_at.isoformat() if workspace.created_at else None,
        "updated_at": workspace.updated_at.isoformat() if workspace.updated_at else None,
    }
