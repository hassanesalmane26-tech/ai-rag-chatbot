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
from app.identity.session_service import (
    CSRF_COOKIE,
    SESSION_COOKIE,
    validate_csrf,
    validate_session,
)


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
    authorization = request.headers.get("authorization")
    session_token = request.cookies.get(SESSION_COOKIE)
    try:
        if authorization:
            token = extract_bearer_token(authorization)
            verified = await request.app.state.identity_verifier.verify(token)
            request.state.authentication_method = "bearer"
            return resolve_principal(db, verified)
        if not session_token:
            raise AuthenticationError("AUTHENTICATION_REQUIRED")
        session, principal = validate_session(db, session_token)
        request.state.authentication_method = "session"
        request.state.application_session = session
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            validate_csrf(
                session,
                request.headers.get("x-csrf-token"),
                request.cookies.get(CSRF_COOKIE),
            )
        return principal
    except AuthenticationUnavailable as exc:
        raise AuthenticationConfigurationError() from exc
    except InvalidIdentityCredential as exc:
        raise AuthenticationError() from exc
    except PrincipalNotProvisioned as exc:
        raise AuthenticationError("PRINCIPAL_NOT_PROVISIONED") from exc
    except ValueError as exc:
        raise AuthenticationError("INVALID_SESSION") from exc
