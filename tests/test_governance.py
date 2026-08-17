import asyncio
import tempfile
import unittest
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import httpx

from app.database.database import Base
from app.database.genesis_models import Workspace
from app.governance.audit import append_audit_event, verify_audit_chain
from app.governance.models import AuditEvent, EntitlementGrant, QuotaCounter
from app.governance.quotas import consume_hourly_quota, enforce_resource_quota, quota_limit
from app.governance.rate_limit import FixedWindowRateLimiter
from app.identity.contracts import AuthenticatedPrincipal
from app.identity.models import User
from app.tenancy.models import Membership, MembershipRole, Organization
from app.core.config import Settings
from app.main import create_app


class GovernanceTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()
        self.user = User()
        self.organization = Organization(name="Org", slug="org", ownership_state="active")
        self.db.add_all([self.user, self.organization])
        self.db.flush()
        self.workspace = Workspace(name="Core", organization_id=self.organization.id)
        self.db.add_all([
            self.workspace,
            Membership(
                user_id=self.user.id,
                organization_id=self.organization.id,
                role=MembershipRole.OWNER.value,
            ),
        ])
        self.db.commit()
        self.principal = AuthenticatedPrincipal(self.user.id, "https://issuer.test", "subject")

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_audit_chain_is_deterministic_and_detects_tampering(self):
        for action in ("workspace.created", "workspace.updated"):
            append_audit_event(
                self.db, action=action, resource_type="workspace",
                resource_id=self.workspace.id, organization_id=self.organization.id,
                workspace_id=self.workspace.id, principal=self.principal,
            )
        self.db.commit()
        events = self.db.query(AuditEvent).order_by(AuditEvent.created_at, AuditEvent.id).all()
        self.assertTrue(verify_audit_chain(events))
        events[1].previous_hash = "f" * 64
        self.assertFalse(verify_audit_chain(events))

    def test_explicit_founder_entitlement_changes_quota_not_authorization(self):
        self.assertEqual(quota_limit(self.db, self.principal, self.organization.id, "workspaces.total"), 10)
        self.db.add(EntitlementGrant(
            user_id=self.user.id, key="ecosystem.full_access", integer_value=1, source="founder"
        ))
        self.db.commit()
        self.assertEqual(quota_limit(self.db, self.principal, self.organization.id, "workspaces.total"), -1)
        self.assertEqual(self.db.query(QuotaCounter).count(), 0)

    def test_resource_and_hourly_quotas_are_enforced(self):
        self.db.add_all([
            EntitlementGrant(organization_id=self.organization.id, key="quota.workspaces.total", integer_value=1, source="plan"),
            EntitlementGrant(organization_id=self.organization.id, key="quota.messages.per_hour", integer_value=1, source="plan"),
        ])
        self.db.commit()
        with self.assertRaisesRegex(Exception, "quota"):
            enforce_resource_quota(self.db, self.principal, self.organization.id, "workspaces.total", 1)
        consume_hourly_quota(self.db, self.principal, self.organization.id, "messages.per_hour")
        self.db.commit()
        with self.assertRaisesRegex(Exception, "quota"):
            consume_hourly_quota(self.db, self.principal, self.organization.id, "messages.per_hour")

    def test_rate_limiter_is_bounded_and_fail_closed_at_limit(self):
        limiter = FixedWindowRateLimiter(2, window_seconds=60, max_buckets=2)
        self.assertTrue(limiter.allow("client")[0])
        self.assertTrue(limiter.allow("client")[0])
        allowed, remaining, retry_after = limiter.allow("client")
        self.assertFalse(allowed)
        self.assertEqual(remaining, 0)
        self.assertGreater(retry_after, 0)

    def test_http_rate_limit_has_stable_contract_and_health_exemption(self):
        async def scenario():
            settings = Settings(
                TRIDENT_DATABASE_URL="sqlite://",
                TRIDENT_RATE_LIMIT_REQUESTS_PER_MINUTE=10,
                _env_file=None,
            )
            application = create_app(settings, self.engine)
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=application), base_url="http://test"
            ) as client:
                for _ in range(10):
                    response = await client.get("/")
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(response.headers["x-trident-api-version"], "1")
                limited = await client.get("/")
                self.assertEqual(limited.status_code, 429)
                self.assertEqual(limited.json()["error"]["code"], "RATE_LIMITED")
                self.assertIn("retry-after", limited.headers)
                self.assertEqual((await client.get("/health/live")).status_code, 200)
        asyncio.run(scenario())

    def test_openapi_operation_ids_are_unique(self):
        settings = Settings(TRIDENT_DATABASE_URL="sqlite://", _env_file=None)
        schema = create_app(settings, self.engine).openapi()
        operation_ids = [
            operation["operationId"]
            for path in schema["paths"].values()
            for method, operation in path.items()
            if method in {"get", "post", "patch", "delete"}
        ]
        self.assertEqual(len(operation_ids), len(set(operation_ids)))


class GovernanceMigrationTests(unittest.TestCase):
    def test_migrated_audit_table_rejects_update_and_delete(self):
        with tempfile.TemporaryDirectory() as directory:
            url = f"sqlite:///{Path(directory) / 'governance.sqlite'}"
            config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
            config.set_main_option("sqlalchemy.url", url)
            command.upgrade(config, "head")
            engine = create_engine(url)
            try:
                with engine.begin() as connection:
                    connection.execute(text("INSERT INTO audit_events (id, action, resource_type, outcome, metadata_json, previous_hash, event_hash, created_at) VALUES ('event', 'test', 'test', 'success', '{}', :zero, :hash, CURRENT_TIMESTAMP)"), {"zero": "0" * 64, "hash": "1" * 64})
                with self.assertRaises(Exception):
                    with engine.begin() as connection:
                        connection.execute(text("UPDATE audit_events SET action='tampered' WHERE id='event'"))
                with self.assertRaises(Exception):
                    with engine.begin() as connection:
                        connection.execute(text("DELETE FROM audit_events WHERE id='event'"))
            finally:
                engine.dispose()
