"""Durable, opaque application sessions and one-time OIDC login transactions."""

import uuid

from sqlalchemy import Column, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.sql import func

from app.database.database import Base


def new_session_id() -> str:
    return str(uuid.uuid4())


class OIDCLoginTransaction(Base):
    __tablename__ = "oidc_login_transactions"

    id = Column(String(36), primary_key=True, default=new_session_id)
    state_hash = Column(String(64), nullable=False, unique=True, index=True)
    nonce = Column(String(128), nullable=False)
    code_verifier = Column(String(128), nullable=False)
    return_to = Column(String(512), nullable=False, default="/")
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    used_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (UniqueConstraint("state_hash", name="uq_oidc_login_state_hash"),)


class ApplicationSession(Base):
    __tablename__ = "application_sessions"

    id = Column(String(36), primary_key=True, default=new_session_id)
    token_hash = Column(String(64), nullable=False, unique=True, index=True)
    csrf_hash = Column(String(64), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    active_organization_id = Column(
        String(36), ForeignKey("organizations.id"), nullable=True, index=True
    )
    active_workspace_id = Column(
        String(36), ForeignKey("workspaces.id"), nullable=True, index=True
    )
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    last_seen_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (UniqueConstraint("token_hash", name="uq_application_session_token_hash"),)
