import asyncio
import time
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa

from app.identity.contracts import InvalidIdentityCredential
from app.identity.oidc import OIDCConfiguration, OIDCIdentityVerifier
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


if __name__ == "__main__":
    unittest.main()
