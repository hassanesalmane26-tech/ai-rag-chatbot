"""Public OIDC entry endpoints and authenticated opaque-session lifecycle."""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.errors import AuthenticationConfigurationError, AuthenticationError, AuthorizationError
from app.database.database import get_db
from app.identity.contracts import AuthenticatedPrincipal, InvalidIdentityCredential
from app.identity.service import resolve_or_create_principal
from app.governance.audit import append_audit_event
from app.identity.session_service import (
    CSRF_COOKIE,
    SESSION_COOKIE,
    TRANSACTION_COOKIE,
    available_context,
    begin_login,
    complete_login,
    consume_login,
    create_session,
    select_context,
    utcnow,
)
from app.security.dependencies import require_principal
from app.tenancy.service import TenantAccessDenied, onboard_personal_tenant

router = APIRouter(prefix="/v1/session", tags=["Session"])


class LoginInput(BaseModel):
    return_to: str = Field(default="/", max_length=512)


class ContextInput(BaseModel):
    organization_id: str = Field(min_length=36, max_length=36)
    workspace_id: str | None = Field(default=None, min_length=36, max_length=36)


def cookie_options(request: Request) -> dict:
    configured = request.app.state.runtime_settings
    return {
        "secure": configured.session_cookie_secure,
        "httponly": True,
        "samesite": "lax",
        "path": "/",
    }


def session_payload(request: Request, db: Session, principal: AuthenticatedPrincipal) -> dict:
    application_session = getattr(request.state, "application_session", None)
    organizations = available_context(db, principal)
    organization_ids = {item["id"] for item in organizations}
    active_organization_id = getattr(application_session, "active_organization_id", None)
    if active_organization_id not in organization_ids:
        active_organization_id = None
    workspace_ids = {
        workspace["id"]
        for organization in organizations
        if organization["id"] == active_organization_id
        for workspace in organization["workspaces"]
    }
    active_workspace_id = getattr(application_session, "active_workspace_id", None)
    if active_workspace_id not in workspace_ids:
        active_workspace_id = None
    return {
        "data": {
            "authenticated": True,
            "user": {"id": principal.user_id},
            "organizations": organizations,
            "active_organization_id": active_organization_id,
            "active_workspace_id": active_workspace_id,
            "expires_at": (
                application_session.expires_at.isoformat() if application_session else None
            ),
        },
        "meta": {},
    }


@router.get("/configuration")
def session_configuration(request: Request):
    configured = request.app.state.runtime_settings
    return {
        "data": {
            "enabled": configured.interactive_session_enabled,
            "provider": "oidc" if configured.interactive_session_enabled else None,
        },
        "meta": {},
    }


@router.post("/login")
def start_login(
    payload: LoginInput, request: Request, db: Session = Depends(get_db)
):
    configured = request.app.state.runtime_settings
    client = request.app.state.authorization_code_client
    if not configured.interactive_session_enabled or client is None:
        raise AuthenticationConfigurationError()
    started = begin_login(db, configured.login_transaction_ttl_seconds, payload.return_to)
    try:
        authorization_url = client.authorization_url(
            started.state, started.nonce, started.challenge
        )
    except InvalidIdentityCredential as exc:
        raise AuthenticationConfigurationError() from exc
    response = JSONResponse(
        status_code=201,
        content={"data": {"authorization_url": authorization_url}, "meta": {}},
    )
    response.set_cookie(
        TRANSACTION_COOKIE,
        started.transaction.id,
        max_age=configured.login_transaction_ttl_seconds,
        **cookie_options(request),
    )
    return response


