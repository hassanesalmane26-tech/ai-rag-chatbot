"""Idempotently reconcile immutable audit guards after schema adoption."""

from alembic import op

revision = "0009_audit_guard_reconciliation"
down_revision = "0008_durable_knowledge_jobs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    op.execute("""
    CREATE OR REPLACE FUNCTION trident_reject_audit_mutation() RETURNS trigger AS $$
    BEGIN RAISE EXCEPTION 'audit_events is append-only'; END; $$ LANGUAGE plpgsql
    """)
    op.execute("""
    DO $$ BEGIN
      IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname='trident_audit_events_immutable') THEN
        CREATE TRIGGER trident_audit_events_immutable BEFORE UPDATE OR DELETE ON audit_events
        FOR EACH ROW EXECUTE FUNCTION trident_reject_audit_mutation();
      END IF;
      IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname='trident_audit_events_no_truncate') THEN
        CREATE TRIGGER trident_audit_events_no_truncate BEFORE TRUNCATE ON audit_events
        FOR EACH STATEMENT EXECUTE FUNCTION trident_reject_audit_mutation();
      END IF;
    END $$
    """)


def downgrade() -> None:
    raise RuntimeError("Immutable audit guard reconciliation is non-downgradable.")
