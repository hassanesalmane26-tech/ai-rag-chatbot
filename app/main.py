"""TRIDENT FastAPI application factory and lifecycle."""

import logging
import re
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

from app.api.genesis import router as genesis_router
from app.core.config import Settings, settings
from app.core.errors import APIError
from app.core.logging import configure_logging
from app.database.database import engine
from app.database.schema import HEAD_REVISION
from app.identity.contracts import IdentityVerifier, UnavailableIdentityVerifier
from app.identity.authorization_code import AuthorizationCodeClient
from app.identity.oidc import OIDCConfiguration, OIDCIdentityVerifier
from app.identity.session_router import router as session_router
from app.governance.rate_limit import FixedWindowRateLimiter
from app.governance.router import router as governance_router
from app.memory.router import router as memory_router
from app.modules.router import router as modules_router

logger = logging.getLogger("trident.api")
REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{8,128}$")


def request_id_for(request: Request) -> str:
    candidate = request.headers.get("x-request-id", "")
    return candidate if REQUEST_ID_PATTERN.fullmatch(candidate) else uuid.uuid4().hex


def error_response(
    status_code: int,
    code: str,
    message: str,
    request: Request,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", request_id_for(request))
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message, "request_id": request_id}},
        headers={"X-Request-ID": request_id, **(headers or {})},
    )


