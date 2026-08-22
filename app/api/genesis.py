"""Public Genesis API. All product resources are nested below Workspace."""

from urllib.parse import quote

from fastapi import APIRouter, Depends, File, HTTPException, Request, Response, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.conversations.service import create_conversation, reply_to_conversation, serialize_conversation, serialize_message
from app.api.contracts import PageParams, page_meta
from app.database.database import get_db
from app.database.genesis_models import Conversation, Workspace, WorkspaceDocument, WorkspaceMessage
from app.identity.contracts import AuthenticatedPrincipal
from app.governance.audit import append_audit_event
from app.governance.quotas import consume_hourly_quota, enforce_resource_quota
from app.knowledge.service import (
    create_document,
    delete_document,
    read_document_original,
    retry_document,
    serialize_document,
)
from app.security.authorization import (
    organization_for_workspace_creation,
    require_workspace_access,
    require_workspace_admin,
    visible_workspaces_query,
)
from app.security.dependencies import require_principal
from app.tenancy.service import TenantContext
from app.workspaces.service import (
    create_genesis_workspace,
    serialize_workspace,
    workspace_activity,
)

router = APIRouter(prefix="/v1", tags=["Genesis"], dependencies=[Depends(require_principal)])


class WorkspaceCreateInput(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=1000)
    organization_id: str | None = Field(default=None, max_length=36)


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
def list_workspaces(
    request: Request,
    db: Session = Depends(get_db),
    principal: AuthenticatedPrincipal = Depends(require_principal),
    page: PageParams = Depends(),
):
    application_session = getattr(request.state, "application_session", None)
    query = visible_workspaces_query(
        db, principal, getattr(application_session, "active_organization_id", None)
    )
    total = query.count()
    workspaces = query.order_by(Workspace.updated_at.desc(), Workspace.id.desc()).offset(page.offset).limit(page.limit).all()
    return data([serialize_workspace(workspace) for workspace in workspaces], {"pagination": page_meta(page, total)})


@router.post("/workspaces", status_code=201)
def create_workspace(
    payload: WorkspaceCreateInput,
    request: Request,
    db: Session = Depends(get_db),
    principal: AuthenticatedPrincipal = Depends(require_principal),
):
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="Le nom du Workspace est requis.")
    application_session = getattr(request.state, "application_session", None)
    organization_id = payload.organization_id or getattr(
        application_session, "active_organization_id", None
    )
    organization, _membership = organization_for_workspace_creation(db, principal, organization_id)
    current = db.query(Workspace).filter_by(organization_id=organization.id).count()
    enforce_resource_quota(db, principal, organization.id, "workspaces.total", current)
    workspace = create_genesis_workspace(db, name, payload.description, organization.id)
    append_audit_event(db, action="workspace.created", resource_type="workspace", resource_id=workspace.id,
                       principal=principal, organization_id=organization.id, workspace_id=workspace.id,
                       request_id=request.state.request_id)
    db.commit()
    return data(serialize_workspace(workspace))


@router.get("/workspaces/{workspace_id}")
def read_workspace(
    workspace_id: str,
    db: Session = Depends(get_db),
    _tenant: TenantContext = Depends(require_workspace_access),
):
    return data(serialize_workspace(get_workspace(workspace_id, db)))


@router.patch("/workspaces/{workspace_id}")
def update_workspace(
    workspace_id: str,
    payload: WorkspaceUpdateInput,
    request: Request,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(require_workspace_admin),
    principal: AuthenticatedPrincipal = Depends(require_principal),
):
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
    append_audit_event(db, action="workspace.updated", resource_type="workspace", resource_id=workspace.id,
                       principal=principal, organization_id=tenant.organization_id, workspace_id=workspace.id,
                       request_id=request.state.request_id, metadata={"fields": sorted(fields)})
    db.commit()
    return data(serialize_workspace(workspace))


@router.get("/workspaces/{workspace_id}/overview")
def read_overview(
    workspace_id: str,
    db: Session = Depends(get_db),
    _tenant: TenantContext = Depends(require_workspace_access),
):
    return data(workspace_activity(db, get_workspace(workspace_id, db)))


@router.get("/workspaces/{workspace_id}/conversations")
def list_conversations(
    workspace_id: str,
    page: PageParams = Depends(),
    db: Session = Depends(get_db),
    _tenant: TenantContext = Depends(require_workspace_access),
):
    get_workspace(workspace_id, db)
    query = db.query(Conversation).filter_by(workspace_id=workspace_id)
    total = query.count()
    conversations = (
        query
        .order_by(Conversation.updated_at.desc(), Conversation.id.desc())
        .offset(page.offset).limit(page.limit)
        .all()
    )
    return data([serialize_conversation(conversation) for conversation in conversations], {"pagination": page_meta(page, total)})


@router.post("/workspaces/{workspace_id}/conversations", status_code=201)
def new_conversation(
    workspace_id: str,
    payload: ConversationInput,
    request: Request,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(require_workspace_access),
    principal: AuthenticatedPrincipal = Depends(require_principal),
):
    get_workspace(workspace_id, db)
    current = db.query(Conversation).filter_by(workspace_id=workspace_id).count()
    enforce_resource_quota(
        db, principal, tenant.organization_id, "conversations.per_workspace", current
    )
    conversation = create_conversation(db, workspace_id, payload.title)
    append_audit_event(db, action="conversation.created", resource_type="conversation", resource_id=conversation.id,
                       principal=principal, organization_id=tenant.organization_id, workspace_id=workspace_id,
                       request_id=request.state.request_id)
    db.commit()
    return data(serialize_conversation(conversation))


