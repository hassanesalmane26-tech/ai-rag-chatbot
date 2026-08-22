import asyncio
import time
import unittest
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import jwt
import httpx
from cryptography.hazmat.primitives.asymmetric import rsa

from app.identity.contracts import InvalidIdentityCredential
from app.identity.oidc import OIDCConfiguration, OIDCIdentityVerifier
from app.core.config import Settings
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database.database import Base, get_db
from app.identity.contracts import VerifiedExternalIdentity
from app.identity.contracts import AuthenticatedPrincipal
from app.identity.models import ExternalIdentity, User
from app.database.genesis_models import Workspace
from app.identity.session_service import create_session, validate_session, utcnow
from app.main import create_app
from app.tenancy.models import Membership, MembershipRole, Organization
from app.security.dependencies import extract_bearer_token


class StaticKeyClient:
    def __init__(self, key):
        self.key = key

    def get_signing_key_from_jwt(self, _credential):
        return SimpleNamespace(key=self.key)


class OIDCVerificationTests(unittest.TestCase):
    issuer = "https://issuer.test"
    audience = "trident-api"

    def setUp(self):
        self.private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        self.other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        self.verifier = OIDCIdentityVerifier(
            OIDCConfiguration(
                issuer=self.issuer,
                audience=self.audience,
                jwks_url="https://issuer.test/jwks",
                clock_skew_seconds=0,
            )
        )
        self.verifier._jwks_client = StaticKeyClient(self.private_key.public_key())

    def token(self, **overrides):
        now = int(time.time())
        claims = {
            "iss": self.issuer,
            "aud": self.audience,
            "sub": "stable-subject",
            "iat": now,
            "exp": now + 300,
        }
        claims.update(overrides)
        key = claims.pop("_key", self.private_key)
        algorithm = claims.pop("_algorithm", "RS256")
        return jwt.encode(claims, key, algorithm=algorithm, headers={"kid": "test-key"})

    def verify(self, token):
        return asyncio.run(self.verifier.verify(token))

    def test_valid_signature_returns_only_stable_verified_identity(self):
        identity = self.verify(self.token(email="mutable@example.test", role="owner"))
        self.assertEqual(identity.issuer, self.issuer)
        self.assertEqual(identity.subject, "stable-subject")

    def test_signature_expiry_issuer_audience_and_subject_fail_closed(self):
        invalid_tokens = [
            self.token(_key=self.other_key),
            self.token(exp=int(time.time()) - 1),
            self.token(iss="https://wrong-issuer.test"),
            self.token(aud="wrong-audience"),
            self.token(sub=""),
            self.token(nbf=int(time.time()) + 300),
        ]
        for token in invalid_tokens:
            with self.assertRaises(InvalidIdentityCredential):
                self.verify(token)
        with self.assertRaises(InvalidIdentityCredential):
            asyncio.run(self.verifier.verify_id_token(self.token(nonce="wrong"), "expected"))

    def test_unsigned_symmetric_malformed_and_algorithm_confusion_are_rejected(self):
        tokens = [
            "not-a-jwt",
            jwt.encode(
                {
                    "iss": self.issuer,
                    "aud": self.audience,
                    "sub": "subject",
                    "iat": int(time.time()),
                    "exp": int(time.time()) + 300,
                },
                "shared-secret-that-is-long-enough-for-hs256",
                algorithm="HS256",
            ),
        ]
        for token in tokens:
            with self.assertRaises(InvalidIdentityCredential):
                self.verify(token)

    def test_discovery_requires_exact_issuer_and_https_jwks(self):
        verifier = OIDCIdentityVerifier(
            OIDCConfiguration(issuer=self.issuer, audience=self.audience)
        )
        response = unittest.mock.MagicMock()
        response.__enter__.return_value.read.return_value = (
            b'{"issuer":"https://issuer.test","jwks_uri":"https://issuer.test/jwks"}'
        )
        with patch("app.identity.oidc.urlopen", return_value=response):
            self.assertEqual(verifier._discover_jwks_url(), "https://issuer.test/jwks")

        response.__enter__.return_value.read.return_value = (
            b'{"issuer":"https://attacker.test","jwks_uri":"https://attacker.test/jwks"}'
        )
        with patch("app.identity.oidc.urlopen", return_value=response):
            with self.assertRaises(InvalidIdentityCredential):
                verifier._discover_jwks_url()

    def test_bearer_extraction_is_strict(self):
        self.assertEqual(extract_bearer_token("Bearer credential"), "credential")
        for header in (None, "", "Bearer", "Basic value", "Bearer one two"):
            with self.assertRaises(Exception):
                extract_bearer_token(header)


