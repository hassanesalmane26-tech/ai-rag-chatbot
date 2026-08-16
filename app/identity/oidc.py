"""Standards-based OIDC JWT verification without provider-specific domain coupling."""

import asyncio
import json
import threading
from dataclasses import dataclass
from urllib.parse import urlparse
from urllib.request import Request, urlopen

import jwt
from jwt import PyJWKClient

from app.identity.contracts import InvalidIdentityCredential, VerifiedExternalIdentity


@dataclass(frozen=True, slots=True)
class OIDCConfiguration:
    issuer: str
    audience: str
    algorithms: tuple[str, ...] = ("RS256",)
    jwks_url: str = ""
    clock_skew_seconds: int = 30
    http_timeout_seconds: float = 5.0


def _https_url(value: str, label: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
        raise InvalidIdentityCredential(f"Invalid {label} configuration")
    return value.rstrip("/")


class OIDCIdentityVerifier:
    """Verify signatures and mandatory OIDC claims against trusted issuer metadata."""

    def __init__(self, configuration: OIDCConfiguration):
        self.configuration = configuration
        self.issuer = _https_url(configuration.issuer, "issuer")
        if not configuration.audience.strip() or not configuration.algorithms:
            raise ValueError("OIDC audience and algorithms are required")
        self._jwks_url = _https_url(configuration.jwks_url, "JWKS URL") if configuration.jwks_url else ""
        self._jwks_client: PyJWKClient | None = None
        self._lock = threading.Lock()

    def _discover_jwks_url(self) -> str:
        discovery_url = f"{self.issuer}/.well-known/openid-configuration"
        try:
            request = Request(discovery_url, headers={"Accept": "application/json"})
            with urlopen(request, timeout=self.configuration.http_timeout_seconds) as response:
                metadata = json.loads(response.read(262_145))
        except Exception as exc:
            raise InvalidIdentityCredential("OIDC metadata is unavailable") from exc
        if metadata.get("issuer", "").rstrip("/") != self.issuer:
            raise InvalidIdentityCredential("OIDC metadata issuer mismatch")
        return _https_url(str(metadata.get("jwks_uri", "")), "JWKS URL")

    def _client(self) -> PyJWKClient:
        with self._lock:
            if self._jwks_client is None:
                url = self._jwks_url or self._discover_jwks_url()
                self._jwks_client = PyJWKClient(
                    url,
                    cache_keys=True,
                    cache_jwk_set=True,
                    lifespan=300,
                    timeout=self.configuration.http_timeout_seconds,
                )
            return self._jwks_client

    def _verify_sync(
        self, credential: str, expected_nonce: str | None = None
    ) -> VerifiedExternalIdentity:
        try:
            header = jwt.get_unverified_header(credential)
            algorithm = header.get("alg")
            if algorithm not in self.configuration.algorithms:
                raise InvalidIdentityCredential("Unsupported token algorithm")
            signing_key = self._client().get_signing_key_from_jwt(credential)
            claims = jwt.decode(
                credential,
                signing_key.key,
                algorithms=list(self.configuration.algorithms),
                audience=self.configuration.audience,
                issuer=self.issuer,
                leeway=self.configuration.clock_skew_seconds,
                options={"require": ["exp", "iat", "iss", "aud", "sub"]},
            )
            issuer = str(claims["iss"]).rstrip("/")
            subject = str(claims["sub"]).strip()
            if issuer != self.issuer or not subject:
                raise InvalidIdentityCredential("Invalid identity claims")
            if expected_nonce is not None and claims.get("nonce") != expected_nonce:
                raise InvalidIdentityCredential("OIDC nonce mismatch")
            return VerifiedExternalIdentity(issuer=issuer, subject=subject)
        except InvalidIdentityCredential:
            raise
        except Exception as exc:
            raise InvalidIdentityCredential("Credential verification failed") from exc

    async def verify(self, credential: str) -> VerifiedExternalIdentity:
        return await asyncio.to_thread(self._verify_sync, credential)

    async def verify_id_token(
        self, credential: str, expected_nonce: str
    ) -> VerifiedExternalIdentity:
        return await asyncio.to_thread(self._verify_sync, credential, expected_nonce)
