import tempfile
import unittest
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.database import Base
from app.governance.founder import plan_founder_bootstrap
from app.identity.models import ExternalIdentity, User
from app.operations.artifacts import artifact_manifest
from app.tenancy.models import Membership, MembershipRole, Organization


class FounderPreparationTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://")
        Base.metadata.create_all(self.engine)
        self.db = sessionmaker(bind=self.engine)()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_unknown_identity_is_never_fabricated(self):
        with self.assertRaises(ValueError):
            plan_founder_bootstrap(self.db, issuer="https://issuer.test", subject="unknown")
        self.assertEqual(self.db.query(User).count(), 0)

    def test_plan_requires_verified_identity_and_explicit_owner_membership(self):
        user = User(display_name="Verified candidate")
        organization = Organization(name="Owned", slug="owned", ownership_state="active")
        self.db.add_all([user, organization])
        self.db.flush()
        self.db.add(ExternalIdentity(user_id=user.id, issuer="https://issuer.test", subject="verified"))
        self.db.commit()
        with self.assertRaises(ValueError):
            plan_founder_bootstrap(self.db, issuer="https://issuer.test", subject="verified")
        self.db.add(Membership(user_id=user.id, organization_id=organization.id, role=MembershipRole.OWNER.value))
        self.db.commit()
        plan = plan_founder_bootstrap(self.db, issuer="https://issuer.test", subject="verified")
        self.assertEqual(plan.user_id, user.id)
        self.assertEqual(plan.owner_organization_ids, (organization.id,))
        self.assertEqual(plan.entitlement_keys, ("ecosystem.full_access",))


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
            self.assertEqual([item["path"] for item in first["files"]], ["assets/app.js", "index.html"])
            self.assertEqual(len(first["sha256"]), 64)
