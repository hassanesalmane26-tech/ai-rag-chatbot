"""Add isolated image tasks/artifacts; no changes to existing product rows."""
from alembic import context, op
import sqlalchemy as sa

revision = "0011_workspace_images"
down_revision = "0010_document_lifecycle"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("workspace_image_artifacts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("workspace_id", sa.String(36), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("conversation_id", sa.String(36), sa.ForeignKey("conversations.id"), nullable=False),
        sa.Column("message_id", sa.String(36), sa.ForeignKey("workspace_messages.id"), nullable=False, unique=True),
        sa.Column("user_message_id", sa.String(36), sa.ForeignKey("workspace_messages.id"), nullable=False),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("request_key", sa.String(64), nullable=False), sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("prompt", sa.Text, nullable=False), sa.Column("aspect_ratio", sa.String(8), nullable=False),
        sa.Column("source_id", sa.String(36), sa.ForeignKey("workspace_image_artifacts.id")),
        sa.Column("source_key", sa.String(512)), sa.Column("output_key", sa.String(512)),
        sa.Column("status", sa.String(16), nullable=False), sa.Column("attempts", sa.Integer, nullable=False),
        sa.Column("error_code", sa.String(40)), sa.Column("provider", sa.String(40)), sa.Column("model", sa.String(120)),
        sa.Column("width", sa.Integer), sa.Column("height", sa.Integer),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("conversation_id", "request_key", name="uq_image_conversation_request"),
        sa.CheckConstraint("status IN ('queued','generating','completed','failed','cancelled')", name="ck_image_status"),
        sa.CheckConstraint("aspect_ratio IN ('1:1','3:2','2:3')", name="ck_image_aspect"),
    )
    for column in ("workspace_id", "conversation_id", "status"):
        op.create_index(f"ix_workspace_image_artifacts_{column}", "workspace_image_artifacts", [column])


def downgrade():
    # Generic downgrade must not partially unwind the protected migration chain.
    # The release operator may reverse ONLY this empty table before activation.
    if context.get_x_argument(as_dictionary=True).get("allow_empty_image_downgrade") != "yes":
        raise RuntimeError("Image persistence is non-downgradable without the explicit empty-table release gate")
    if op.get_bind().execute(sa.text("SELECT COUNT(*) FROM workspace_image_artifacts")).scalar():
        raise RuntimeError("Image artifacts exist: destructive downgrade refused")
    op.drop_table("workspace_image_artifacts")
