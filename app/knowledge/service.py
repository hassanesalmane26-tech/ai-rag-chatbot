import hashlib
import re
from pathlib import Path

from fastapi import HTTPException, UploadFile
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database.genesis_models import WorkspaceDocument, new_id
from app.database.genesis_models import Workspace
from app.knowledge.jobs import enqueue_ingestion, requeue_ingestion
from app.knowledge.models import KnowledgeJob
from app.knowledge.state import (
    INDEXED,
    PENDING_PROCESSING,
    PENDING_SCAN,
    PROCESSING_FAILED,
    RETRYABLE_STATUSES,
    SCAN_FAILED,
    canonical_status,
    status_view,
    transition_document,
)
from app.knowledge.storage import LocalObjectStorage, storage_for_backend
from app.rag.vectorstore import vectorstore

DOCUMENTS_ROOT = settings.documents_path
ALLOWED_SUFFIXES = {".pdf", ".txt", ".docx"}
MAX_UPLOAD_BYTES = 20 * 1024 * 1024


def _storage() -> LocalObjectStorage:
    return LocalObjectStorage(DOCUMENTS_ROOT)


def _safe_display_name(filename: str | None) -> str:
    candidate = Path(filename or "document").name.strip()
    candidate = re.sub(r"[^\w. ()-]", "_", candidate, flags=re.UNICODE)
    if not candidate or Path(candidate).suffix.lower() not in ALLOWED_SUFFIXES:
        raise HTTPException(status_code=415, detail="Format de document non pris en charge.")
    return candidate[:200]


def _original_matches(document: WorkspaceDocument) -> bool:
    storage = storage_for_backend(document.storage_backend, local_root=DOCUMENTS_ROOT)
    key = document.storage_key or f"{document.workspace_id}/{document.storage_name}"
    if not storage.exists(key):
        return False
    if not document.content_hash:
        return True
    digest = hashlib.sha256()
    with storage.materialize(key) as path:
        with path.open("rb") as source:
            for block in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(block)
    return digest.hexdigest() == document.content_hash


def _enqueue_document(db: Session, document: WorkspaceDocument):
    workspace = db.get(Workspace, document.workspace_id)
    if not workspace or not workspace.organization_id:
        raise HTTPException(status_code=409, detail="Le Workspace du document est incohérent.")
    job = enqueue_ingestion(
        db, workspace.organization_id, document.workspace_id, document.id, document.version
    )
    db.commit()
    return job


async def create_document(db: Session, workspace_id: str, upload: UploadFile) -> WorkspaceDocument:
    display_name = _safe_display_name(upload.filename)
    content = await upload.read(MAX_UPLOAD_BYTES + 1)
    if not content:
        raise HTTPException(status_code=422, detail="Le document est vide.")
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Le document dépasse la limite de 20 Mo.")

    content_hash = hashlib.sha256(content).hexdigest()
    existing = (
        db.query(WorkspaceDocument)
        .filter_by(workspace_id=workspace_id, content_hash=content_hash)
        .first()
    )
    if existing:
        if canonical_status(existing.status) == INDEXED:
            return existing
        stored = _storage().put(
            existing.storage_key or f"{existing.workspace_id}/{existing.storage_name}", content
        )
        existing.original_etag = stored.etag
        db.commit()
        if canonical_status(existing.status) in RETRYABLE_STATUSES:
            transition_document(existing, PENDING_SCAN)
        _enqueue_document(db, existing)
        return existing

    storage_name = f"{new_id()}{Path(display_name).suffix.lower()}"
    document = WorkspaceDocument(
        workspace_id=workspace_id,
        display_name=display_name,
        storage_name=storage_name,
        storage_backend="local",
        storage_key=f"{workspace_id}/{storage_name}",
        media_type=upload.content_type or "application/octet-stream",
        size_bytes=len(content),
        content_hash=content_hash,
        status="uploaded",
    )
    db.add(document)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = (
            db.query(WorkspaceDocument)
            .filter_by(workspace_id=workspace_id, content_hash=content_hash)
            .one()
        )
        if canonical_status(existing.status) == INDEXED:
            return existing
        stored = _storage().put(
            existing.storage_key or f"{existing.workspace_id}/{existing.storage_name}", content
        )
        existing.original_etag = stored.etag
        db.commit()
        if canonical_status(existing.status) in RETRYABLE_STATUSES:
            transition_document(existing, PENDING_SCAN)
        _enqueue_document(db, existing)
        return existing
    db.refresh(document)

    try:
        stored = _storage().put(document.storage_key, content)
        document.original_etag = stored.etag
        db.commit()
    except Exception as exc:
        document.status = PROCESSING_FAILED
        document.error_message = "Stockage de l’original impossible."
        db.commit()
        raise HTTPException(status_code=503, detail="Le document n’a pas pu être stocké.") from exc
    transition_document(document, PENDING_SCAN)
    _enqueue_document(db, document)
    return document


