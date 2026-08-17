"""Add provider-neutral object metadata and durable Knowledge jobs."""

from alembic import op
import sqlalchemy as sa

revision = "0008_durable_knowledge_jobs"
down_revision = "0007_audit_truncate_guard"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("workspace_documents", sa.Column("storage_backend", sa.String(32), server_default="local", nullable=False))
    op.add_column("workspace_documents", sa.Column("storage_key", sa.String(512), nullable=True))
    op.add_column("workspace_documents", sa.Column("original_etag", sa.String(128), nullable=True))
    documents = sa.table(
        "workspace_documents",
        sa.column("workspace_id", sa.String()),
        sa.column("storage_name", sa.String()),
        sa.column("storage_key", sa.String()),
        sa.column("original_etag", sa.String()),
        sa.column("content_hash", sa.String()),
    )
    op.execute(
        documents.update()
        .where(documents.c.storage_key.is_(None))
        .values(
            storage_key=documents.c.workspace_id + sa.literal("/") + documents.c.storage_name,
            original_etag=documents.c.content_hash,
        )
    )
    op.create_table(
        "knowledge_jobs",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("workspace_id", sa.String(36), nullable=False),
        sa.Column("document_id", sa.String(36), nullable=False),
        sa.Column("operation", sa.String(16), nullable=False),
        sa.Column("idempotency_key", sa.String(160), nullable=False),
        sa.Column("status", sa.String(16), server_default="queued", nullable=False),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("max_attempts", sa.Integer(), server_default="5", nullable=False),
        sa.Column("available_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("worker_id", sa.String(128), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("operation IN ('ingest', 'delete')", name="ck_knowledge_jobs_operation"),
        sa.CheckConstraint("status IN ('queued', 'running', 'succeeded', 'failed')", name="ck_knowledge_jobs_status"),
        sa.CheckConstraint("attempts >= 0 AND max_attempts > 0", name="ck_knowledge_jobs_attempts"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.ForeignKeyConstraint(["document_id"], ["workspace_documents.id"]),
        sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("idempotency_key"),
    )
    for column in ("organization_id", "workspace_id", "document_id", "status", "available_at"):
        op.create_index(f"ix_knowledge_jobs_{column}", "knowledge_jobs", [column])
    op.create_index("ix_knowledge_jobs_claim", "knowledge_jobs", ["status", "available_at", "lease_expires_at"])


def downgrade() -> None:
    raise RuntimeError("AI-5 durable Knowledge state is non-downgradable.")