def create_app(
    runtime_settings: Settings = settings,
    database_engine: Engine = engine,
    identity_verifier: IdentityVerifier | None = None,
) -> FastAPI:
    @asynccontextmanager
    async def lifespan(application: FastAPI):
        configure_logging(runtime_settings.log_level)
        application.state.started_at = time.time()
        logger.info("application_started", extra={"event_name": "application_started"})
        try:
            yield
        finally:
            database_engine.dispose()
            logger.info("application_stopped", extra={"event_name": "application_stopped"})

    application = FastAPI(
        title=runtime_settings.app_name,
        version=runtime_settings.app_version,
        debug=runtime_settings.debug,
        root_path="/api",
        docs_url=None if runtime_settings.environment in {"staging", "production"} else "/docs",
        redoc_url=None if runtime_settings.environment in {"staging", "production"} else "/redoc",
        openapi_url=None if runtime_settings.environment in {"staging", "production"} else "/openapi.json",
        lifespan=lifespan,
    )
    application.state.security_mode = runtime_settings.security_mode
    application.state.runtime_settings = runtime_settings
    application.state.identity_verifier = identity_verifier or (
        OIDCIdentityVerifier(
            OIDCConfiguration(
                issuer=runtime_settings.oidc_issuer,
                audience=runtime_settings.oidc_audience,
                algorithms=runtime_settings.allowed_oidc_algorithms(),
                jwks_url=runtime_settings.oidc_jwks_url,
                clock_skew_seconds=runtime_settings.oidc_clock_skew_seconds,
                http_timeout_seconds=runtime_settings.oidc_http_timeout_seconds,
            )
        )
        if runtime_settings.security_mode == "oidc"
        else UnavailableIdentityVerifier()
    )
    application.state.authorization_code_client = (
        AuthorizationCodeClient(
            issuer=runtime_settings.oidc_issuer,
            client_id=runtime_settings.oidc_client_id,
            redirect_uri=runtime_settings.oidc_redirect_uri,
            scopes=runtime_settings.oidc_scope_values(),
            timeout_seconds=runtime_settings.oidc_http_timeout_seconds,
        )
        if runtime_settings.interactive_session_enabled else None
    )
    application.state.id_token_verifier = (
        OIDCIdentityVerifier(
            OIDCConfiguration(
                issuer=runtime_settings.oidc_issuer,
                audience=runtime_settings.oidc_client_id,
                algorithms=runtime_settings.allowed_oidc_algorithms(),
                jwks_url=runtime_settings.oidc_jwks_url,
                clock_skew_seconds=runtime_settings.oidc_clock_skew_seconds,
                http_timeout_seconds=runtime_settings.oidc_http_timeout_seconds,
            )
        )
        if runtime_settings.interactive_session_enabled else UnavailableIdentityVerifier()
    )
    application.state.rate_limiter = FixedWindowRateLimiter(
        runtime_settings.rate_limit_requests_per_minute
    )

    origins = list(runtime_settings.allowed_cors_origins())
    if origins:
        application.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
            allow_headers=["Authorization", "Content-Type", "X-Request-ID", "X-CSRF-Token"],
            expose_headers=["X-Request-ID", "X-TRIDENT-API-Version", "X-RateLimit-Remaining", "Retry-After"],
        )

    @application.middleware("http")
    async def correlate_request(request: Request, call_next):
        request.state.request_id = request_id_for(request)
        started = time.perf_counter()
        is_health = request.url.path.startswith("/health/")
        client_key = request.client.host if request.client else "unknown"
        allowed, remaining, retry_after = (True, runtime_settings.rate_limit_requests_per_minute, 0)
        if not is_health:
            allowed, remaining, retry_after = application.state.rate_limiter.allow(client_key)
        if not allowed:
            response = error_response(
                429, "RATE_LIMITED", "Trop de requêtes. Réessayez plus tard.", request,
                {"Retry-After": str(retry_after), "X-RateLimit-Remaining": "0"},
            )
            response.headers["X-TRIDENT-API-Version"] = "1"
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["Referrer-Policy"] = "no-referrer"
            return response
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-TRIDENT-API-Version"] = "1"
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        if request.url.path.startswith("/v1/session"):
            response.headers["Cache-Control"] = "no-store"
        logger.info(
            "http_request_completed",
            extra={
                "event_name": "http_request_completed",
                "request_id": request.state.request_id,
                "method": request.method,
                "route": getattr(request.scope.get("route"), "path", "unmatched"),
                "status_code": response.status_code,
                "duration_ms": round((time.perf_counter() - started) * 1000, 2),
            },
        )
        return response

    @application.exception_handler(RequestValidationError)
    async def validation_error(request: Request, _exc: RequestValidationError):
        return error_response(422, "VALIDATION_ERROR", "La requête est invalide.", request)

    @application.exception_handler(APIError)
    async def api_error(request: Request, exc: APIError):
        headers = {"WWW-Authenticate": "Bearer"} if exc.status_code == 401 else None
        return error_response(exc.status_code, exc.code, exc.message, request, headers)

    @application.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException):
        codes = {
            404: "RESOURCE_NOT_FOUND",
            409: "RESOURCE_CONFLICT",
            413: "PAYLOAD_TOO_LARGE",
            415: "UNSUPPORTED_MEDIA_TYPE",
            422: "UNPROCESSABLE_ENTITY",
            401: "AUTHENTICATION_REQUIRED",
            403: "ACCESS_DENIED",
            503: "DEPENDENCY_UNAVAILABLE",
            429: "RATE_LIMITED",
        }
        message = exc.detail if isinstance(exc.detail, str) else "La requête a échoué."
        return error_response(
            exc.status_code,
            codes.get(exc.status_code, "REQUEST_FAILED"),
            message,
            request,
            dict(exc.headers or {}),
        )

    @application.exception_handler(Exception)
    async def unhandled_error(request: Request, exc: Exception):
        logger.exception(
            "unhandled_request_error",
            extra={"event_name": "unhandled_request_error", "request_id": request.state.request_id},
        )
        return error_response(500, "INTERNAL_ERROR", "Une erreur interne est survenue.", request)

    @application.get("/")
    def root():
        return {
            "status": "online",
            "application": runtime_settings.app_name,
            "version": runtime_settings.app_version,
        }

    @application.get("/health/live")
    def health_live():
        return {"status": "ok"}

    @application.get("/health/ready")
    def health_ready():
        try:
            with database_engine.connect() as connection:
                connection.execute(text("SELECT 1"))
        except Exception:
            return JSONResponse(status_code=503, content={"status": "not_ready", "checks": {"database": "unavailable"}})
        return {"status": "ready", "checks": {"database": "ok"}}

    @application.get("/health/build")
    def health_build():
        migration_revision = "unmanaged"
        if inspect(database_engine).has_table("alembic_version"):
            with database_engine.connect() as connection:
                migration_revision = connection.execute(
                    text("SELECT version_num FROM alembic_version LIMIT 1")
                ).scalar_one_or_none() or "unversioned"
        return {
            "service": runtime_settings.app_name,
            "environment": runtime_settings.environment,
            "version": runtime_settings.app_version,
            "build_sha": runtime_settings.build_sha,
            "migration_head": HEAD_REVISION,
            "migration_revision": migration_revision,
            "security_mode": runtime_settings.security_mode,
            "business_api_protected": runtime_settings.security_mode == "oidc",
        }

    application.include_router(session_router)
    application.include_router(governance_router)
    application.include_router(genesis_router)
    application.include_router(memory_router)
    application.include_router(modules_router)
    return application


app = create_app()
