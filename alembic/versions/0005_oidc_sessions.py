"""Add one-time OIDC transactions and opaque application sessions."""

from alembic import op
import sqlalchemy as sa

revision = "0005_oidc_sessions"
down_revision = "0004_identity_tenancy"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "oidc_login_transactions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("state_hash", sa.String(length=64), nullable=False),
        sa.Column("nonce", sa.String(length=128), nullable=False),
        sa.Column("code_verifier", sa.String(length=128), nullable=False),
        sa.Column("return_to", sa.String(length=512), server_default="/", nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("state_hash"),
    )
    op.create_index(
        "ix_oidc_login_transactions_state_hash", "oidc_login_transactions", ["state_hash"],
        unique=True,
    )
    op.create_index(
        "ix_oidc_login_transactions_expires_at", "oidc_login_transactions", ["expires_at"]
    )
    op.create_table(
        "application_sessions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("csrf_hash", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("active_organization_id", sa.String(length=36), nullable=True),
        sa.Column("active_workspace_id", sa.String(length=36), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["active_organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["active_workspace_id"], ["workspaces.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    for column in ("token_hash", "user_id", "active_organization_id", "active_workspace_id", "expires_at"):
        op.create_index(f"ix_application_sessions_{column}", "application_sessions", [column], unique=column == "token_hash")


def downgrade() -> None:
    raise RuntimeError(
        "AI-3 session persistence is non-downgradable: expire/revoke sessions and restore "
        "a verified pre-migration backup instead of dropping security state."
    )