def retry_document(db: Session, document: WorkspaceDocument) -> WorkspaceDocument:
    normalized = canonical_status(document.status)
    if normalized not in RETRYABLE_STATUSES:
        raise HTTPException(status_code=409, detail="Ce document ne nécessite pas de nouvelle tentative.")
    if not _original_matches(document):
        document.status = PROCESSING_FAILED
        document.error_message = "Original introuvable ou incohérent."
        db.commit()
        raise HTTPException(status_code=409, detail="L’original du document est introuvable ou incohérent.")
    target = PENDING_SCAN if normalized == SCAN_FAILED else PENDING_PROCESSING
    job = _enqueue_document(db, document)
    if job.attempts >= job.max_attempts:
        raise HTTPException(status_code=409, detail="Le nombre maximal de tentatives est atteint.")
    transition_document(document, target)
    try:
        requeue_ingestion(db, job)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Le nombre maximal de tentatives est atteint.") from exc
    db.refresh(document)
    return document


def delete_document(db: Session, document: WorkspaceDocument) -> None:
    document.status = "deleting"
    document.error_message = None
    db.commit()
    try:
        vectorstore.delete(where={"document_id": document.id})
        storage = storage_for_backend(document.storage_backend, local_root=DOCUMENTS_ROOT)
        storage.delete(document.storage_key or f"{document.workspace_id}/{document.storage_name}")
        db.query(KnowledgeJob).filter_by(document_id=document.id).delete(synchronize_session=False)
        db.delete(document)
        db.commit()
    except Exception as exc:
        db.rollback()
        durable = db.get(WorkspaceDocument, document.id)
        if durable:
            durable.status = "delete_failed"
            durable.error_message = "Suppression incomplète. Une nouvelle tentative est possible."
            db.commit()
        raise HTTPException(status_code=503, detail="Le document n’a pas pu être supprimé complètement.") from exc


def read_document_original(document: WorkspaceDocument) -> bytes:
    """Read one already-authorized original through the storage boundary."""
    storage_key = document.storage_key or f"{document.workspace_id}/{document.storage_name}"
    try:
        storage = storage_for_backend(document.storage_backend, local_root=DOCUMENTS_ROOT)
        return storage.read(storage_key)
    except (OSError, ValueError) as exc:
        raise HTTPException(status_code=404, detail="Le fichier original est introuvable.") from exc


def serialize_document(document: WorkspaceDocument, db: Session | None = None) -> dict:
    lifecycle = status_view(document.status)
    job = db.query(KnowledgeJob).filter_by(
        idempotency_key=f"ingest:{document.id}:v{document.version}"
    ).one_or_none() if db is not None else None
    retryable = lifecycle.retryable and (job is None or job.attempts < job.max_attempts)
    return {
        "id": document.id,
        "workspace_id": document.workspace_id,
        "display_name": document.display_name,
        "media_type": document.media_type,
        "size_bytes": document.size_bytes,
        "storage_backend": document.storage_backend,
        "version": document.version,
        "status": lifecycle.status,
        "ready": lifecycle.ready,
        "retryable": retryable,
        "processing": {
            "attempts": job.attempts if job else document.ingestion_attempts,
            "max_attempts": job.max_attempts if job else None,
        },
        "ingestion_attempts": document.ingestion_attempts,
        "chunk_count": document.chunk_count,
        "error_message": document.error_message,
        "created_at": document.created_at.isoformat() if document.created_at else None,
        "updated_at": document.updated_at.isoformat() if document.updated_at else None,
        "indexed_at": document.indexed_at.isoformat() if document.indexed_at else None,
    }