@router.get("/workspaces/{workspace_id}/conversations/{conversation_id}")
def read_conversation(
    workspace_id: str,
    conversation_id: str,
    db: Session = Depends(get_db),
    _tenant: TenantContext = Depends(require_workspace_access),
):
    conversation = get_conversation(workspace_id, conversation_id, db)
    messages = (
        db.query(WorkspaceMessage)
        .filter_by(conversation_id=conversation.id)
        .order_by(WorkspaceMessage.created_at.asc(), WorkspaceMessage.id.asc())
        .all()
    )
    return data({**serialize_conversation(conversation), "messages": [serialize_message(message) for message in messages]})


@router.post("/workspaces/{workspace_id}/conversations/{conversation_id}/messages", status_code=201)
def send_message(
    workspace_id: str,
    conversation_id: str,
    payload: MessageInput,
    request: Request,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(require_workspace_access),
    principal: AuthenticatedPrincipal = Depends(require_principal),
):
    conversation = get_conversation(workspace_id, conversation_id, db)
    consume_hourly_quota(db, principal, tenant.organization_id, "messages.per_hour")
    try:
        user_message, assistant_message = reply_to_conversation(
            db, workspace_id, conversation, payload.content
        )
    except HTTPException:
        append_audit_event(
            db, action="conversation.message_failed", resource_type="conversation",
            resource_id=conversation.id, principal=principal,
            organization_id=tenant.organization_id, workspace_id=workspace_id,
            request_id=request.state.request_id, outcome="failure",
        )
        db.commit()
        raise
    append_audit_event(db, action="conversation.message_created", resource_type="conversation",
                       resource_id=conversation.id, principal=principal,
                       organization_id=tenant.organization_id, workspace_id=workspace_id,
                       request_id=request.state.request_id)
    db.commit()
    return data({
        **serialize_message(assistant_message),
        "user_message": serialize_message(user_message),
    })


@router.get("/workspaces/{workspace_id}/documents")
def list_documents(
    workspace_id: str,
    page: PageParams = Depends(),
    db: Session = Depends(get_db),
    _tenant: TenantContext = Depends(require_workspace_access),
):
    get_workspace(workspace_id, db)
    query = db.query(WorkspaceDocument).filter_by(workspace_id=workspace_id)
    total = query.count()
    documents = query.order_by(WorkspaceDocument.created_at.desc(), WorkspaceDocument.id.desc()).offset(page.offset).limit(page.limit).all()
    return data([serialize_document(document) for document in documents], {"pagination": page_meta(page, total)})


@router.get("/workspaces/{workspace_id}/documents/{document_id}/original")
def download_document_original(
    workspace_id: str,
    document_id: str,
    db: Session = Depends(get_db),
    _tenant: TenantContext = Depends(require_workspace_access),
):
    document = db.get(WorkspaceDocument, document_id)
    if not document or document.workspace_id != workspace_id:
        raise HTTPException(status_code=404, detail="Document introuvable.")
    return Response(
        content=read_document_original(document),
        media_type=document.media_type or "application/octet-stream",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(document.display_name)}",
            "Content-Length": str(document.size_bytes),
        },
    )


@router.post("/workspaces/{workspace_id}/documents", status_code=201)
async def upload_document(
    workspace_id: str,
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(require_workspace_access),
    principal: AuthenticatedPrincipal = Depends(require_principal),
):
    get_workspace(workspace_id, db)
    current = db.query(WorkspaceDocument).filter_by(workspace_id=workspace_id).count()
    enforce_resource_quota(db, principal, tenant.organization_id, "documents.per_workspace", current)
    document = await create_document(db, workspace_id, file)
    append_audit_event(db, action="document.created", resource_type="document", resource_id=document.id,
                       principal=principal, organization_id=tenant.organization_id, workspace_id=workspace_id,
                       request_id=request.state.request_id)
    db.commit()
    return data(serialize_document(document))


@router.delete("/workspaces/{workspace_id}/documents/{document_id}")
def remove_document(
    workspace_id: str,
    document_id: str,
    request: Request,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(require_workspace_access),
    principal: AuthenticatedPrincipal = Depends(require_principal),
):
    document = db.get(WorkspaceDocument, document_id)
    if not document or document.workspace_id != workspace_id:
        raise HTTPException(status_code=404, detail="Document introuvable.")
    delete_document(db, document)
    append_audit_event(db, action="document.deleted", resource_type="document", resource_id=document_id,
                       principal=principal, organization_id=tenant.organization_id, workspace_id=workspace_id,
                       request_id=request.state.request_id)
    db.commit()
    return data({"id": document_id, "deleted": True})


@router.post("/workspaces/{workspace_id}/documents/{document_id}/retry")
def retry_failed_document(
    workspace_id: str,
    document_id: str,
    request: Request,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(require_workspace_access),
    principal: AuthenticatedPrincipal = Depends(require_principal),
):
    document = db.get(WorkspaceDocument, document_id)
    if not document or document.workspace_id != workspace_id:
        raise HTTPException(status_code=404, detail="Document introuvable.")
    document = retry_document(db, document)
    append_audit_event(db, action="document.retry_requested", resource_type="document", resource_id=document_id,
                       principal=principal, organization_id=tenant.organization_id, workspace_id=workspace_id,
                       request_id=request.state.request_id)
    db.commit()
    return data(serialize_document(document))
