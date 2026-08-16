"""Prevent PostgreSQL TRUNCATE from bypassing immutable audit history."""

from alembic import op

revision = "0007_audit_truncate_guard"
down_revision = "0006_governance_controls"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute(
            "CREATE TRIGGER trident_audit_events_no_truncate "
            "BEFORE TRUNCATE ON audit_events FOR EACH STATEMENT "
            "EXECUTE FUNCTION trident_reject_audit_mutation()"
        )


def downgrade() -> None:
    raise RuntimeError("AI-4 audit immutability controls are non-downgradable.")
