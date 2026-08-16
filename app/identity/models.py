"""Internal users and provider-neutral external identity mappings."""

import uuid

from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.sql import func

from app.database.database import Base


def new_identity_id() -> str:
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=new_identity_id)
    display_name = Column(String(160), nullable=True)
    status = Column(String(24), nullable=False, default="active")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        CheckConstraint("status IN ('active', 'disabled')", name="ck_users_status"),
    )


class ExternalIdentity(Base):
    __tablename__ = "external_identities"

    id = Column(String(36), primary_key=True, default=new_identity_id)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    issuer = Column(String(512), nullable=False)
    subject = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_seen_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("issuer", "subject", name="uq_external_identities_issuer_subject"),
    )
