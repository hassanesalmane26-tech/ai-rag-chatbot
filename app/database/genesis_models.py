"""Persistent Genesis resources.

These records intentionally use opaque UUIDs so the same ownership model can be
extended with organizations and members in TRIDENT AI without changing public IDs.
"""

import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func

from app.database.database import Base


def new_id() -> str:
    return str(uuid.uuid4())


class Workspace(Base):
    __tablename__ = "workspaces"

    id = Column(String(36), primary_key=True, default=new_id)
    name = Column(String(120), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(String(36), primary_key=True, default=new_id)
    workspace_id = Column(String(36), ForeignKey("workspaces.id"), nullable=False, index=True)
    title = Column(String(160), nullable=False, default="Nouvelle conversation")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class WorkspaceMessage(Base):
    __tablename__ = "workspace_messages"

    id = Column(String(36), primary_key=True, default=new_id)
    conversation_id = Column(
        String(36), ForeignKey("conversations.id"), nullable=False, index=True
    )
    role = Column(String(16), nullable=False)
    content = Column(Text, nullable=False)
    citations_json = Column(Text, nullable=False, default="[]")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class WorkspaceDocument(Base):
    __tablename__ = "workspace_documents"

    id = Column(String(36), primary_key=True, default=new_id)
    workspace_id = Column(String(36), ForeignKey("workspaces.id"), nullable=False, index=True)
    display_name = Column(String(255), nullable=False)
    storage_name = Column(String(255), nullable=False, unique=True)
    media_type = Column(String(120), nullable=False)
    size_bytes = Column(Integer, nullable=False)
    status = Column(String(24), nullable=False, default="pending")
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    indexed_at = Column(DateTime(timezone=True), nullable=True)
