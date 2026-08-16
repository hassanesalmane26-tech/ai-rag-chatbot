"""Fail-closed FastAPI dependencies for verified TRIDENT principals."""

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.errors import AuthenticationConfigurationError, AuthenticationError
from app.database.database import get_db
from app.identity.contracts import (
    AuthenticatedPrincipal,
    AuthenticationUnavailable,
    InvalidIdentityCredential,
    PrincipalNotProvisioned,
)
from app.identity.service import resolve_principal


def extract_bearer_token(authorization: str | None) -> str:
    if not authorization:
        raise AuthenticationError("AUTHENTICATION_REQUIRED")
    parts = authorization.strip().split()
    if len(parts) != 2 or parts[0].lower() != "bearer" or not parts[1]:
        raise AuthenticationError("INVALID_AUTHORIZATION_HEADER")
    return parts[1]


async def require_principal(
    request: Request, db: Session = Depends(get_db)
) -> AuthenticatedPrincipal:
    if request.app.state.security_mode != "oidc":
        raise AuthenticationConfigurationError()
    token = extract_bearer_token(request.headers.get("authorization"))
    try:
        verified = await request.app.state.identity_verifier.verify(token)
        return resolve_principal(db, verified)
    except AuthenticationUnavailable as exc:
        raise AuthenticationConfigurationError() from exc
    except InvalidIdentityCredential as exc:
        raise AuthenticationError() from exc
    except PrincipalNotProvisioned as exc:
        raise AuthenticationError("PRINCIPAL_NOT_PROVISIONED") from exc
