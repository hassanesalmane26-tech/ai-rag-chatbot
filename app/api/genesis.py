"""Public Genesis API. All product resources are nested below Workspace."""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.conversations.service import create_conversation, reply_to_conversation, serialize_conversation, serialize_message
from app.database.database import get_db
from app.database.genesis_models import Conversation, Workspace, WorkspaceDocument, WorkspaceMessage
from app.knowledge.service import create_document, delete_document, serialize_document
from app.workspaces.service import ensure_genesis_workspace, serialize_workspace, workspace_activity

router = APIRouter(prefix="/v1", tags=["Genesis"])


class WorkspaceCreateInput(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=1000)


class WorkspaceUpdateInput(BaseModel):
    name: str | None = Field(default=None, max_length=120)
    description: str | None = Field(default=None, max_length=1000)


class ConversationInput(BaseModel):
    title: str | None = Field(default=None, max_length=160)


class MessageInput(BaseModel):
    content: str = Field(min_length=1, max_length=12000)


def data(value, meta: dict | None = None):
    return {"data": value, "meta": meta or {}}


def get_workspace(workspace_id: str, db: Session) -> Workspace:
    workspace = db.get(Workspace, workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace introuvable.")
    return workspace


def get_conversation(workspace_id: str, conversation_id: str, db: Session) -> Conversation:
    conversation = db.get(Conversation, conversation_id)
    if not conversation or conversation.workspace_id != workspace_id:
        raise HTTPException(status_code=404, detail="Conversation introuvable.")
    return conversation


@router.get("/workspaces")
def list_workspaces(db: Session = Depends(get_db)):
    ensure_genesis_workspace(db)
    workspaces = db.query(Workspace).order_by(Workspace.updated_at.desc()).all()
    return data([serialize_workspace(workspace) for workspace in workspaces])


@router.post("/workspaces", status_code=201)
def create_workspace(payload: WorkspaceCreateInput, db: Session = Depends(get_db)):
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="Le nom du Workspace est requis.")
    workspace = Workspace(name=name, description=payload.description)
    db.add(workspace)
    db.commit()
    db.refresh(workspace)
    return data(serialize_workspace(workspace))


@router.get("/workspaces/{workspace_id}")
def read_workspace(workspace_id: str, db: Session = Depends(get_db)):
    return data(serialize_workspace(get_workspace(workspace_id, db)))


@router.patch("/workspaces/{workspace_id}")
def update_workspace(workspace_id: str, payload: WorkspaceUpdateInput, db: Session = Depends(get_db)):
    workspace = get_workspace(workspace_id, db)
    fields = payload.model_fields_set
    if not fields:
        raise HTTPException(status_code=422, detail="Aucune modification de Workspace fournie.")
    if "name" in fields:
        if payload.name is None or not payload.name.strip():
            raise HTTPException(status_code=422, detail="Le nom du Workspace est requis.")
        workspace.name = payload.name.strip()
    if "description" in fields:
        workspace.description = payload.description
    db.commit()
    db.refresh(workspace)
    return data(serialize_workspace(workspace))


@router.get("/workspaces/{workspace_id}/overview")
def read_overview(workspace_id: str, db: Session = Depends(get_db)):
    return data(workspace_activity(db, get_workspace(workspace_id, db)))


@router.get("/workspaces/{workspace_id}/conversations")
def list_conversations(workspace_id: str, db: Session = Depends(get_db)):
    get_workspace(workspace_id, db)
    conversations = (
        db.query(Conversation)
        .filter_by(workspace_id=workspace_id)
        .order_by(Conversation.updated_at.desc(), Conversation.id.desc())
        .all()
    )
    return data([serialize_conversation(conversation) for conversation in conversations])


@router.post("/workspaces/{workspace_id}/conversations", status_code=201)
def new_conversation(workspace_id: str, payload: ConversationInput, db: Session = Depends(get_db)):
    get_workspace(workspace_id, db)
    return data(serialize_conversation(create_conversation(db, workspace_id, payload.title)))


@router.get("/workspaces/{workspace_id}/conversations/{conversation_id}")
def read_conversation(workspace_id: str, conversation_id: str, db: Session = Depends(get_db)):
    conversation = get_conversation(workspace_id, conversation_id, db)
    messages = (
        db.query(WorkspaceMessage)
        .filter_by(conversation_id=conversation.id)
        .order_by(WorkspaceMessage.created_at.asc(), WorkspaceMessage.id.asc())
        .all()
    )
    return data({**serialize_conversation(conversation), "messages": [serialize_message(message) for message in messages]})


@router.post("/workspaces/{workspace_id}/conversations/{conversation_id}/messages", status_code=201)
def send_message(workspace_id: str, conversation_id: str, payload: MessageInput, db: Session = Depends(get_db)):
    conversation = get_conversation(workspace_id, conversation_id, db)
    user_message, assistant_message = reply_to_conversation(
        db, workspace_id, conversation, payload.content
    )
    return data({
        **serialize_message(assistant_message),
        "user_message": serialize_message(user_message),
    })


@router.get("/workspaces/{workspace_id}/documents")
def list_documents(workspace_id: str, db: Session = Depends(get_db)):
    get_workspace(workspace_id, db)
    documents = db.query(WorkspaceDocument).filter_by(workspace_id=workspace_id).order_by(WorkspaceDocument.created_at.desc()).all()
    return data([serialize_document(document) for document in documents])


@router.post("/workspaces/{workspace_id}/documents", status_code=201)
async def upload_document(workspace_id: str, file: UploadFile = File(...), db: Session = Depends(get_db)):
    get_workspace(workspace_id, db)
    return data(serialize_document(await create_document(db, workspace_id, file)))


@router.delete("/workspaces/{workspace_id}/documents/{document_id}")
def remove_document(workspace_id: str, document_id: str, db: Session = Depends(get_db)):
    document = db.get(WorkspaceDocument, document_id)
    if not document or document.workspace_id != workspace_id:
        raise HTTPException(status_code=404, detail="Document introuvable.")
    delete_document(db, document)
    return data({"id": document_id, "deleted": True})
