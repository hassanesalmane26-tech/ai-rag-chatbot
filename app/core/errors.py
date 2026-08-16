"""Stable public API errors and safe internal exception mapping."""

from dataclasses import dataclass


@dataclass(slots=True)
class APIError(Exception):
    code: str
    message: str
    status_code: int = 400

    def __post_init__(self):
        Exception.__init__(self, self.message)


class ConflictError(APIError):
    def __init__(self, message: str = "La ressource entre en conflit avec l’état actuel."):
        APIError.__init__(self, code="RESOURCE_CONFLICT", message=message, status_code=409)


class BusinessRuleError(APIError):
    def __init__(self, message: str, code: str = "BUSINESS_RULE_VIOLATION"):
        APIError.__init__(self, code=code, message=message, status_code=422)


class AuthenticationError(APIError):
    def __init__(self, code: str = "INVALID_TOKEN", message: str = "Authentification requise."):
        APIError.__init__(self, code=code, message=message, status_code=401)


class AuthenticationConfigurationError(APIError):
    def __init__(self):
        APIError.__init__(
            self,
            code="AUTHENTICATION_UNAVAILABLE",
            message="L’authentification TRIDENT n’est pas configurée.",
            status_code=503,
        )


class AuthorizationError(APIError):
    def __init__(self, message: str = "Accès refusé."):
        APIError.__init__(self, code="ACCESS_DENIED", message=message, status_code=403)


class QuotaExceededError(APIError):
    def __init__(self, metric: str, limit: int):
        APIError.__init__(
            self, code="QUOTA_EXCEEDED",
            message=f"Le quota {metric} ({limit}) est atteint.", status_code=429,
        )
