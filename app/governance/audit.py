"""Append-only, hash-chained audit recording and verification."""

import hashlib
import json
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.governance.models import AuditEvent, new_id
from app.identity.contracts import AuthenticatedPrincipal

GENESIS_HASH = "0" * 64


def _canonical(payload: dict) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _timestamp(value: datetime) -> str:
    aware = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    return aware.astimezone(timezone.utc).isoformat()


def append_audit_event(
    db: Session,
    *,
    action: str,
    resource_type: str,
    principal: AuthenticatedPrincipal | None = None,
    organization_id: str | None = None,
    workspace_id: str | None = None,
    resource_id: str | None = None,
    outcome: str = "success",
    request_id: str | None = None,
    metadata: dict | None = None,
) -> AuditEvent:
    """Append an event; callers never receive an update/delete capability."""
    if db.bind and db.bind.dialect.name == "postgresql":
        scope = organization_id or "global"
        db.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:scope, 0))"), {"scope": f"audit:{scope}"})
    previous = (
        db.query(AuditEvent)
        .filter(AuditEvent.organization_id == organization_id)
        .order_by(AuditEvent.created_at.desc(), AuditEvent.id.desc())
        .with_for_update()
        .first()
    )
    created_at = datetime.now(timezone.utc)
    event = AuditEvent(
        id=new_id(),
        organization_id=organization_id,
        workspace_id=workspace_id,
        actor_user_id=principal.user_id if principal else None,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        outcome=outcome,
        request_id=request_id,
        metadata_json=_canonical(metadata or {}),
        previous_hash=previous.event_hash if previous else GENESIS_HASH,
        created_at=created_at,
    )
    event.event_hash = hashlib.sha256(_canonical({
        "id": event.id,
        "organization_id": organization_id,
        "workspace_id": workspace_id,
        "actor_user_id": event.actor_user_id,
        "action": action,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "outcome": outcome,
        "request_id": request_id,
        "metadata": metadata or {},
        "previous_hash": event.previous_hash,
        "created_at": _timestamp(created_at),
    }).encode()).hexdigest()
    db.add(event)
    db.flush()
    return event


def verify_audit_chain(events: list[AuditEvent]) -> bool:
    previous = GENESIS_HASH
    for event in events:
        if event.previous_hash != previous:
            return False
        payload = {
            "id": event.id, "organization_id": event.organization_id,
            "workspace_id": event.workspace_id, "actor_user_id": event.actor_user_id,
            "action": event.action, "resource_type": event.resource_type,
            "resource_id": event.resource_id, "outcome": event.outcome,
            "request_id": event.request_id, "metadata": json.loads(event.metadata_json),
            "previous_hash": event.previous_hash, "created_at": _timestamp(event.created_at),
        }
        if hashlib.sha256(_canonical(payload).encode()).hexdigest() != event.event_hash:
            return False
        previous = event.event_hash
    return True


def serialize_audit_event(event: AuditEvent) -> dict:
    return {
        "id": event.id, "action": event.action, "resource_type": event.resource_type,
        "resource_id": event.resource_id, "workspace_id": event.workspace_id,
        "actor_user_id": event.actor_user_id, "outcome": event.outcome,
        "request_id": event.request_id, "metadata": json.loads(event.metadata_json),
        "previous_hash": event.previous_hash, "event_hash": event.event_hash,
        "created_at": _timestamp(event.created_at),
    }
