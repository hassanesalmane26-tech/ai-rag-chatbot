"""Identity contracts that do not depend on a commercial OIDC provider."""

from dataclasses import dataclass
from typing import Protocol


class AuthenticationUnavailable(RuntimeError):
    """Raised when no cryptographic identity verifier is configured."""


class PrincipalNotProvisioned(LookupError):
    """Raised when a verified external identity has no internal TRIDENT User."""


@dataclass(frozen=True, slots=True)
class VerifiedExternalIdentity:
    """Claims emitted only after verification by an IdentityVerifier adapter."""

    issuer: str
    subject: str

    def __post_init__(self) -> None:
        if not self.issuer.strip() or not self.subject.strip():
            raise ValueError("A verified identity requires issuer and subject")


@dataclass(frozen=True, slots=True)
class AuthenticatedPrincipal:
    """Stable internal identity used by TRIDENT domain services."""

    user_id: str
    issuer: str
    subject: str


class IdentityVerifier(Protocol):
    async def verify(self, credential: str) -> VerifiedExternalIdentity:
        """Cryptographically verify a credential and return stable OIDC identity."""


class UnavailableIdentityVerifier:
    """Safe AI-1 default: never decodes or trusts an incoming credential."""

    async def verify(self, credential: str) -> VerifiedExternalIdentity:
        del credential
        raise AuthenticationUnavailable("No verified OIDC adapter is configured")
