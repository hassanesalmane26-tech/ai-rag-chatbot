import asyncio
import unittest

from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.database.database import Base
from app.database.genesis_models import Workspace
from app.identity.contracts import (
    AuthenticatedPrincipal,
    AuthenticationUnavailable,
    PrincipalNotProvisioned,
    UnavailableIdentityVerifier,
    VerifiedExternalIdentity,
)
from app.identity.models import ExternalIdentity, User
from app.identity.service import resolve_principal
from app.tenancy.models import Membership, MembershipRole, Organization
from app.tenancy.service import TenantAccessDenied, tenant_context_for_workspace


class IdentityTenancyTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_default_verifier_never_trusts_or_decodes_credentials(self):
        with self.assertRaises(AuthenticationUnavailable):
            asyncio.run(UnavailableIdentityVerifier().verify("unverified.jwt.payload"))
        with self.assertRaises(ValueError):
            VerifiedExternalIdentity(issuer="", subject="subject")

    def test_verified_external_identity_maps_to_stable_internal_user(self):
        user = User(display_name="Test principal")
        self.db.add(user)
        self.db.flush()
        identity = ExternalIdentity(
            user_id=user.id,
            issuer="https://issuer.example",
            subject="stable-subject",
        )
        self.db.add(identity)
        self.db.commit()

        principal = resolve_principal(
            self.db,
            VerifiedExternalIdentity(
                issuer="https://issuer.example", subject="stable-subject"
            ),
        )
        self.assertEqual(principal.user_id, user.id)
        self.assertEqual(principal.issuer, "https://issuer.example")

        self.db.add(
            ExternalIdentity(
                user_id=user.id,
                issuer="https://issuer.example",
                subject="stable-subject",
            )
        )
        with self.assertRaises(IntegrityError):
            self.db.commit()
        self.db.rollback()

        user.status = "disabled"
        self.db.commit()
        with self.assertRaises(PrincipalNotProvisioned):
            resolve_principal(
                self.db,
                VerifiedExternalIdentity(
                    issuer="https://issuer.example", subject="stable-subject"
                ),
            )

    def test_membership_roles_and_uniqueness_are_bounded(self):
        user = User()
        organization = Organization(name="Organization", slug="organization")
        self.db.add_all([user, organization])
        self.db.flush()
        membership = Membership(
            user_id=user.id,
            organization_id=organization.id,
            role=MembershipRole.OWNER.value,
        )
        self.db.add(membership)
        self.db.commit()
        self.assertEqual(MembershipRole(membership.role), MembershipRole.OWNER)

        self.db.add(
            Membership(
                user_id=user.id,
                organization_id=organization.id,
                role=MembershipRole.MEMBER.value,
            )
        )
        with self.assertRaises(IntegrityError):
            self.db.commit()
        self.db.rollback()

        second_user = User()
        self.db.add(second_user)
        self.db.flush()
        self.db.add(
            Membership(
                user_id=second_user.id,
                organization_id=organization.id,
                role="super-admin",
            )
        )
        with self.assertRaises(IntegrityError):
            self.db.commit()

    def test_tenant_context_requires_membership_in_workspace_organization(self):
        user = User()
        other_user = User()
        organization = Organization(name="Allowed", slug="allowed")
        other_organization = Organization(name="Denied", slug="denied")
        self.db.add_all([user, other_user, organization, other_organization])
        self.db.flush()
        workspace = Workspace(name="Tenant Workspace", organization_id=organization.id)
        membership = Membership(
            user_id=user.id,
            organization_id=organization.id,
            role=MembershipRole.ADMIN.value,
        )
        self.db.add_all([workspace, membership])
        self.db.commit()

        principal = AuthenticatedPrincipal(
            user_id=user.id,
            issuer="https://issuer.example",
            subject="allowed",
        )
        context = tenant_context_for_workspace(self.db, principal, workspace.id)
        self.assertEqual(context.organization_id, organization.id)
        self.assertEqual(context.role, MembershipRole.ADMIN)

        denied = AuthenticatedPrincipal(
            user_id=other_user.id,
            issuer="https://issuer.example",
            subject="denied",
        )
        with self.assertRaises(TenantAccessDenied):
            tenant_context_for_workspace(self.db, denied, workspace.id)

        workspace.organization_id = None
        self.db.commit()
        with self.assertRaises(TenantAccessDenied):
            tenant_context_for_workspace(self.db, principal, workspace.id)


if __name__ == "__main__":
    unittest.main()
