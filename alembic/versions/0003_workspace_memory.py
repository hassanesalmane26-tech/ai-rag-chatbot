"""Add explicit Workspace-scoped GENESIS memory."""

from alembic import op
import sqlalchemy as sa

revision = "0003_workspace_memory"
down_revision = "0002_durable_document_ingestion"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "workspace_memories",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("workspace_id", sa.String(length=36), nullable=False),
        sa.Column("conversation_id", sa.String(length=36), nullable=True),
        sa.Column("kind", sa.String(length=24), server_default="note", nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"]),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_workspace_memories_workspace_id", "workspace_memories", ["workspace_id"]
    )
    op.create_index(
        "ix_workspace_memories_conversation_id",
        "workspace_memories",
        ["conversation_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_workspace_memories_conversation_id", table_name="workspace_memories")
    op.drop_index("ix_workspace_memories_workspace_id", table_name="workspace_memories")
    op.drop_table("workspace_memories")
