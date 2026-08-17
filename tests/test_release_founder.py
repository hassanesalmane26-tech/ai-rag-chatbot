import tempfile
import unittest
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.product import TRIDENT_PRODUCT
from app.database.database import Base
from app.governance.audit import verify_audit_chain
from app.governance.founder import (
    FOUNDER_ENTITLEMENT,
    FounderBootstrapError,
    assign_founder_entitlement,
    plan_founder_bootstrap,
    revoke_founder_entitlement,
)
from app.governance.entitlements import has_capability
from app.governance.models import AuditEvent, EntitlementGrant
from app.identity.contracts import AuthenticatedPrincipal
from app.identity.models import ExternalIdentity, User
from app.operations.artifacts import artifact_manifest
from app.tenancy.models import Membership, MembershipRole, Organization


class FounderEntitlementSecurityTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://")
        Base.metadata.create_all(self.engine)
        self.db = sessionmaker(bind=self.engine)()
        self.user = User(display_name="Verified candidate")
        self.organization = Organization(name="Owned", slug="owned", ownership_state="active")
        self.db.add_all([self.user, self.organization])
        self.db.flush()
        self.identity = ExternalIdentity(
            user_id=self.user.id, issuer="https://issuer.test", subject="verified"
        )
        self.db.add(self.identity)
        self.db.commit()
        self.principal = AuthenticatedPrincipal(
            self.user.id, self.identity.issuer, self.identity.subject
        )

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def make_owner(self, user=None):
        target = user or self.user
        membership = Membership(
            user_id=target.id,
            organization_id=self.organization.id,
            role=MembershipRole.OWNER.value,
        )
        self.db.add(membership)
        self.db.commit()
        return membership

    def test_unknown_conflicting_and_non_owner_principals_are_rejected(self):
        unknown = AuthenticatedPrincipal("missing", "https://issuer.test", "unknown")
        with self.assertRaises(FounderBootstrapError):
            plan_founder_bootstrap(
                self.db, principal=unknown, organization_id=self.organization.id
            )
        conflicting = AuthenticatedPrincipal(
            "different-user", self.identity.issuer, self.identity.subject
        )
        with self.assertRaises(FounderBootstrapError):
            plan_founder_bootstrap(
                self.db, principal=conflicting, organization_id=self.organization.id
            )
        with self.assertRaises(FounderBootstrapError):
            plan_founder_bootstrap(
                self.db, principal=self.principal, organization_id=self.organization.id
            )
        self.assertEqual(self.db.query(EntitlementGrant).count(), 0)

    def test_wrong_entitlement_and_conflicting_grant_are_rejected(self):
        self.make_owner()
        with self.assertRaises(FounderBootstrapError):
            plan_founder_bootstrap(
                self.db,
                principal=self.principal,
                organization_id=self.organization.id,
                entitlement_key="workspace.admin",
            )
        self.db.add(
            EntitlementGrant(
                user_id=self.user.id,
                key=FOUNDER_ENTITLEMENT,
                integer_value=1,
                source="manual",
            )
        )
        self.db.commit()
        with self.assertRaises(FounderBootstrapError):
            plan_founder_bootstrap(
                self.db, principal=self.principal, organization_id=self.organization.id
            )

    def test_assignment_is_permanent_idempotent_and_immutably_audited(self):
        self.make_owner()
        plan = plan_founder_bootstrap(
            self.db, principal=self.principal, organization_id=self.organization.id
        )
        self.assertFalse(plan.already_active)
        first = assign_founder_entitlement(
            self.db,
            principal=self.principal,
            organization_id=self.organization.id,
            approval_reference="OWNER-APPROVAL-001",
            request_id="request-founder-1",
        )
        second = assign_founder_entitlement(
            self.db,
            principal=self.principal,
            organization_id=self.organization.id,
            approval_reference="OWNER-APPROVAL-001",
        )
        self.assertEqual(first.id, second.id)
        self.assertEqual(first.source, "founder")
        self.assertEqual(first.integer_value, 1)
        self.assertIsNone(first.expires_at)
        self.assertIsNone(first.revoked_at)
        self.assertEqual(self.db.query(EntitlementGrant).count(), 1)
        self.assertTrue(
            has_capability(
                self.db, self.principal, self.organization.id, "edition.nova.access"
            )
        )
        events = self.db.query(AuditEvent).order_by(AuditEvent.created_at, AuditEvent.id).all()
        self.assertEqual([event.action for event in events], ["founder.entitlement_granted"])
        self.assertEqual(events[0].request_id, "request-founder-1")
        self.assertTrue(verify_audit_chain(events))

    def test_revocation_requires_owner_and_preserves_evidence(self):
        self.make_owner()
        grant = assign_founder_entitlement(
            self.db,
            principal=self.principal,
            organization_id=self.organization.id,
            approval_reference="OWNER-APPROVAL-001",
        )
        outsider = User()
        self.db.add(outsider)
        self.db.flush()
        outsider_identity = ExternalIdentity(
            user_id=outsider.id, issuer="https://issuer.test", subject="outsider"
        )
        self.db.add(outsider_identity)
        self.db.commit()
        outsider_principal = AuthenticatedPrincipal(
            outsider.id, outsider_identity.issuer, outsider_identity.subject
        )
        with self.assertRaises(FounderBootstrapError):
            revoke_founder_entitlement(
                self.db,
                operator=outsider_principal,
                target_user_id=self.user.id,
                organization_id=self.organization.id,
                approval_reference="OWNER-REVOCATION-001",
            )
        revoked = revoke_founder_entitlement(
            self.db,
            operator=self.principal,
            target_user_id=self.user.id,
            organization_id=self.organization.id,
            approval_reference="OWNER-REVOCATION-001",
        )
        self.assertIsNotNone(revoked.revoked_at)
        self.assertEqual(self.db.query(EntitlementGrant).count(), 1)
        events = self.db.query(AuditEvent).order_by(AuditEvent.created_at, AuditEvent.id).all()
        self.assertEqual(
            [event.action for event in events],
            ["founder.entitlement_granted", "founder.entitlement_revoked"],
        )
        self.assertTrue(verify_audit_chain(events))
        with self.assertRaises(FounderBootstrapError):
            plan_founder_bootstrap(
                self.db, principal=self.principal, organization_id=self.organization.id
            )


class ProductAttributionTests(unittest.TestCase):
    def test_creator_attribution_is_canonical_and_authorization_independent(self):
        self.assertEqual(TRIDENT_PRODUCT.creator, "Salmane Hassan")
        self.assertEqual(TRIDENT_PRODUCT.attribution, "Created by Salmane Hassan")
        self.assertEqual(TRIDENT_PRODUCT.project_mark, "A TRIDENT Project")


class ArtifactManifestTests(unittest.TestCase):
    def test_manifest_is_deterministic_and_content_addressed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "assets").mkdir()
            (root / "index.html").write_text("TRIDENT", encoding="utf-8")
            (root / "assets/app.js").write_text("workspace", encoding="utf-8")
            first = artifact_manifest(root)
            second = artifact_manifest(root)
            self.assertEqual(first, second)
            self.assertEqual(
                [item["path"] for item in first["files"]],
                ["assets/app.js", "index.html"],
            )
            self.assertEqual(len(first["sha256"]), 64)
