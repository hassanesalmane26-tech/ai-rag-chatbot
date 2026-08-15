import json

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.database.genesis_models import Conversation, WorkspaceMessage
from app.rag.search import search_workspace_documents


def create_conversation(db: Session, workspace_id: str, title: str | None = None) -> Conversation:
    conversation = Conversation(workspace_id=workspace_id, title=(title or "Nouvelle conversation")[:160])
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


def serialize_conversation(conversation: Conversation) -> dict:
    return {
        "id": conversation.id,
        "workspace_id": conversation.workspace_id,
        "title": conversation.title,
        "created_at": conversation.created_at.isoformat() if conversation.created_at else None,
        "updated_at": conversation.updated_at.isoformat() if conversation.updated_at else None,
    }


def serialize_message(message: WorkspaceMessage) -> dict:
    return {
        "id": message.id,
        "conversation_id": message.conversation_id,
        "role": message.role,
        "content": message.content,
        "citations": json.loads(message.citations_json or "[]"),
        "created_at": message.created_at.isoformat() if message.created_at else None,
    }


def build_citations(workspace_id: str, text: str) -> tuple[str, list[dict]]:
    results = search_workspace_documents(workspace_id, text)
    citations = []
    context = []
    for document, _score in results:
        metadata = document.metadata
        citations.append(
            {
                "document_id": metadata.get("document_id"),
                "document_name": metadata.get("document_name", "Document"),
                "excerpt": document.page_content[:280],
            }
        )
        context.append(document.page_content)
    return "\n\n".join(context), citations
