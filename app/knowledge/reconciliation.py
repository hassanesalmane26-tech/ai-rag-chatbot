"""Read-only consistency audit for authoritative and derived Knowledge state."""

import hashlib
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import settings
from app.database.genesis_models import WorkspaceDocument
from app.knowledge.storage import LocalObjectStorage
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
    storage = LocalObjectStorage(root)
    documents = db.query(WorkspaceDocument).filter_by(workspace_id=workspace_id).all()
    document_ids = {document.id for document in documents}
    issues: list[ReconciliationIssue] = []
    stored_originals = 0

    for document in documents:
        original = storage.path(document.storage_key or f"{workspace_id}/{document.storage_name}")
        if not original.is_file():
            issues.append(ReconciliationIssue("missing_original", document.id))
            continue
        stored_originals += 1
        if document.content_hash and _sha256(original) != document.content_hash:
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
