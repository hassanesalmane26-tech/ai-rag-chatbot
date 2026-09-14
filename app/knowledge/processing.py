"""Worker-compatible, fail-closed Knowledge document processing."""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.config import settings
from app.database.genesis_models import WorkspaceDocument
from app.knowledge.scanner import MalwareScanner, ScanVerdict, scanner_for_environment
from app.knowledge.state import (
    INDEXED,
    PENDING_PROCESSING,
    PENDING_SCAN,
    PROCESSING,
    PROCESSING_FAILED,
    REJECTED,
    SCAN_FAILED,
    SCANNING,
    canonical_status,
    transition_document,
)
from app.knowledge.storage import ObjectStorage, storage_for_backend
from app.rag.loader import load_document
from app.rag.splitter import split_documents
from app.rag.vectorstore import vectorstore


class NonRetryableProcessingError(RuntimeError):
    pass


def _storage(document: WorkspaceDocument) -> ObjectStorage:
    return storage_for_backend(document.storage_backend, local_root=settings.documents_path)


def _chunk_ids(document: WorkspaceDocument, chunks: list) -> list[str]:
    return [f"{document.id}:v{document.version}:{position}" for position, _ in enumerate(chunks)]


def process_document(
    db: Session,
    document: WorkspaceDocument,
    *,
    scanner: MalwareScanner | None = None,
    storage: ObjectStorage | None = None,
    store=None,
) -> WorkspaceDocument:
    """Scan and index one claimed document; repeat calls are idempotent."""
    status = canonical_status(document.status)
    if status == INDEXED:
        return document
    if status == REJECTED:
        raise NonRetryableProcessingError("Rejected documents cannot be processed")
    if status not in {PENDING_SCAN, SCAN_FAILED, PENDING_PROCESSING, PROCESSING_FAILED}:
        raise NonRetryableProcessingError(f"Document is not processable from {status}")

    selected_storage = storage or _storage(document)
    selected_scanner = scanner or scanner_for_environment(settings.environment)
    selected_store = store or vectorstore
    key = document.storage_key or f"{document.workspace_id}/{document.storage_name}"

    # A retry after a successful scan may resume parsing without rescanning.
    if status == SCAN_FAILED:
        transition_document(document, PENDING_SCAN)
        status = PENDING_SCAN
    elif status == PROCESSING_FAILED:
        transition_document(document, PENDING_PROCESSING)
        status = PENDING_PROCESSING
    if status in {PENDING_SCAN, SCAN_FAILED}:
        transition_document(document, SCANNING)
        db.commit()
        try:
            with selected_storage.materialize(key) as path:
                result = selected_scanner.scan(path)
        except Exception as exc:
            transition_document(document, SCAN_FAILED, error="Analyse de sécurité indisponible.")
            db.commit()
            raise RuntimeError("Document scan failed closed") from exc
        if result.verdict is ScanVerdict.UNSAFE:
            transition_document(document, REJECTED, error="Document rejeté par le contrôle de sécurité.")
            db.commit()
            raise NonRetryableProcessingError("Document rejected by malware scanner")
        if result.verdict is not ScanVerdict.SAFE:
            transition_document(document, SCAN_FAILED, error="Résultat du contrôle de sécurité indéterminé.")
            db.commit()
            raise RuntimeError("Document scan result was indeterminate")
        transition_document(document, PENDING_PROCESSING)
        db.commit()

    transition_document(document, PROCESSING)
    document.ingestion_attempts = (document.ingestion_attempts or 0) + 1
    db.commit()
    try:
        with selected_storage.materialize(key) as destination:
            try:
                chunks = split_documents(load_document(str(destination)))
            except (UnicodeError, ValueError) as exc:
                transition_document(document, REJECTED, error="Document illisible ou corrompu.")
                db.commit()
                raise NonRetryableProcessingError("Document content is permanently invalid") from exc
        for position, chunk in enumerate(chunks):
            chunk.metadata.update({
                "workspace_id": document.workspace_id,
                "document_id": document.id,
                "document_name": document.display_name,
                "document_version": document.version,
                "content_hash": document.content_hash or "legacy",
                "chunk_position": position,
            })
        # Replacing the version-specific vector set makes retry deterministic.
        selected_store.delete(where={"document_id": document.id})
        if chunks:
            selected_store.add_documents(chunks, ids=_chunk_ids(document, chunks))
        transition_document(document, INDEXED)
        document.chunk_count = len(chunks)
        document.indexed_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(document)
        return document
    except NonRetryableProcessingError:
        raise
    except Exception as exc:
        db.rollback()
        durable = db.get(WorkspaceDocument, document.id)
        if durable and canonical_status(durable.status) == PROCESSING:
            transition_document(
                durable,
                PROCESSING_FAILED,
                error="Indexation impossible. Une nouvelle tentative est possible.",
            )
            db.commit()
        raise RuntimeError("Document processing failed") from exc
