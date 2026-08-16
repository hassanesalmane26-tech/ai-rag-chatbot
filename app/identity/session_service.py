"""Opaque session lifecycle, PKCE transaction state and tenant entry selection."""

import base64
import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.database.genesis_models import Workspace
from app.identity.contracts import AuthenticatedPrincipal
from app.identity.models import ExternalIdentity, User
from app.identity.session_models import ApplicationSession, OIDCLoginTransaction
from app.tenancy.models import Membership, Organization


SESSION_COOKIE = "trident_session"
CSRF_COOKIE = "trident_csrf"
TRANSACTION_COOKIE = "trident_oidc_transaction"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def random_secret(bytes_count: int = 32) -> str:
    return secrets.token_urlsafe(bytes_count)


def code_challenge(verifier: str) -> str:
    return base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()


@dataclass(frozen=True, slots=True)
class LoginStart:
    transaction: OIDCLoginTransaction
    state: str
    nonce: str
    challenge: str


def safe_return_to(value: str | None) -> str:
    candidate = value or "/"
    if not candidate.startswith("/") or candidate.startswith("//") or "\\" in candidate:
        return "/"
    return candidate[:512]


def begin_login(db: Session, ttl_seconds: int, return_to: str | None) -> LoginStart:
    state, nonce, verifier = random_secret(), random_secret(), random_secret(64)
    transaction = OIDCLoginTransaction(
        state_hash=digest(state),
        nonce=nonce,
        code_verifier=verifier,
        return_to=safe_return_to(return_to),
        expires_at=utcnow() + timedelta(seconds=ttl_seconds),
    )
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    return LoginStart(transaction, state, nonce, code_challenge(verifier))


def consume_login(
    db: Session, transaction_id: str, state: str
) -> tuple[OIDCLoginTransaction, str]:
    transaction = (
        db.query(OIDCLoginTransaction)
        .filter(OIDCLoginTransaction.id == transaction_id)
        .with_for_update()
        .first()
    )
    if (
        not transaction
        or transaction.used_at is not None
        or aware(transaction.expires_at) <= utcnow()
        or not secrets.compare_digest(transaction.state_hash, digest(state))
    ):
        raise ValueError("Invalid or expired OIDC transaction")
    return transaction, transaction.code_verifier


def complete_login(transaction: OIDCLoginTransaction) -> None:
    transaction.used_at = utcnow()
    transaction.code_verifier = "consumed"


def create_session(
    db: Session, principal: AuthenticatedPrincipal, ttl_seconds: int
) -> tuple[ApplicationSession, str, str]:
    token, csrf = random_secret(), random_secret()
    now = utcnow()
    session = ApplicationSession(
        token_hash=digest(token),
        csrf_hash=digest(csrf),
        user_id=principal.user_id,
        expires_at=now + timedelta(seconds=ttl_seconds),
        last_seen_at=now,
    )
    db.add(session)
    db.flush()
    return session, token, csrf


def validate_session(db: Session, token: str) -> tuple[ApplicationSession, AuthenticatedPrincipal]:
    session = db.query(ApplicationSession).filter_by(token_hash=digest(token)).first()
    if not session or session.revoked_at or aware(session.expires_at) <= utcnow():
        raise ValueError("Session expired or revoked")
    user = db.get(User, session.user_id)
    mapping = db.query(ExternalIdentity).filter_by(user_id=session.user_id).first()
    if not user or user.status != "active" or not mapping:
        raise ValueError("Session principal unavailable")
    session.last_seen_at = utcnow()
    db.commit()
    db.refresh(session)
    return session, AuthenticatedPrincipal(user.id, mapping.issuer, mapping.subject)


def validate_csrf(session: ApplicationSession, supplied: str | None, cookie: str | None) -> None:
    if not supplied or not cookie or not secrets.compare_digest(supplied, cookie):
        raise ValueError("CSRF validation failed")
    if not secrets.compare_digest(session.csrf_hash, digest(supplied)):
        raise ValueError("CSRF validation failed")


def available_context(db: Session, principal: AuthenticatedPrincipal) -> list[dict]:
    memberships = (
        db.query(Membership, Organization)
        .join(Organization, Organization.id == Membership.organization_id)
        .filter(Membership.user_id == principal.user_id, Organization.ownership_state == "active")
        .order_by(Organization.name.asc())
        .all()
    )
    result = []
    for membership, organization in memberships:
        workspaces = (
            db.query(Workspace)
            .filter_by(organization_id=organization.id)
            .order_by(Workspace.name.asc())
            .all()
        )
        result.append(
            {
                "id": organization.id,
                "name": organization.name,
                "slug": organization.slug,
                "role": membership.role,
                "workspaces": [{"id": item.id, "name": item.name} for item in workspaces],
            }
        )
    return result


def select_context(
    db: Session,
    session: ApplicationSession,
    principal: AuthenticatedPrincipal,
    organization_id: str,
    workspace_id: str | None,
) -> None:
    membership = db.query(Membership).filter_by(
        user_id=principal.user_id, organization_id=organization_id
    ).first()
    organization = db.get(Organization, organization_id)
    if not membership or not organization or organization.ownership_state != "active":
        raise ValueError("Organization unavailable")
    workspace = db.get(Workspace, workspace_id) if workspace_id else None
    if workspace_id and (not workspace or workspace.organization_id != organization_id):
        raise ValueError("Workspace unavailable")
    session.active_organization_id = organization_id
    session.active_workspace_id = workspace_id
    db.commit()
