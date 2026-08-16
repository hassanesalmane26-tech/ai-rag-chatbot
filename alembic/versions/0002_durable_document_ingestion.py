"""Add recoverable and idempotent document ingestion metadata."""

from alembic import op
import sqlalchemy as sa

revision = "0002_durable_document_ingestion"
down_revision = "0001_genesis_baseline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("workspace_documents", sa.Column("content_hash", sa.String(length=64), nullable=True))
    op.add_column(
        "workspace_documents",
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
    )
    op.add_column(
        "workspace_documents",
        sa.Column("ingestion_attempts", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "workspace_documents",
        sa.Column("chunk_count", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "workspace_documents",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    op.create_index(
        "uq_workspace_documents_workspace_content_hash",
        "workspace_documents",
        ["workspace_id", "content_hash"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "uq_workspace_documents_workspace_content_hash",
        table_name="workspace_documents",
    )
    op.drop_column("workspace_documents", "updated_at")
    op.drop_column("workspace_documents", "chunk_count")
    op.drop_column("workspace_documents", "ingestion_attempts")
    op.drop_column("workspace_documents", "version")
    op.drop_column("workspace_documents", "content_hash")