@router.get("/callback")
async def oidc_callback(
    request: Request,
    code: str = "",
    state: str = "",
    error: str = "",
    db: Session = Depends(get_db),
):
    configured = request.app.state.runtime_settings
    client = request.app.state.authorization_code_client
    transaction_id = request.cookies.get(TRANSACTION_COOKIE, "")
    if error or not code or not state or not transaction_id or client is None:
        raise AuthenticationError("OIDC_CALLBACK_REJECTED")
    try:
        transaction, verifier = consume_login(db, transaction_id, state)
        token_response = await client.exchange(code, verifier)
        identity = await request.app.state.id_token_verifier.verify_id_token(
            token_response["id_token"], transaction.nonce
        )
        principal = resolve_or_create_principal(db, identity)
        complete_login(transaction)
        application_session, token, csrf = create_session(
            db, principal, configured.session_ttl_seconds
        )
        onboarding = onboard_personal_tenant(db, principal)
        if onboarding is not None:
            application_session.active_organization_id = onboarding.organization.id
            application_session.active_workspace_id = onboarding.workspace.id
        if onboarding is not None and onboarding.created:
            append_audit_event(
                db,
                action="organization.personal_onboarded",
                resource_type="organization",
                resource_id=onboarding.organization.id,
                principal=principal,
                organization_id=onboarding.organization.id,
                workspace_id=onboarding.workspace.id,
                request_id=request.state.request_id,
            )
        append_audit_event(
            db, action="session.created", resource_type="session",
            resource_id=application_session.id, principal=principal,
            request_id=request.state.request_id,
        )
        db.commit()
    except (ValueError, InvalidIdentityCredential, TenantAccessDenied) as exc:
        db.rollback()
        raise AuthenticationError("OIDC_CALLBACK_REJECTED") from exc
    response = RedirectResponse(transaction.return_to, status_code=303)
    response.delete_cookie(TRANSACTION_COOKIE, path="/")
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=configured.session_ttl_seconds,
        **cookie_options(request),
    )
    response.set_cookie(
        CSRF_COOKIE,
        csrf,
        max_age=configured.session_ttl_seconds,
        secure=configured.session_cookie_secure,
        httponly=False,
        samesite="strict",
        path="/",
    )
    return response


@router.get("")
def current_session(
    request: Request,
    db: Session = Depends(get_db),
    principal: AuthenticatedPrincipal = Depends(require_principal),
):
    return session_payload(request, db, principal)


@router.post("/onboarding")
def onboard_current_user(
    request: Request,
    db: Session = Depends(get_db),
    principal: AuthenticatedPrincipal = Depends(require_principal),
):
    """Recover an authenticated user who has not yet received a tenant."""
    application_session = getattr(request.state, "application_session", None)
    if application_session is None:
        raise AuthorizationError("Une session navigateur est requise.")
    try:
        onboarding = onboard_personal_tenant(db, principal)
    except TenantAccessDenied as exc:
        raise AuthorizationError() from exc
    if onboarding is not None:
        application_session.active_organization_id = onboarding.organization.id
        application_session.active_workspace_id = onboarding.workspace.id
    if onboarding is not None and onboarding.created:
        append_audit_event(
            db,
            action="organization.personal_onboarded",
            resource_type="organization",
            resource_id=onboarding.organization.id,
            principal=principal,
            organization_id=onboarding.organization.id,
            workspace_id=onboarding.workspace.id,
            request_id=request.state.request_id,
        )
    db.commit()
    return session_payload(request, db, principal)


@router.post("/context")
def update_context(
    payload: ContextInput,
    request: Request,
    db: Session = Depends(get_db),
    principal: AuthenticatedPrincipal = Depends(require_principal),
):
    application_session = getattr(request.state, "application_session", None)
    if application_session is None:
        raise AuthorizationError("Une session navigateur est requise.")
    try:
        select_context(
            db,
            application_session,
            principal,
            payload.organization_id,
            payload.workspace_id,
        )
    except ValueError as exc:
        raise AuthorizationError() from exc
    append_audit_event(
        db, action="session.context_selected", resource_type="session",
        resource_id=application_session.id, principal=principal,
        organization_id=payload.organization_id, workspace_id=payload.workspace_id,
        request_id=request.state.request_id,
    )
    db.commit()
    return session_payload(request, db, principal)


@router.post("/logout")
def logout(
    request: Request,
    db: Session = Depends(get_db),
    principal: AuthenticatedPrincipal = Depends(require_principal),
):
    application_session = getattr(request.state, "application_session", None)
    if application_session:
        application_session.revoked_at = utcnow()
        append_audit_event(
            db, action="session.revoked", resource_type="session",
            resource_id=application_session.id, principal=principal,
            organization_id=application_session.active_organization_id,
            workspace_id=application_session.active_workspace_id,
            request_id=request.state.request_id,
        )
        db.commit()
    client = request.app.state.authorization_code_client
    try:
        logout_url = (
            client.logout_url(request.app.state.runtime_settings.oidc_post_logout_redirect_uri)
            if client else None
        )
    except InvalidIdentityCredential:
        logout_url = None
    response = JSONResponse(
        content={"data": {"logged_out": True, "end_session_url": logout_url}, "meta": {}}
    )
    response.delete_cookie(SESSION_COOKIE, path="/")
    response.delete_cookie(CSRF_COOKIE, path="/")
    return response
