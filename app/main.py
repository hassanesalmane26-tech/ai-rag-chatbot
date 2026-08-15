from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.genesis import router as genesis_router
from app.core.config import settings
from app.database.database import Base, engine
from app.database import genesis_models, models  # Register all metadata before bootstrap.

app = FastAPI(title="TRIDENT GENESIS", version="0.2.0", debug=settings.DEBUG, root_path="/api")

# Genesis bootstrap only. Alembic replaces this lifecycle in the production-foundation phase.
Base.metadata.create_all(bind=engine)


def error_response(status_code: int, code: str, message: str, request: Request) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message, "request_id": request.headers.get("x-request-id")}},
    )


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, _exc: RequestValidationError):
    return error_response(422, "VALIDATION_ERROR", "La requête est invalide.", request)


@app.exception_handler(HTTPException)
async def http_error(request: Request, exc: HTTPException):
    codes = {
        404: "RESOURCE_NOT_FOUND",
        413: "PAYLOAD_TOO_LARGE",
        415: "UNSUPPORTED_MEDIA_TYPE",
        422: "UNPROCESSABLE_ENTITY",
        503: "DEPENDENCY_UNAVAILABLE",
    }
    message = exc.detail if isinstance(exc.detail, str) else "La requête a échoué."
    return error_response(exc.status_code, codes.get(exc.status_code, "REQUEST_FAILED"), message, request)


@app.exception_handler(Exception)
async def unhandled_error(request: Request, _exc: Exception):
    return error_response(500, "INTERNAL_ERROR", "Une erreur interne est survenue.", request)


@app.get("/")
def root():
    return {"status": "online", "application": "TRIDENT GENESIS", "version": "0.2.0"}


@app.get("/health/live")
def health_live():
    return {"status": "ok"}


app.include_router(genesis_router)
