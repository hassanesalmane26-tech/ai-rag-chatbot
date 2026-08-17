"""Durable job contract usable inline today and by external workers later."""

from datetime import datetime, timedelta, timezone
from sqlalchemy import or_
from sqlalchemy.orm import Session
from app.knowledge.models import KnowledgeJob


def enqueue_ingestion(db: Session, organization_id: str, workspace_id: str, document_id: str, version: int) -> KnowledgeJob:
    key = f"ingest:{document_id}:v{version}"
    existing = db.query(KnowledgeJob).filter_by(idempotency_key=key).first()
    if existing: return existing
    job = KnowledgeJob(organization_id=organization_id, workspace_id=workspace_id,
                       document_id=document_id, operation="ingest", idempotency_key=key)
    db.add(job); db.flush(); return job


def claim_job(db: Session, job_id: str, worker_id: str, lease_seconds: int = 300) -> KnowledgeJob | None:
    now = datetime.now(timezone.utc)
    job = db.query(KnowledgeJob).filter_by(id=job_id).with_for_update().first()
    if not job or job.status == "succeeded" or job.attempts >= job.max_attempts: return None
    available = job.available_at
    if available and available.tzinfo is None: available = available.replace(tzinfo=timezone.utc)
    if available and available > now: return None
    lease = job.lease_expires_at
    if lease and lease.tzinfo is None: lease = lease.replace(tzinfo=timezone.utc)
    if job.status == "running" and lease and lease > now: return None
    job.status="running"; job.worker_id=worker_id; job.attempts += 1
    job.lease_expires_at=now + timedelta(seconds=lease_seconds); job.error_message=None
    db.commit(); db.refresh(job); return job


def claim_next_job(db: Session, worker_id: str, lease_seconds: int = 300) -> KnowledgeJob | None:
    """Claim one available job; expired leases are recoverable after interruption."""
    now = datetime.now(timezone.utc)
    candidate = (
        db.query(KnowledgeJob.id)
        .filter(KnowledgeJob.attempts < KnowledgeJob.max_attempts)
        .filter(KnowledgeJob.available_at <= now)
        .filter(
            or_(
                KnowledgeJob.status == "queued",
                (KnowledgeJob.status == "running")
                & (KnowledgeJob.lease_expires_at <= now),
            )
        )
        .order_by(KnowledgeJob.available_at, KnowledgeJob.created_at)
        .first()
    )
    return claim_job(db, candidate[0], worker_id, lease_seconds) if candidate else None


def finish_job(db: Session, job: KnowledgeJob) -> None:
    job.status="succeeded"; job.completed_at=datetime.now(timezone.utc); job.lease_expires_at=None
    db.commit()


def fail_job(db: Session, job: KnowledgeJob, message: str) -> None:
    job.status="failed" if job.attempts >= job.max_attempts else "queued"
    job.error_message=message[:1000]; job.lease_expires_at=None
    job.available_at=datetime.now(timezone.utc) + timedelta(seconds=min(300, 2 ** job.attempts))
    db.commit()
