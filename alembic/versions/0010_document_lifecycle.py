"""Formalize the asynchronous, scan-gated document lifecycle."""

from alembic import op
import sqlalchemy as sa


revision = "0010_document_lifecycle"
down_revision = "0009_audit_guard_reconciliation"
branch_labels = None
depends_on = None


STATUSES = (
    "uploaded", "pending_scan", "scanning", "scan_failed", "rejected",
    "pending_processing", "processing", "indexed", "processing_failed",
    "deleting", "delete_failed",
)


def upgrade() -> None:
    documents = sa.table("workspace_documents", sa.column("status", sa.String()))
    op.execute(documents.update().where(documents.c.status == "pending").values(status="pending_scan"))
    op.execute(documents.update().where(documents.c.status == "failed").values(status="processing_failed"))
    allowed = ",".join(f"'{status}'" for status in STATUSES)
    with op.batch_alter_table("workspace_documents") as batch:
        batch.create_check_constraint("ck_workspace_documents_status", f"status IN ({allowed})")


def downgrade() -> None:
    raise RuntimeError("The scan-gated document lifecycle is non-downgradable.")
