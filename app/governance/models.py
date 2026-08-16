"""Additive governance persistence owned by the Organization boundary."""

import uuid

from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.sql import func

from app.database.database import Base


def new_id() -> str:
    return str(uuid.uuid4())


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id = Column(String(36), primary_key=True, default=new_id)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=True, index=True)
    workspace_id = Column(String(36), ForeignKey("workspaces.id"), nullable=True, index=True)
    actor_user_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)
    action = Column(String(96), nullable=False, index=True)
    resource_type = Column(String(64), nullable=False)
    resource_id = Column(String(128), nullable=True)
    outcome = Column(String(16), nullable=False, default="success")
    request_id = Column(String(128), nullable=True)
    metadata_json = Column(Text, nullable=False, default="{}")
    previous_hash = Column(String(64), nullable=False)
    event_hash = Column(String(64), nullable=False, unique=True)
    created_at = Column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        CheckConstraint("outcome IN ('success', 'denied', 'failure')", name="ck_audit_events_outcome"),
        Index("ix_audit_events_org_created", "organization_id", "created_at", "id"),
    )


class EntitlementGrant(Base):
    __tablename__ = "entitlement_grants"

    id = Column(String(36), primary_key=True, default=new_id)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)
    key = Column(String(96), nullable=False)
    integer_value = Column(Integer, nullable=True)
    source = Column(String(32), nullable=False, default="manual")
    issued_by_user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint(
            "(organization_id IS NOT NULL AND user_id IS NULL) OR "
            "(organization_id IS NULL AND user_id IS NOT NULL)",
            name="ck_entitlement_grants_single_subject",
        ),
        CheckConstraint("source IN ('plan', 'founder', 'manual')", name="ck_entitlement_grants_source"),
        Index(
            "uq_entitlement_organization_key", "organization_id", "key", unique=True,
            postgresql_where=text("organization_id IS NOT NULL"),
            sqlite_where=text("organization_id IS NOT NULL"),
        ),
        Index(
            "uq_entitlement_user_key", "user_id", "key", unique=True,
            postgresql_where=text("user_id IS NOT NULL"),
            sqlite_where=text("user_id IS NOT NULL"),
        ),
    )


class QuotaCounter(Base):
    __tablename__ = "quota_counters"

    id = Column(String(36), primary_key=True, default=new_id)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    metric = Column(String(64), nullable=False)
    window_start = Column(DateTime(timezone=True), nullable=False)
    used = Column(Integer, nullable=False, default=0)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("used >= 0", name="ck_quota_counters_used"),
        UniqueConstraint("organization_id", "metric", "window_start", name="uq_quota_counter_window"),
    )
