"""Read-only consistency audit for authoritative and derived Knowledge state."""

import hashlib
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import settings
from app.database.genesis_models import Workspace, WorkspaceDocument
from app.knowledge.storage import storage_for_backend
from app.knowledge.jobs import enqueue_ingestion, requeue_ingestion
from app.knowledge.state import (
    INDEXED,
    PROCESSING_FAILED,
    SCAN_FAILED,
    SCANNING,
    PROCESSING,
    canonical_status,
    transition_document,
)
from app.rag.vectorstore import vectorstore


@dataclass(frozen=True)
class ReconciliationIssue:
    kind: str
    document_id: str | None


@dataclass(frozen=True)
class ReconciliationReport:
    workspace_id: str
    database_documents: int
    stored_originals: int
    vector_chunks: int
    issues: tuple[ReconciliationIssue, ...]

    @property
    def consistent(self) -> bool:
        return not self.issues


@dataclass(frozen=True)
class ReconciliationAction:
    document_id: str
    previous_status: str
    status: str
    requeued: bool


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def audit_workspace_knowledge(
    db: Session,
    workspace_id: str,
    *,
    store=None,
    documents_root: Path | None = None,
) -> ReconciliationReport:
    """Report drift without modifying PostgreSQL, originals, or vector data."""
    selected_store = store or vectorstore
    root = documents_root or settings.documents_path
    documents = db.query(WorkspaceDocument).filter_by(workspace_id=workspace_id).all()
    document_ids = {document.id for document in documents}
    issues: list[ReconciliationIssue] = []
    stored_originals = 0

    for document in documents:
        storage = storage_for_backend(document.storage_backend, local_root=root)
        key = document.storage_key or f"{workspace_id}/{document.storage_name}"
        if not storage.exists(key):
            issues.append(ReconciliationIssue("missing_original", document.id))
            continue
        stored_originals += 1
        if document.content_hash:
            with storage.materialize(key) as original:
                if _sha256(original) != document.content_hash:
                    issues.append(ReconciliationIssue("checksum_mismatch", document.id))

    workspace_directory = root / workspace_id
    if workspace_directory.is_dir():
        known_names = {document.storage_name for document in documents}
        for original in workspace_directory.iterdir():
            if original.is_file() and original.name not in known_names:
                issues.append(ReconciliationIssue("orphan_original", None))

    vector_data = selected_store.get(
        where={"workspace_id": workspace_id}, include=["metadatas"]
    )
    metadatas = vector_data.get("metadatas") or []
    vector_document_ids = {
        metadata.get("document_id") for metadata in metadatas if metadata
    }
    for document in documents:
        if document.status == "indexed" and document.id not in vector_document_ids:
            issues.append(ReconciliationIssue("missing_vectors", document.id))
    for document_id in vector_document_ids - document_ids:
        issues.append(ReconciliationIssue("orphan_vectors", document_id))

    return ReconciliationReport(
        workspace_id=workspace_id,
        database_documents=len(documents),
        stored_originals=stored_originals,
        vector_chunks=len(metadatas),
        issues=tuple(issues),
    )


def reconcile_stuck_documents(
    db: Session,
    workspace_id: str,
    *,
    stale_after: timedelta = timedelta(minutes=15),
    now: datetime | None = None,
    store=None,
    documents_root: Path | None = None,
) -> tuple[ReconciliationAction, ...]:
    """Recover interrupted scan/index states without any scheduler coupling."""
    current_time = now or datetime.now(timezone.utc)
    cutoff = current_time - stale_after
    root = documents_root or settings.documents_path
    selected_store = store or vectorstore
    documents = (
        db.query(WorkspaceDocument)
        .filter(WorkspaceDocument.workspace_id == workspace_id)
        .filter(WorkspaceDocument.status.in_((SCANNING, PROCESSING)))
        .filter(WorkspaceDocument.updated_at < cutoff)
        .all()
    )
    actions = []
    for document in documents:
        previous = canonical_status(document.status)
        failed = SCAN_FAILED if previous == SCANNING else PROCESSING_FAILED
        transition_document(document, failed, error="Traitement interrompu; reprise requise.")
        workspace = db.get(Workspace, document.workspace_id)
        job = enqueue_ingestion(
            db, workspace.organization_id, document.workspace_id, document.id, document.version
        )
        requeued = job.attempts < job.max_attempts
        if requeued:
            requeue_ingestion(db, job)
        actions.append(ReconciliationAction(document.id, previous, failed, requeued))

    indexed = db.query(WorkspaceDocument).filter_by(workspace_id=workspace_id, status=INDEXED).all()
    vector_data = selected_store.get(where={"workspace_id": workspace_id}, include=["metadatas"])
    vector_ids = {
        metadata.get("document_id")
        for metadata in (vector_data.get("metadatas") or [])
        if metadata and metadata.get("document_id")
    }
    for document in indexed:
        storage = storage_for_backend(document.storage_backend, local_root=root)
        key = document.storage_key or f"{workspace_id}/{document.storage_name}"
        original_exists = storage.exists(key)
        vectors_exist = document.id in vector_ids
        if original_exists and vectors_exist:
            continue
        transition_document(
            document,
            PROCESSING_FAILED,
            error=("Original introuvable; restauration requise." if not original_exists else "Index dérivé manquant; reprise requise."),
        )
        requeued = False
        if original_exists:
            workspace = db.get(Workspace, document.workspace_id)
            job = enqueue_ingestion(
                db, workspace.organization_id, document.workspace_id, document.id, document.version
            )
            requeued = job.attempts < job.max_attempts
            if requeued:
                requeue_ingestion(db, job)
        actions.append(ReconciliationAction(document.id, INDEXED, PROCESSING_FAILED, requeued))
    db.commit()
    return tuple(actions)
