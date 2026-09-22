"""One durable record is both the task and its eventual image artifact."""
from sqlalchemy import Column, String, Text, DateTime, Integer, ForeignKey, UniqueConstraint, CheckConstraint
from sqlalchemy.sql import func
from app.database.database import Base
from app.database.genesis_models import new_id


class ImageArtifact(Base):
    __tablename__ = "workspace_image_artifacts"
    id = Column(String(36), primary_key=True, default=new_id)
    workspace_id = Column(String(36), ForeignKey("workspaces.id"), nullable=False, index=True)
    conversation_id = Column(String(36), ForeignKey("conversations.id"), nullable=False, index=True)
    message_id = Column(String(36), ForeignKey("workspace_messages.id"), nullable=False, unique=True)
    user_message_id = Column(String(36), ForeignKey("workspace_messages.id"), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    request_key = Column(String(64), nullable=False)
    request_hash = Column(String(64), nullable=False)
    prompt = Column(Text, nullable=False)
    aspect_ratio = Column(String(8), nullable=False)
    source_id = Column(String(36), ForeignKey("workspace_image_artifacts.id"), nullable=True)
    source_key = Column(String(512), nullable=True)
    output_key = Column(String(512), nullable=True)
    status = Column(String(16), nullable=False, default="queued", index=True)
    attempts = Column(Integer, nullable=False, default=0)
    error_code = Column(String(40), nullable=True)
    provider = Column(String(40), nullable=True)
    model = Column(String(120), nullable=True)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    __table_args__ = (
        UniqueConstraint("conversation_id", "request_key", name="uq_image_conversation_request"),
        CheckConstraint("status IN ('queued','generating','completed','failed','cancelled')", name="ck_image_status"),
        CheckConstraint("aspect_ratio IN ('1:1','3:2','2:3')", name="ck_image_aspect"),
    )
