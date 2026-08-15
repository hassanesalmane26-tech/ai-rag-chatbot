import os
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.database.genesis_models import WorkspaceDocument, new_id
from app.rag.loader import load_document
from app.rag.splitter import split_documents
from app.rag.vectorstore import vectorstore

DOCUMENTS_ROOT = Path("documents/workspaces")
ALLOWED_SUFFIXES = {".pdf", ".txt", ".docx"}
MAX_UPLOAD_BYTES = 20 * 1024 * 1024


def _safe_display_name(filename: str | None) -> str:
    candidate = Path(filename or "document").name.strip()
    candidate = re.sub(r"[^\w. ()-]", "_", candidate, flags=re.UNICODE)
    if not candidate or Path(candidate).suffix.lower() not in ALLOWED_SUFFIXES:
        raise HTTPException(status_code=415, detail="Format de document non pris en charge.")
    return candidate[:200]


async def create_document(db: Session, workspace_id: str, upload: UploadFile) -> WorkspaceDocument:
    display_name = _safe_display_name(upload.filename)
    content = await upload.read(MAX_UPLOAD_BYTES + 1)
    if not content:
        raise HTTPException(status_code=422, detail="Le document est vide.")
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Le document dépasse la limite de 20 Mo.")

    document = WorkspaceDocument(
        workspace_id=workspace_id,
        display_name=display_name,
        storage_name=f"{new_id()}{Path(display_name).suffix.lower()}",
        media_type=upload.content_type or "application/octet-stream",
        size_bytes=len(content),
        status="processing",
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    destination = DOCUMENTS_ROOT / workspace_id / document.storage_name
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        destination.write_bytes(content)
        chunks = split_documents(load_document(str(destination)))
        for chunk in chunks:
            chunk.metadata.update(
                {
                    "workspace_id": workspace_id,
                    "document_id": document.id,
                    "document_name": document.display_name,
                }
            )
        if chunks:
            vectorstore.add_documents(chunks)
        document.status = "indexed"
        document.indexed_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(document)
        return document
    except Exception as exc:
        destination.unlink(missing_ok=True)
        document.status = "failed"
        document.error_message = "Indexation impossible."
        db.commit()
        raise HTTPException(status_code=422, detail="Le document n’a pas pu être indexé.") from exc


def delete_document(db: Session, document: WorkspaceDocument) -> None:
    try:
        vectorstore.delete(where={"document_id": document.id})
    except Exception:
        # Vector content is derived; a later reconciliation can remove leftovers.
        pass
    path = DOCUMENTS_ROOT / document.workspace_id / document.storage_name
    path.unlink(missing_ok=True)
    db.delete(document)
    db.commit()


def serialize_document(document: WorkspaceDocument) -> dict:
    return {
        "id": document.id,
        "workspace_id": document.workspace_id,
        "display_name": document.display_name,
        "media_type": document.media_type,
        "size_bytes": document.size_bytes,
        "status": document.status,
        "error_message": document.error_message,
        "created_at": document.created_at.isoformat() if document.created_at else None,
        "indexed_at": document.indexed_at.isoformat() if document.indexed_at else None,
    }
