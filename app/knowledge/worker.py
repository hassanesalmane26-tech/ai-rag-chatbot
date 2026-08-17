"""Small durable Knowledge worker entrypoint for the Genesis modular monolith."""

import argparse
import logging
import os
import socket
import time

from app.database.database import SessionLocal
from app.database.genesis_models import WorkspaceDocument
from app.knowledge.jobs import claim_next_job, fail_job, finish_job
from app.knowledge.service import ingest_document

logger = logging.getLogger("trident.knowledge.worker")


def process_one(worker_id: str) -> bool:
    """Process at most one leased job and return whether work was claimed."""
    db = SessionLocal()
    try:
        job = claim_next_job(db, worker_id)
        if job is None:
            return False
        document = db.get(WorkspaceDocument, job.document_id)
        if document is None:
            fail_job(db, job, "Document no longer exists")
            return True
        try:
            if job.operation == "ingest":
                ingest_document(db, document)
            else:
                raise RuntimeError(f"Unsupported durable operation: {job.operation}")
            finish_job(db, job)
        except Exception as exc:
            logger.warning(
                "knowledge_job_failed",
                extra={"event_name": "knowledge_job_failed", "job_id": job.id},
            )
            fail_job(db, job, type(exc).__name__)
        return True
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="TRIDENT durable Knowledge worker")
    parser.add_argument("--once", action="store_true", help="process at most one job")
    parser.add_argument("--poll-seconds", type=float, default=2.0)
    args = parser.parse_args()
    worker_id = f"{socket.gethostname()}:{os.getpid()}"
    while True:
        processed = process_one(worker_id)
        if args.once:
            return
        if not processed:
            time.sleep(max(0.2, args.poll_seconds))


if __name__ == "__main__":
    main()
