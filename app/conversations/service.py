import json
from datetime import datetime, timezone

from fastapi import HTTPException
from openai import OpenAI
from sqlalchemy.orm import Session

from app.core.config import settings
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


def recent_messages(db: Session, conversation_id: str, limit: int = 20) -> list[WorkspaceMessage]:
    """Return the newest bounded history in chronological order."""
    messages = (
        db.query(WorkspaceMessage)
        .filter_by(conversation_id=conversation_id)
        .order_by(WorkspaceMessage.created_at.desc(), WorkspaceMessage.id.desc())
        .limit(limit)
        .all()
    )
    return list(reversed(messages))


def reply_to_conversation(
    db: Session, workspace_id: str, conversation: Conversation, content: str
) -> tuple[WorkspaceMessage, WorkspaceMessage]:
    """Persist a Workspace-bound turn and its provider response."""
    text = content.strip()
    if not text:
        raise HTTPException(status_code=422, detail="Le message est requis.")

    user_message = WorkspaceMessage(
        conversation_id=conversation.id,
        role="user",
        content=text,
        created_at=datetime.now(timezone.utc),
    )
    db.add(user_message)
    conversation.updated_at = datetime.now(timezone.utc)
    db.add(conversation)
    db.commit()

    try:
        context, citations = build_citations(workspace_id, text)
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail="La recherche dans les connaissances est temporairement indisponible.",
        ) from exc
    system = (
        "Tu es Nova, l’assistant du Workspace TRIDENT GENESIS. Réponds en français. "
        "Utilise prioritairement les connaissances fournies et cite les sources disponibles. "
        f"\n\nConnaissances du Workspace :\n{context or 'Aucune connaissance indexée.'}"
    )
    conversation_input = [{"role": "system", "content": system}] + [
        {"role": message.role, "content": message.content}
        for message in recent_messages(db, conversation.id)
    ]
    try:
        response = OpenAI(api_key=settings.OPENAI_API_KEY).responses.create(
            model="gpt-4.1-mini", input=conversation_input
        )
        reply = response.output_text
    except Exception as exc:
        # The user turn is intentionally durable; clients reload history after this recoverable failure.
        raise HTTPException(status_code=503, detail="Le service IA est temporairement indisponible.") from exc

    assistant_message = WorkspaceMessage(
        conversation_id=conversation.id,
        role="assistant",
        content=reply,
        citations_json=json.dumps(citations, ensure_ascii=False),
        created_at=datetime.now(timezone.utc),
    )
    if conversation.title == "Nouvelle conversation":
        conversation.title = text[:80]
    conversation.updated_at = datetime.now(timezone.utc)
    db.add(assistant_message)
    db.commit()
    db.refresh(assistant_message)
    return user_message, assistant_message
