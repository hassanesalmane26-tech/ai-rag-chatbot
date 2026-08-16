"""Provider-neutral Authorization Code + PKCE client boundary."""

import asyncio
import json
from dataclasses import dataclass
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import httpx

from app.identity.contracts import InvalidIdentityCredential
from app.identity.oidc import _https_url


@dataclass(frozen=True, slots=True)
class OIDCProviderMetadata:
    issuer: str
    authorization_endpoint: str
    token_endpoint: str
    end_session_endpoint: str = ""


class AuthorizationCodeClient:
    def __init__(
        self,
        issuer: str,
        client_id: str,
        redirect_uri: str,
        scopes: tuple[str, ...],
        timeout_seconds: float = 5.0,
    ):
        self.issuer = _https_url(issuer, "issuer")
        self.client_id = client_id
        self.redirect_uri = redirect_uri
        self.scopes = scopes
        self.timeout_seconds = timeout_seconds
        self._metadata: OIDCProviderMetadata | None = None

    def metadata(self) -> OIDCProviderMetadata:
        if self._metadata:
            return self._metadata
        try:
            request = Request(
                f"{self.issuer}/.well-known/openid-configuration",
                headers={"Accept": "application/json"},
            )
            with urlopen(request, timeout=self.timeout_seconds) as response:
                payload = json.loads(response.read(262_145))
            if str(payload.get("issuer", "")).rstrip("/") != self.issuer:
                raise InvalidIdentityCredential("OIDC metadata issuer mismatch")
            self._metadata = OIDCProviderMetadata(
                issuer=self.issuer,
                authorization_endpoint=_https_url(
                    str(payload.get("authorization_endpoint", "")), "authorization endpoint"
                ),
                token_endpoint=_https_url(
                    str(payload.get("token_endpoint", "")), "token endpoint"
                ),
                end_session_endpoint=(
                    _https_url(str(payload["end_session_endpoint"]), "logout endpoint")
                    if payload.get("end_session_endpoint") else ""
                ),
            )
            return self._metadata
        except InvalidIdentityCredential:
            raise
        except Exception as exc:
            raise InvalidIdentityCredential("OIDC metadata is unavailable") from exc

    def authorization_url(self, state: str, nonce: str, code_challenge: str) -> str:
        query = urlencode(
            {
                "response_type": "code",
                "client_id": self.client_id,
                "redirect_uri": self.redirect_uri,
                "scope": " ".join(self.scopes),
                "state": state,
                "nonce": nonce,
                "code_challenge": code_challenge,
                "code_challenge_method": "S256",
            }
        )
        return f"{self.metadata().authorization_endpoint}?{query}"

    async def exchange(self, code: str, code_verifier: str) -> dict:
        try:
            metadata = await asyncio.to_thread(self.metadata)
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(
                    metadata.token_endpoint,
                    data={
                        "grant_type": "authorization_code",
                        "client_id": self.client_id,
                        "redirect_uri": self.redirect_uri,
                        "code": code,
                        "code_verifier": code_verifier,
                    },
                    headers={"Accept": "application/json"},
                )
            response.raise_for_status()
            payload = response.json()
        except Exception as exc:
            raise InvalidIdentityCredential("OIDC code exchange failed") from exc
        if payload.get("token_type", "").lower() != "bearer" or not payload.get("id_token"):
            raise InvalidIdentityCredential("OIDC token response is incomplete")
        return payload

    def logout_url(self, post_logout_redirect_uri: str) -> str | None:
        endpoint = self.metadata().end_session_endpoint
        if not endpoint or not post_logout_redirect_uri:
            return None
        return f"{endpoint}?{urlencode({'client_id': self.client_id, 'post_logout_redirect_uri': post_logout_redirect_uri})}"
