"""Durable image lifecycle. Atomic claims prevent duplicate provider invocation."""
import hashlib
import json
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from app.database.genesis_models import Conversation, Workspace, WorkspaceMessage
from app.identity.models import User
from app.images.contracts import ASPECT_SIZES, ImageGenerationRequest, normalize_image
from app.images.models import ImageArtifact
from app.governance.audit import append_audit_event
from app.governance.quotas import consume_hourly_quota
from app.knowledge.storage import LocalObjectStorage
from app.tenancy.service import tenant_context_for_workspace, TenantAccessDenied
from app.identity.contracts import AuthenticatedPrincipal

MAX_ATTEMPTS = 3


def image_storage(config):
    return LocalObjectStorage(config.images_path or config.documents_path / "nova-images")


def serialize_artifact(item, actor_id):
    owns_task = item.user_id == actor_id
    return {
        "id": item.id, "type": "image", "workspace_id": item.workspace_id,
        "conversation_id": item.conversation_id, "message_id": item.message_id,
        "prompt": item.prompt, "aspect_ratio": item.aspect_ratio, "status": item.status,
        "source_id": item.source_id, "width": item.width, "height": item.height,
        "created_at": item.created_at.isoformat(), "attempts": item.attempts,
        "error": "La création n’a pas abouti." if item.status == "failed" else None,
        "can_retry": owns_task and item.status == "failed" and item.attempts < MAX_ATTEMPTS,
        "can_cancel": owns_task and item.status == "queued",
    }


def get_artifact(db, workspace_id, artifact_id):
    item = db.get(ImageArtifact, artifact_id)
    if item is None or item.workspace_id != workspace_id:
        raise HTTPException(404, "Image introuvable dans ce Workspace.")
    return item


def enqueue_image(db, tenant, conversation_id, prompt, aspect_ratio, request_key, config, *, source_id=None, source=None):
    if config.image_provider == "disabled" or not config.openai_key():
        raise HTTPException(503, "La création d’images n’est pas configurée. Nova reste disponible pour vos conversations.")
    prompt = prompt.strip()
    if not prompt or len(prompt) > 4000 or aspect_ratio not in ASPECT_SIZES:
        raise HTTPException(422, "Description ou format d’image invalide.")
    if not request_key or len(request_key) > 64 or source_id and source:
        raise HTTPException(422, "Requête d’image invalide.")
    conversation = db.get(Conversation, conversation_id)
    if conversation is None or conversation.workspace_id != tenant.workspace_id:
        raise HTTPException(404, "Conversation introuvable.")
    if source_id:
        parent = get_artifact(db, tenant.workspace_id, source_id)
        if parent.conversation_id != conversation_id or parent.status != "completed":
            raise HTTPException(409, "Sélectionnez une image terminée dans cette conversation.")
    else:
        parent = None
    try:
        normalized = normalize_image(source)[0] if source is not None else None
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    fingerprint = hashlib.sha256(json.dumps([prompt, aspect_ratio, source_id, hashlib.sha256(normalized).hexdigest() if normalized else None]).encode()).hexdigest()
    # Serialize enqueue and operational queue bounds per Workspace on PostgreSQL.
    db.query(Workspace).filter_by(id=tenant.workspace_id).with_for_update().one()
    existing = db.query(ImageArtifact).filter_by(conversation_id=conversation_id, request_key=request_key).first()
    if existing:
        if existing.request_hash != fingerprint or existing.user_id != tenant.principal.user_id:
            raise HTTPException(409, "Cette requête a déjà été utilisée pour une autre création.")
        return existing
    if db.query(ImageArtifact).filter(ImageArtifact.workspace_id == tenant.workspace_id, ImageArtifact.status.in_(["queued", "generating"])).count() >= 3:
        raise HTTPException(429, "Trois créations sont déjà en cours dans ce Workspace.")
    consume_hourly_quota(db, tenant.principal, tenant.organization_id, "messages.per_hour")
    identifier = str(uuid.uuid4())
    source_key = parent.output_key if parent else None
    owned_source = None
    if normalized:
        owned_source = f"{tenant.workspace_id}/{identifier}/source.png"
        image_storage(config).put(owned_source, normalized)
        source_key = owned_source
    now = datetime.now(timezone.utc)
    user_message = WorkspaceMessage(id=str(uuid.uuid4()), conversation_id=conversation_id, role="user", content=prompt, created_at=now)
    assistant = WorkspaceMessage(id=str(uuid.uuid4()), conversation_id=conversation_id, role="assistant", content="Création d’image demandée.", created_at=now + timedelta(microseconds=1))
    item = ImageArtifact(id=identifier, workspace_id=tenant.workspace_id, conversation_id=conversation_id,
        message_id=assistant.id, user_message_id=user_message.id, user_id=tenant.principal.user_id, request_key=request_key, request_hash=fingerprint,
        prompt=prompt, aspect_ratio=aspect_ratio, source_id=source_id, source_key=source_key, status="queued")
    try:
        db.add_all([user_message, assistant]); db.flush()
        db.add(item)
        if conversation.title == "Nouvelle conversation": conversation.title = prompt[:80]
        conversation.updated_at = now
        append_audit_event(db, action="image.queued", resource_type="image", resource_id=item.id,
            principal=tenant.principal, organization_id=tenant.organization_id, workspace_id=tenant.workspace_id)
        db.commit(); db.refresh(item)
        return item
    except Exception as exc:
        db.rollback()
        if owned_source: image_storage(config).delete(owned_source)
        if isinstance(exc, IntegrityError):
            existing = db.query(ImageArtifact).filter_by(conversation_id=conversation_id, request_key=request_key).first()
            if existing and existing.request_hash == fingerprint and existing.user_id == tenant.principal.user_id:
                return existing
        raise


