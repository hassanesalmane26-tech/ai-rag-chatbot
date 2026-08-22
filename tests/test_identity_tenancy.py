import asyncio
import unittest

from sqlalchemy import create_engine, select
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
from app.identity.service import resolve_or_create_principal, resolve_principal
from app.governance.models import AuditEvent, EntitlementGrant
from app.tenancy.models import Membership, MembershipRole, Organization
from app.tenancy.service import (
    LEGACY_ORGANIZATION_ID,
    LegacyOrganizationClaimError,
    TenantAccessDenied,
    claim_legacy_organization,
    claim_persisted_legacy_organization,
    ensure_legacy_organization,
    onboard_personal_tenant,
    tenant_context_for_workspace,
)


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

    def test_verified_identity_jit_creation_grants_no_membership(self):
        principal = resolve_or_create_principal(
            self.db,
            VerifiedExternalIdentity(
                issuer="https://issuer.example", subject="new-verified-subject"
            ),
        )
        self.assertIsNotNone(self.db.get(User, principal.user_id))
        self.assertEqual(
            self.db.query(Membership).filter_by(user_id=principal.user_id).count(), 0
        )

    def test_first_login_creates_one_personal_tenant_without_founder_entitlement(self):
        user = User()
        self.db.add(user)
        self.db.flush()
        principal = AuthenticatedPrincipal(user.id, "https://issuer.example", "personal-user")

        onboarding = onboard_personal_tenant(self.db, principal)
        self.db.commit()

        self.assertIsNotNone(onboarding)
        self.assertEqual(self.db.query(Organization).count(), 1)
        self.assertEqual(self.db.query(Workspace).count(), 1)
        membership = self.db.query(Membership).one()
        workspace = self.db.query(Workspace).one()
        self.assertEqual(membership.user_id, user.id)
        self.assertEqual(membership.role, MembershipRole.OWNER.value)
        self.assertEqual(workspace.organization_id, membership.organization_id)
        self.assertNotEqual(membership.organization_id, LEGACY_ORGANIZATION_ID)
        self.assertEqual(self.db.query(EntitlementGrant).count(), 0)

    def test_personal_tenant_onboarding_retry_is_idempotent(self):
        user = User()
        self.db.add(user)
        self.db.flush()
        principal = AuthenticatedPrincipal(user.id, "https://issuer.example", "retry-user")

        first = onboard_personal_tenant(self.db, principal)
        self.db.commit()
        retry = onboard_personal_tenant(self.db, principal)
        self.db.commit()

        self.assertIsNotNone(first)
        self.assertIsNotNone(retry)
        self.assertFalse(retry.created)
        self.assertEqual(retry.organization.id, first.organization.id)
        self.assertEqual(retry.workspace.id, first.workspace.id)
        self.assertEqual(self.db.query(Organization).count(), 1)
        self.assertEqual(self.db.query(Membership).count(), 1)
        self.assertEqual(self.db.query(Workspace).count(), 1)

    def test_personal_tenant_onboarding_leaves_existing_member_unchanged(self):
        user = User()
        organization = Organization(name="Existing", slug="existing", ownership_state="active")
        self.db.add_all([user, organization])
        self.db.flush()
        membership = Membership(
            user_id=user.id,
            organization_id=organization.id,
            role=MembershipRole.MEMBER.value,
        )
        workspace = Workspace(name="Existing Workspace", organization_id=organization.id)
        self.db.add_all([membership, workspace])
        self.db.commit()
        principal = AuthenticatedPrincipal(user.id, "https://issuer.example", "existing-user")

        result = onboard_personal_tenant(self.db, principal)
        self.db.commit()

        self.assertIsNone(result)
        self.assertEqual(self.db.query(Organization).count(), 1)
        self.assertEqual(self.db.query(Membership).one().role, MembershipRole.MEMBER.value)
        self.assertEqual(self.db.query(Workspace).one().id, workspace.id)

    def test_personal_tenant_remains_isolated_from_other_users(self):
        user = User()
        other_user = User()
        self.db.add_all([user, other_user])
        self.db.flush()
        principal = AuthenticatedPrincipal(user.id, "https://issuer.example", "owner")
        other = AuthenticatedPrincipal(other_user.id, "https://issuer.example", "other")
        onboarding = onboard_personal_tenant(self.db, principal)
        self.db.commit()

        context = tenant_context_for_workspace(self.db, principal, onboarding.workspace.id)
        self.assertEqual(context.organization_id, onboarding.organization.id)
        with self.assertRaises(TenantAccessDenied):
            tenant_context_for_workspace(self.db, other, onboarding.workspace.id)

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

    def test_legacy_claim_requires_verified_identity_and_is_one_time(self):
        organization = ensure_legacy_organization(self.db)
        workspace = Workspace(name="Preserved", organization_id=organization.id)
        self.db.add(workspace)
        self.db.commit()
        workspace_id = workspace.id

        identity = VerifiedExternalIdentity(
            issuer="https://issuer.example", subject="verified-owner"
        )
        principal = claim_legacy_organization(self.db, identity)
        self.assertEqual(self.db.get(Workspace, workspace_id).organization_id, LEGACY_ORGANIZATION_ID)
        claimed = self.db.get(Organization, LEGACY_ORGANIZATION_ID)
        self.assertEqual(claimed.ownership_state, "active")
        membership = self.db.query(Membership).filter_by(user_id=principal.user_id).one()
        self.assertEqual(membership.role, MembershipRole.OWNER.value)
        self.assertEqual(membership.organization_id, LEGACY_ORGANIZATION_ID)

        with self.assertRaises(LegacyOrganizationClaimError):
            claim_legacy_organization(self.db, identity)

    def test_host_claim_requires_persisted_active_identity_and_is_audited(self):
        organization = ensure_legacy_organization(self.db)
        workspace = Workspace(name="Preserved", organization_id=organization.id)
        user = User()
        self.db.add_all([workspace, user])
        self.db.flush()
        mapping = ExternalIdentity(
            user_id=user.id,
            issuer="https://issuer.example",
            subject="persisted-owner",
        )
        self.db.add(mapping)
        self.db.commit()
        principal = AuthenticatedPrincipal(user.id, mapping.issuer, mapping.subject)

        membership = claim_persisted_legacy_organization(
            self.db,
            principal=principal,
            approval_reference="OWNER-CLOSURE-001",
        )
        self.assertEqual(membership.role, MembershipRole.OWNER.value)
        self.assertEqual(self.db.get(Workspace, workspace.id).id, workspace.id)
        self.assertEqual(
            self.db.get(Organization, LEGACY_ORGANIZATION_ID).ownership_state,
            "active",
        )
        event = self.db.execute(select(AuditEvent)).scalar_one()
        self.assertEqual(event.action, "organization.legacy_claimed")

        same = claim_persisted_legacy_organization(
            self.db,
            principal=principal,
            approval_reference="OWNER-CLOSURE-001",
        )
        self.assertEqual(same.id, membership.id)
        self.assertEqual(self.db.execute(select(AuditEvent)).scalars().all(), [event])

        conflicting = AuthenticatedPrincipal("different", mapping.issuer, mapping.subject)
        with self.assertRaises(LegacyOrganizationClaimError):
            claim_persisted_legacy_organization(
                self.db,
                principal=conflicting,
                approval_reference="OWNER-CLOSURE-002",
            )


if __name__ == "__main__":
    unittest.main()
