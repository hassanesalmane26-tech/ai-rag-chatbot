"""Add immutable audit, entitlement grants and durable quota counters."""

from alembic import op
import sqlalchemy as sa

revision = "0006_governance_controls"
down_revision = "0005_oidc_sessions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "audit_events",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("organization_id", sa.String(36), nullable=True),
        sa.Column("workspace_id", sa.String(36), nullable=True),
        sa.Column("actor_user_id", sa.String(36), nullable=True),
        sa.Column("action", sa.String(96), nullable=False),
        sa.Column("resource_type", sa.String(64), nullable=False),
        sa.Column("resource_id", sa.String(128), nullable=True),
        sa.Column("outcome", sa.String(16), nullable=False),
        sa.Column("request_id", sa.String(128), nullable=True),
        sa.Column("metadata_json", sa.Text(), nullable=False),
        sa.Column("previous_hash", sa.String(64), nullable=False),
        sa.Column("event_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("outcome IN ('success', 'denied', 'failure')", name="ck_audit_events_outcome"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("event_hash"),
    )
    for column in ("organization_id", "workspace_id", "actor_user_id", "action"):
        op.create_index(f"ix_audit_events_{column}", "audit_events", [column])
    op.create_index("ix_audit_events_org_created", "audit_events", ["organization_id", "created_at", "id"])

    op.create_table(
        "entitlement_grants",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("organization_id", sa.String(36), nullable=True),
        sa.Column("user_id", sa.String(36), nullable=True),
        sa.Column("key", sa.String(96), nullable=False),
        sa.Column("integer_value", sa.Integer(), nullable=True),
        sa.Column("source", sa.String(32), server_default="manual", nullable=False),
        sa.Column("issued_by_user_id", sa.String(36), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint("(organization_id IS NOT NULL AND user_id IS NULL) OR (organization_id IS NULL AND user_id IS NOT NULL)", name="ck_entitlement_grants_single_subject"),
        sa.CheckConstraint("source IN ('plan', 'founder', 'manual')", name="ck_entitlement_grants_source"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["issued_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_entitlement_grants_organization_id", "entitlement_grants", ["organization_id"])
    op.create_index("ix_entitlement_grants_user_id", "entitlement_grants", ["user_id"])
    op.create_index("uq_entitlement_organization_key", "entitlement_grants", ["organization_id", "key"], unique=True, postgresql_where=sa.text("organization_id IS NOT NULL"), sqlite_where=sa.text("organization_id IS NOT NULL"))
    op.create_index("uq_entitlement_user_key", "entitlement_grants", ["user_id", "key"], unique=True, postgresql_where=sa.text("user_id IS NOT NULL"), sqlite_where=sa.text("user_id IS NOT NULL"))

    op.create_table(
        "quota_counters",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("metric", sa.String(64), nullable=False),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint("used >= 0", name="ck_quota_counters_used"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "metric", "window_start", name="uq_quota_counter_window"),
    )
    op.create_index("ix_quota_counters_organization_id", "quota_counters", ["organization_id"])

    dialect = op.get_bind().dialect.name
    if dialect == "postgresql":
        op.execute("""
        CREATE FUNCTION trident_reject_audit_mutation() RETURNS trigger AS $$
        BEGIN RAISE EXCEPTION 'audit_events is append-only'; END; $$ LANGUAGE plpgsql;
        CREATE TRIGGER trident_audit_events_immutable BEFORE UPDATE OR DELETE ON audit_events
        FOR EACH ROW EXECUTE FUNCTION trident_reject_audit_mutation();
        """)
    elif dialect == "sqlite":
        op.execute("CREATE TRIGGER trident_audit_events_no_update BEFORE UPDATE ON audit_events BEGIN SELECT RAISE(ABORT, 'audit_events is append-only'); END")
        op.execute("CREATE TRIGGER trident_audit_events_no_delete BEFORE DELETE ON audit_events BEGIN SELECT RAISE(ABORT, 'audit_events is append-only'); END")


def downgrade() -> None:
    raise RuntimeError("AI-4 governance records are non-downgradable; never drop audit history.")