class ControlledVerifier:
    async def verify(self, _credential):
        return VerifiedExternalIdentity("https://issuer.test", "session-subject")


class ControlledIDTokenVerifier:
    async def verify_id_token(self, credential, expected_nonce):
        if credential != "signed-id-token" or not expected_nonce:
            raise InvalidIdentityCredential("invalid controlled ID token")
        return VerifiedExternalIdentity("https://issuer.test", "session-subject")


class ControlledAuthorizationCodeClient:
    def __init__(self):
        self.nonce = None
        self.challenge = None

    def authorization_url(self, state, nonce, code_challenge):
        self.nonce, self.challenge = nonce, code_challenge
        return f"https://issuer.test/authorize?state={state}"

    async def exchange(self, code, code_verifier):
        if code != "valid-code" or not code_verifier:
            raise InvalidIdentityCredential("exchange rejected")
        return {"token_type": "Bearer", "id_token": "signed-id-token"}

    def logout_url(self, post_logout_redirect_uri):
        return f"https://issuer.test/logout?return={post_logout_redirect_uri}"


class SessionLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.engine = create_engine(f"sqlite:///{Path(self.tempdir.name) / 'sessions.sqlite'}")
        Base.metadata.create_all(bind=self.engine)
        self.Session = sessionmaker(bind=self.engine)
        db = self.Session()
        user = User()
        organization = Organization(name="Session Org", slug="session-org", ownership_state="active")
        db.add_all([user, organization]); db.flush()
        workspace = Workspace(name="Session Workspace", organization_id=organization.id)
        db.add(workspace); db.flush()
        db.add_all([
            ExternalIdentity(user_id=user.id, issuer="https://issuer.test", subject="session-subject"),
            Membership(user_id=user.id, organization_id=organization.id, role=MembershipRole.OWNER.value),
        ])
        db.commit()
        self.organization_id = organization.id
        self.workspace_id = workspace.id
        db.close()
        configured = Settings(
            TRIDENT_ENV="test",
            TRIDENT_DATABASE_URL=str(self.engine.url),
            TRIDENT_SECURITY_MODE="oidc",
            TRIDENT_OIDC_ISSUER="https://issuer.test",
            TRIDENT_OIDC_AUDIENCE="trident-api",
            TRIDENT_OIDC_CLIENT_ID="trident-web",
            TRIDENT_OIDC_REDIRECT_URI="http://test/v1/session/callback",
            TRIDENT_OIDC_POST_LOGOUT_REDIRECT_URI="http://test/",
            TRIDENT_SESSION_COOKIE_SECURE=False,
            _env_file=None,
        )
        self.code_client = ControlledAuthorizationCodeClient()
        self.application = create_app(configured, self.engine, ControlledVerifier())
        self.application.state.authorization_code_client = self.code_client
        self.application.state.id_token_verifier = ControlledIDTokenVerifier()
        def test_db():
            db = self.Session()
            try:
                yield db
            finally:
                db.close()
        self.application.dependency_overrides[get_db] = test_db

    def tearDown(self):
        self.engine.dispose()
        self.tempdir.cleanup()

    async def scenario(self):
        transport = httpx.ASGITransport(app=self.application, raise_app_exceptions=False)
        async with self.application.router.lifespan_context(self.application):
            async with httpx.AsyncClient(
                transport=transport, base_url="http://test", follow_redirects=False
            ) as client:
                configuration = await client.get("/v1/session/configuration")
                self.assertTrue(configuration.json()["data"]["enabled"])
                started = await client.post("/v1/session/login", json={"return_to": "//attacker.test"})
                self.assertEqual(started.status_code, 201, started.text)
                state = started.json()["data"]["authorization_url"].split("state=")[1]
                self.assertTrue(self.code_client.challenge)
                callback = await client.get(
                    "/v1/session/callback", params={"code": "valid-code", "state": state}
                )
                self.assertEqual(callback.status_code, 303, callback.text)
                self.assertEqual(callback.headers["location"], "/")

                current = await client.get("/v1/session")
                self.assertEqual(current.status_code, 200, current.text)
                self.assertEqual(current.json()["data"]["organizations"][0]["id"], self.organization_id)

                denied = await client.post(
                    "/v1/session/context",
                    json={"organization_id": self.organization_id, "workspace_id": self.workspace_id},
                )
                self.assertEqual(denied.status_code, 401, denied.text)
                csrf = client.cookies.get("trident_csrf")
                selected = await client.post(
                    "/v1/session/context",
                    json={"organization_id": self.organization_id, "workspace_id": self.workspace_id},
                    headers={"X-CSRF-Token": csrf},
                )
                self.assertEqual(selected.status_code, 200, selected.text)
                self.assertEqual(selected.json()["data"]["active_organization_id"], self.organization_id)
                self.assertEqual(selected.json()["data"]["active_workspace_id"], self.workspace_id)
                visible = await client.get("/v1/workspaces")
                self.assertEqual([item["id"] for item in visible.json()["data"]], [self.workspace_id])

                logout = await client.post(
                    "/v1/session/logout", headers={"X-CSRF-Token": csrf}
                )
                self.assertEqual(logout.status_code, 200, logout.text)
                self.assertTrue(logout.json()["data"]["logged_out"])
                expired = await client.get("/v1/session")
                self.assertEqual(expired.status_code, 401, expired.text)

    def test_authorization_code_pkce_session_context_csrf_and_logout(self):
        asyncio.run(self.scenario())

    async def first_login_scenario(self):
        db = self.Session()
        db.query(Membership).delete()
        db.query(Workspace).delete()
        db.query(Organization).delete()
        db.commit()
        db.close()

        transport = httpx.ASGITransport(app=self.application, raise_app_exceptions=False)
        async with self.application.router.lifespan_context(self.application):
            async with httpx.AsyncClient(
                transport=transport, base_url="http://test", follow_redirects=False
            ) as client:
                started = await client.post("/v1/session/login", json={"return_to": "/"})
                state = started.json()["data"]["authorization_url"].split("state=")[1]
                callback = await client.get(
                    "/v1/session/callback", params={"code": "valid-code", "state": state}
                )
                self.assertEqual(callback.status_code, 303, callback.text)
                current = await client.get("/v1/session")
                self.assertEqual(current.status_code, 200, current.text)
                payload = current.json()["data"]
                self.assertEqual(len(payload["organizations"]), 1)
                self.assertEqual(payload["active_organization_id"], payload["organizations"][0]["id"])
                self.assertEqual(
                    payload["active_workspace_id"],
                    payload["organizations"][0]["workspaces"][0]["id"],
                )

    def test_first_login_onboards_and_selects_personal_workspace(self):
        asyncio.run(self.first_login_scenario())

    def test_expired_and_revoked_sessions_fail_closed(self):
        db = self.Session()
        user = db.query(User).filter_by().first()
        principal = AuthenticatedPrincipal(user.id, "https://issuer.test", "session-subject")
        session, token, _csrf = create_session(db, principal, 300)
        db.commit()
        session.expires_at = utcnow().replace(year=2000)
        db.commit()
        with self.assertRaises(ValueError):
            validate_session(db, token)

        second, second_token, _csrf = create_session(db, principal, 300)
        second.revoked_at = utcnow()
        db.commit()
        with self.assertRaises(ValueError):
            validate_session(db, second_token)
        db.close()


if __name__ == "__main__":
    unittest.main()
