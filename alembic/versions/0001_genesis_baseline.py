"""Adopt the existing non-destructive TRIDENT GENESIS schema."""

from alembic import op
import sqlalchemy as sa

revision = "0001_genesis_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("chat_messages", sa.Column("id", sa.Integer(), autoincrement=True, nullable=False), sa.Column("user_message", sa.Text(), nullable=False), sa.Column("ai_response", sa.Text(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True), sa.PrimaryKeyConstraint("id"))
    op.create_index("ix_chat_messages_id", "chat_messages", ["id"], unique=False)
    op.create_table("workspaces", sa.Column("id", sa.String(length=36), nullable=False), sa.Column("name", sa.String(length=120), nullable=False), sa.Column("description", sa.Text(), nullable=True), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False), sa.PrimaryKeyConstraint("id"))
    op.create_table("conversations", sa.Column("id", sa.String(length=36), nullable=False), sa.Column("workspace_id", sa.String(length=36), nullable=False), sa.Column("title", sa.String(length=160), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False), sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]), sa.PrimaryKeyConstraint("id"))
    op.create_index("ix_conversations_workspace_id", "conversations", ["workspace_id"], unique=False)
    op.create_table("workspace_documents", sa.Column("id", sa.String(length=36), nullable=False), sa.Column("workspace_id", sa.String(length=36), nullable=False), sa.Column("display_name", sa.String(length=255), nullable=False), sa.Column("storage_name", sa.String(length=255), nullable=False), sa.Column("media_type", sa.String(length=120), nullable=False), sa.Column("size_bytes", sa.Integer(), nullable=False), sa.Column("status", sa.String(length=24), nullable=False), sa.Column("error_message", sa.Text(), nullable=True), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False), sa.Column("indexed_at", sa.DateTime(timezone=True), nullable=True), sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]), sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("storage_name", name="workspace_documents_storage_name_key"))
    op.create_index("ix_workspace_documents_workspace_id", "workspace_documents", ["workspace_id"], unique=False)
    op.create_table("workspace_messages", sa.Column("id", sa.String(length=36), nullable=False), sa.Column("conversation_id", sa.String(length=36), nullable=False), sa.Column("role", sa.String(length=16), nullable=False), sa.Column("content", sa.Text(), nullable=False), sa.Column("citations_json", sa.Text(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False), sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"]), sa.PrimaryKeyConstraint("id"))
    op.create_index("ix_workspace_messages_conversation_id", "workspace_messages", ["conversation_id"], unique=False)


def downgrade() -> None:
    raise RuntimeError("The GENESIS baseline is non-downgradable because dropping it would destroy existing data.")
