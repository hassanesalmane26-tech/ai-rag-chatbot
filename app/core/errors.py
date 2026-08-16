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
