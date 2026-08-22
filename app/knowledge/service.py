import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path

from fastapi import HTTPException, UploadFile
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database.genesis_models import WorkspaceDocument, new_id
from app.database.genesis_models import Workspace
from app.knowledge.jobs import claim_job, enqueue_ingestion, fail_job, finish_job
from app.knowledge.storage import LocalObjectStorage
from app.rag.loader import load_document
from app.rag.splitter import split_documents
from app.rag.vectorstore import vectorstore

DOCUMENTS_ROOT = settings.documents_path
ALLOWED_SUFFIXES = {".pdf", ".txt", ".docx"}
MAX_UPLOAD_BYTES = 20 * 1024 * 1024
RETRYABLE_STATUSES = {"pending", "processing", "failed"}


def _storage() -> LocalObjectStorage:
    return LocalObjectStorage(DOCUMENTS_ROOT)


def _safe_display_name(filename: str | None) -> str:
    candidate = Path(filename or "document").name.strip()
    candidate = re.sub(r"[^\w. ()-]", "_", candidate, flags=re.UNICODE)
    if not candidate or Path(candidate).suffix.lower() not in ALLOWED_SUFFIXES:
        raise HTTPException(status_code=415, detail="Format de document non pris en charge.")
    return candidate[:200]


def _document_path(document: WorkspaceDocument) -> Path:
    return _storage().path(document.storage_key or f"{document.workspace_id}/{document.storage_name}")


def _chunk_ids(document: WorkspaceDocument, chunks: list) -> list[str]:
    return [f"{document.id}:v{document.version}:{position}" for position, _chunk in enumerate(chunks)]


def _original_matches(document: WorkspaceDocument) -> bool:
    path = _document_path(document)
    if not path.is_file():
        return False
    if not document.content_hash:
        return True
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest() == document.content_hash


def ingest_document(db: Session, document: WorkspaceDocument) -> WorkspaceDocument:
    """Index one durable original; safe to retry after any partial failure."""
    storage_key = document.storage_key or f"{document.workspace_id}/{document.storage_name}"
    document.status = "processing"
    document.ingestion_attempts = (document.ingestion_attempts or 0) + 1
    document.error_message = None
    db.commit()
    try:
        with _storage().materialize(storage_key) as destination:
            chunks = split_documents(load_document(str(destination)))
        for position, chunk in enumerate(chunks):
            chunk.metadata.update(
                {
                    "workspace_id": document.workspace_id,
                    "document_id": document.id,
                    "document_name": document.display_name,
                    "document_version": document.version,
                    "content_hash": document.content_hash or "legacy",
                    "chunk_position": position,
                }
            )
        vectorstore.delete(where={"document_id": document.id})
        if chunks:
            vectorstore.add_documents(chunks, ids=_chunk_ids(document, chunks))
        document.status = "indexed"
        document.chunk_count = len(chunks)
        document.indexed_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(document)
        return document
    except Exception as exc:
        db.rollback()
        durable = db.get(WorkspaceDocument, document.id)
        if durable:
            durable.status = "failed"
            durable.error_message = "Indexation impossible. Une nouvelle tentative est possible."
            db.commit()
        raise HTTPException(status_code=503, detail="Le document n’a pas pu être indexé.") from exc


def _process_ingestion_job(
    db: Session, document: WorkspaceDocument, *, manual_retry: bool = False
) -> WorkspaceDocument:
    workspace = db.get(Workspace, document.workspace_id)
    if not workspace or not workspace.organization_id:
        raise HTTPException(status_code=409, detail="Le Workspace du document est incohérent.")
    job = enqueue_ingestion(
        db, workspace.organization_id, document.workspace_id, document.id, document.version
    )
    if manual_retry and job.status in {"queued", "failed"}:
        job.status = "queued"
        job.available_at = datetime.now(timezone.utc)
    db.commit()
    claimed = claim_job(db, job.id, "inline-api")
    if claimed is None:
        if job.status == "succeeded" and document.status == "indexed":
            return document
        raise HTTPException(status_code=409, detail="L’ingestion du document est déjà en cours.")
    try:
        result = ingest_document(db, document)
        finish_job(db, claimed)
        return result
    except HTTPException:
        fail_job(db, claimed, "Document ingestion failed")
        raise


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
        if existing.status == "indexed":
            return existing
        stored = _storage().put(
            existing.storage_key or f"{existing.workspace_id}/{existing.storage_name}", content
        )
        existing.original_etag = stored.etag
        db.commit()
        return _process_ingestion_job(db, existing)

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
        status="pending",
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
        if existing.status == "indexed":
            return existing
        stored = _storage().put(
            existing.storage_key or f"{existing.workspace_id}/{existing.storage_name}", content
        )
        existing.original_etag = stored.etag
        db.commit()
        return _process_ingestion_job(db, existing)
    db.refresh(document)

    try:
        stored = _storage().put(document.storage_key, content)
        document.original_etag = stored.etag
        db.commit()
    except Exception as exc:
        document.status = "failed"
        document.error_message = "Stockage de l’original impossible."
        db.commit()
        raise HTTPException(status_code=503, detail="Le document n’a pas pu être stocké.") from exc
    return _process_ingestion_job(db, document)


def retry_document(db: Session, document: WorkspaceDocument) -> WorkspaceDocument:
    if document.status not in RETRYABLE_STATUSES:
        raise HTTPException(status_code=409, detail="Ce document ne nécessite pas de nouvelle tentative.")
    if not _original_matches(document):
        document.status = "failed"
        document.error_message = "Original introuvable ou incohérent."
        db.commit()
        raise HTTPException(status_code=409, detail="L’original du document est introuvable ou incohérent.")
    return _process_ingestion_job(db, document, manual_retry=True)


def delete_document(db: Session, document: WorkspaceDocument) -> None:
    document.status = "deleting"
    document.error_message = None
    db.commit()
    try:
        vectorstore.delete(where={"document_id": document.id})
        _storage().delete(document.storage_key or f"{document.workspace_id}/{document.storage_name}")
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
        return _storage().read(storage_key)
    except (OSError, ValueError) as exc:
        raise HTTPException(status_code=404, detail="Le fichier original est introuvable.") from exc


def serialize_document(document: WorkspaceDocument) -> dict:
    return {
        "id": document.id,
        "workspace_id": document.workspace_id,
        "display_name": document.display_name,
        "media_type": document.media_type,
        "size_bytes": document.size_bytes,
        "storage_backend": document.storage_backend,
        "version": document.version,
        "status": document.status,
        "ingestion_attempts": document.ingestion_attempts,
        "chunk_count": document.chunk_count,
        "error_message": document.error_message,
        "created_at": document.created_at.isoformat() if document.created_at else None,
        "updated_at": document.updated_at.isoformat() if document.updated_at else None,
        "indexed_at": document.indexed_at.isoformat() if document.indexed_at else None,
    }
