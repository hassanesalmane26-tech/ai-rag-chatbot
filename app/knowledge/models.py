"""Durable, retryable Knowledge jobs."""

import uuid
from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.sql import func
from app.database.database import Base


class KnowledgeJob(Base):
    __tablename__ = "knowledge_jobs"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    workspace_id = Column(String(36), ForeignKey("workspaces.id"), nullable=False, index=True)
    document_id = Column(String(36), ForeignKey("workspace_documents.id"), nullable=False, index=True)
    operation = Column(String(16), nullable=False)
    idempotency_key = Column(String(160), nullable=False, unique=True)
    status = Column(String(16), nullable=False, default="queued", index=True)
    attempts = Column(Integer, nullable=False, default=0)
    max_attempts = Column(Integer, nullable=False, default=5)
    available_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    lease_expires_at = Column(DateTime(timezone=True), nullable=True)
    worker_id = Column(String(128), nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    __table_args__ = (
        CheckConstraint("operation IN ('ingest', 'delete')", name="ck_knowledge_jobs_operation"),
        CheckConstraint("status IN ('queued', 'running', 'succeeded', 'failed')", name="ck_knowledge_jobs_status"),
        CheckConstraint("attempts >= 0 AND max_attempts > 0", name="ck_knowledge_jobs_attempts"),
        Index("ix_knowledge_jobs_claim", "status", "available_at", "lease_expires_at"),
    )
