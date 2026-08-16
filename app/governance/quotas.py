"""Edition-ready entitlements and durable Organization quota accounting."""

from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.errors import QuotaExceededError
from app.governance.models import EntitlementGrant, QuotaCounter
from app.identity.contracts import AuthenticatedPrincipal

AI_DEFAULTS = {
    "workspaces.total": 10,
    "documents.per_workspace": 100,
    "conversations.per_workspace": 200,
    "memories.per_workspace": 500,
    "messages.per_hour": 100,
}


def _lock_scope(db: Session, organization_id: str, metric: str) -> None:
    if db.bind and db.bind.dialect.name == "postgresql":
        db.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:scope, 0))"),
            {"scope": f"quota:{organization_id}:{metric}"},
        )


def _active(query, now: datetime):
    return query.filter(EntitlementGrant.revoked_at.is_(None)).filter(
        (EntitlementGrant.expires_at.is_(None)) | (EntitlementGrant.expires_at > now)
    )


def entitlement_value(
    db: Session, principal: AuthenticatedPrincipal, organization_id: str, key: str
) -> int | None:
    now = datetime.now(timezone.utc)
    user_grant = _active(db.query(EntitlementGrant).filter_by(user_id=principal.user_id, key=key), now).first()
    if user_grant:
        return user_grant.integer_value
    org_grant = _active(db.query(EntitlementGrant).filter_by(organization_id=organization_id, key=key), now).first()
    return org_grant.integer_value if org_grant else None


def quota_limit(db: Session, principal: AuthenticatedPrincipal, organization_id: str, metric: str) -> int:
    unlimited = entitlement_value(db, principal, organization_id, "ecosystem.full_access")
    if unlimited == 1:
        return -1
    override = entitlement_value(db, principal, organization_id, f"quota.{metric}")
    return override if override is not None else AI_DEFAULTS[metric]


def enforce_resource_quota(
    db: Session, principal: AuthenticatedPrincipal, organization_id: str, metric: str, current: int
) -> None:
    _lock_scope(db, organization_id, metric)
    limit = quota_limit(db, principal, organization_id, metric)
    if limit >= 0 and current >= limit:
        raise QuotaExceededError(metric, limit)


def consume_hourly_quota(
    db: Session, principal: AuthenticatedPrincipal, organization_id: str, metric: str
) -> None:
    _lock_scope(db, organization_id, metric)
    limit = quota_limit(db, principal, organization_id, metric)
    if limit < 0:
        return
    now = datetime.now(timezone.utc)
    window = now.replace(minute=0, second=0, microsecond=0)
    counter = (
        db.query(QuotaCounter)
        .filter_by(organization_id=organization_id, metric=metric, window_start=window)
        .with_for_update().first()
    )
    if counter is None:
        counter = QuotaCounter(organization_id=organization_id, metric=metric, window_start=window, used=0)
        db.add(counter)
        db.flush()
    if counter.used >= limit:
        raise QuotaExceededError(metric, limit)
    counter.used += 1
    db.flush()
