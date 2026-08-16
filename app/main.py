"""TRIDENT FastAPI application factory and lifecycle."""

import logging
import re
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

from app.api.genesis import router as genesis_router
from app.core.config import Settings, settings
from app.core.errors import APIError
from app.core.logging import configure_logging
from app.database.database import engine

logger = logging.getLogger("trident.api")
REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{8,128}$")


def request_id_for(request: Request) -> str:
    candidate = request.headers.get("x-request-id", "")
    return candidate if REQUEST_ID_PATTERN.fullmatch(candidate) else uuid.uuid4().hex


def error_response(status_code: int, code: str, message: str, request: Request) -> JSONResponse:
    request_id = getattr(request.state, "request_id", request_id_for(request))
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message, "request_id": request_id}},
        headers={"X-Request-ID": request_id},
    )


def create_app(runtime_settings: Settings = settings, database_engine: Engine = engine) -> FastAPI:
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
        lifespan=lifespan,
    )

    @application.middleware("http")
    async def correlate_request(request: Request, call_next):
        request.state.request_id = request_id_for(request)
        started = time.perf_counter()
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
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
        return error_response(exc.status_code, exc.code, exc.message, request)

    @application.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException):
        codes = {
            404: "RESOURCE_NOT_FOUND",
            409: "RESOURCE_CONFLICT",
            413: "PAYLOAD_TOO_LARGE",
            415: "UNSUPPORTED_MEDIA_TYPE",
            422: "UNPROCESSABLE_ENTITY",
            503: "DEPENDENCY_UNAVAILABLE",
        }
        message = exc.detail if isinstance(exc.detail, str) else "La requête a échoué."
        return error_response(exc.status_code, codes.get(exc.status_code, "REQUEST_FAILED"), message, request)

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
            "migration_head": "0001_genesis_baseline",
            "migration_revision": migration_revision,
        }

    application.include_router(genesis_router)
    return application


app = create_app()
