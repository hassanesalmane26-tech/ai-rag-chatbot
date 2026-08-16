"""Map verified external identities to stable internal principals."""

from sqlalchemy.orm import Session

from app.identity.contracts import (
    AuthenticatedPrincipal,
    PrincipalNotProvisioned,
    VerifiedExternalIdentity,
)
from app.identity.models import ExternalIdentity, User


def resolve_principal(
    db: Session, verified_identity: VerifiedExternalIdentity
) -> AuthenticatedPrincipal:
    mapping = (
        db.query(ExternalIdentity)
        .filter_by(
            issuer=verified_identity.issuer.strip(),
            subject=verified_identity.subject.strip(),
        )
        .first()
    )
    user = db.get(User, mapping.user_id) if mapping else None
    if not user or user.status != "active":
        raise PrincipalNotProvisioned("Verified identity is not provisioned")
    return AuthenticatedPrincipal(
        user_id=user.id,
        issuer=mapping.issuer,
        subject=mapping.subject,
    )