def change_task(db, tenant, artifact_id, action, config):
    item = get_artifact(db, tenant.workspace_id, artifact_id)
    if item.user_id != tenant.principal.user_id:
        raise HTTPException(403, "Seul l’auteur peut modifier cette tâche.")
    expected, target = ("failed", "queued") if action == "retry" else ("queued", "cancelled")
    if action == "retry":
        if config.image_provider == "disabled" or not config.openai_key(): raise HTTPException(503, "Création d’images indisponible.")
        db.query(Workspace).filter_by(id=tenant.workspace_id).with_for_update().one()
        if db.query(ImageArtifact).filter(ImageArtifact.workspace_id == tenant.workspace_id, ImageArtifact.status.in_(["queued", "generating"])).count() >= 3:
            raise HTTPException(429, "Trois créations sont déjà en cours dans ce Workspace.")
        consume_hourly_quota(db, tenant.principal, tenant.organization_id, "messages.per_hour")
    changed = db.query(ImageArtifact).filter(ImageArtifact.id == item.id, ImageArtifact.status == expected, ImageArtifact.attempts < MAX_ATTEMPTS).update({"status": target, "error_code": None, "updated_at": datetime.now(timezone.utc)}, synchronize_session=False)
    if not changed:
        db.rollback(); raise HTTPException(409, "Cette action n’est plus disponible.")
    append_audit_event(db, action=f"image.{action}", resource_type="image", resource_id=item.id, principal=tenant.principal, organization_id=tenant.organization_id, workspace_id=tenant.workspace_id)
    db.commit(); db.refresh(item)
    return item


def process_image(db, artifact_id, provider, storage):
    claimed = db.query(ImageArtifact).filter_by(id=artifact_id, status="queued").update({"status": "generating", "attempts": ImageArtifact.attempts + 1, "updated_at": datetime.now(timezone.utc)}, synchronize_session=False)
    db.commit()
    if not claimed: return False
    item = db.get(ImageArtifact, artifact_id); db.refresh(item)
    try:
        user = db.get(User, item.user_id)
        if user is None or user.status != "active": raise TenantAccessDenied()
        tenant_context_for_workspace(db, AuthenticatedPrincipal(item.user_id, "worker", "worker"), item.workspace_id)
        source = storage.read(item.source_key) if item.source_key else None
        # Include the parent description for bounded iterative context, never unrelated Memory.
        parent = db.get(ImageArtifact, item.source_id) if item.source_id else None
        prompt = f"Previous image description: {parent.prompt}\nRequested edit: {item.prompt}" if parent else item.prompt
        result = provider.generate(ImageGenerationRequest(prompt, item.aspect_ratio, source))
        content, width, height = normalize_image(result.content)
        key = f"{item.workspace_id}/{item.id}/result.png"
        storage.put(key, content)
        completed = db.query(ImageArtifact).filter_by(id=item.id, status="generating").update({"status": "completed", "output_key": key, "width": width, "height": height, "provider": result.provider, "model": result.model, "updated_at": datetime.now(timezone.utc)}, synchronize_session=False)
        if completed:
            db.query(WorkspaceMessage).filter_by(id=item.message_id).update({"content": "Image créée dans ce Workspace."})
        db.commit()
        if not completed: storage.delete(key)
    except Exception:
        db.rollback()
        db.query(ImageArtifact).filter_by(id=artifact_id, status="generating").update({"status": "failed", "error_code": "generation_failed", "updated_at": datetime.now(timezone.utc)}, synchronize_session=False)
        db.commit()
    return True


def reconcile_images(db):
    """A lost provider response is ambiguous: fail visibly, never rebill automatically."""
    count = db.query(ImageArtifact).filter(ImageArtifact.status == "generating", ImageArtifact.updated_at < datetime.now(timezone.utc) - timedelta(minutes=10)).update({"status": "failed", "error_code": "interrupted"}, synchronize_session=False)
    db.commit()
    return count
