"""Typed runtime configuration with legacy VPS environment compatibility."""

import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import AliasChoices, Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    environment: Literal["development", "test", "staging", "production"] = Field(
        default="development",
        validation_alias=AliasChoices("TRIDENT_ENV", "ENVIRONMENT"),
    )
    app_name: str = Field(
        default="TRIDENT GENESIS",
        validation_alias=AliasChoices("TRIDENT_APP_NAME", "APP_NAME"),
    )
    app_version: str = Field(
        default="0.3.0",
        validation_alias=AliasChoices("TRIDENT_APP_VERSION", "APP_VERSION"),
    )
    build_sha: str = Field(
        default="development",
        validation_alias=AliasChoices("TRIDENT_BUILD_SHA", "BUILD_SHA"),
    )
    debug: bool = Field(
        default=False,
        validation_alias=AliasChoices("TRIDENT_DEBUG", "DEBUG"),
    )
    log_level: str = Field(
        default="INFO",
        validation_alias=AliasChoices("TRIDENT_LOG_LEVEL", "LOG_LEVEL"),
    )
    database_url: str = Field(
        validation_alias=AliasChoices("TRIDENT_DATABASE_URL", "DATABASE_URL"),
    )
    openai_api_key: SecretStr = Field(
        default=SecretStr(""),
        validation_alias=AliasChoices("TRIDENT_OPENAI_API_KEY", "OPENAI_API_KEY"),
    )
    openai_chat_model: str = Field(
        default="gpt-4.1-mini",
        validation_alias=AliasChoices("TRIDENT_OPENAI_CHAT_MODEL", "OPENAI_CHAT_MODEL"),
    )
    openai_embedding_model: str = Field(
        default="text-embedding-3-small",
        validation_alias=AliasChoices("TRIDENT_OPENAI_EMBEDDING_MODEL", "OPENAI_EMBEDDING_MODEL"),
    )
    provider_timeout_seconds: float = Field(
        default=60.0,
        gt=0,
        le=300,
        validation_alias=AliasChoices("TRIDENT_PROVIDER_TIMEOUT_SECONDS", "PROVIDER_TIMEOUT_SECONDS"),
    )
    documents_path: Path = Field(
        default=Path("documents/workspaces"),
        validation_alias=AliasChoices("TRIDENT_DOCUMENTS_PATH", "DOCUMENTS_PATH"),
    )
    vector_db_path: Path = Field(
        default=Path("vector_db"),
        validation_alias=AliasChoices("TRIDENT_VECTOR_DB_PATH", "VECTOR_DB_PATH"),
    )
    security_mode: Literal["disabled", "oidc"] = Field(
        default="disabled",
        validation_alias=AliasChoices("TRIDENT_SECURITY_MODE", "SECURITY_MODE"),
    )
    oidc_issuer: str = Field(
        default="",
        validation_alias=AliasChoices("TRIDENT_OIDC_ISSUER", "OIDC_ISSUER"),
    )
    oidc_audience: str = Field(
        default="",
        validation_alias=AliasChoices("TRIDENT_OIDC_AUDIENCE", "OIDC_AUDIENCE"),
    )
    oidc_jwks_url: str = Field(
        default="",
        validation_alias=AliasChoices("TRIDENT_OIDC_JWKS_URL", "OIDC_JWKS_URL"),
    )
    oidc_allowed_algorithms: str = Field(
        default="RS256",
        validation_alias=AliasChoices(
            "TRIDENT_OIDC_ALLOWED_ALGORITHMS", "OIDC_ALLOWED_ALGORITHMS"
        ),
    )
    oidc_clock_skew_seconds: int = Field(
        default=30,
        ge=0,
        le=300,
        validation_alias=AliasChoices("TRIDENT_OIDC_CLOCK_SKEW_SECONDS", "OIDC_CLOCK_SKEW_SECONDS"),
    )
    oidc_http_timeout_seconds: float = Field(
        default=5.0,
        gt=0,
        le=30,
        validation_alias=AliasChoices("TRIDENT_OIDC_HTTP_TIMEOUT_SECONDS", "OIDC_HTTP_TIMEOUT_SECONDS"),
    )
    cors_allowed_origins: str = Field(
        default="",
        validation_alias=AliasChoices("TRIDENT_CORS_ALLOWED_ORIGINS", "CORS_ALLOWED_ORIGINS"),
    )

    model_config = SettingsConfigDict(extra="ignore", populate_by_name=True)

    @model_validator(mode="after")
    def validate_runtime_safety(self):
        if not self.database_url.strip():
            raise ValueError("TRIDENT_DATABASE_URL (or legacy DATABASE_URL) is required")
        if self.environment == "production" and self.debug:
            raise ValueError("Debug mode is forbidden in production")
        if self.environment in {"staging", "production"} and self.security_mode != "oidc":
            raise ValueError("OIDC security mode is required outside development/test")
        if self.security_mode == "oidc":
            if not self.oidc_issuer.strip() or not self.oidc_audience.strip():
                raise ValueError("OIDC issuer and audience are required in OIDC mode")
            if not self.oidc_issuer.startswith("https://"):
                raise ValueError("OIDC issuer must use HTTPS")
        algorithms = self.allowed_oidc_algorithms()
        supported = {"RS256", "RS384", "RS512", "PS256", "PS384", "PS512", "ES256", "ES384", "ES512"}
        if not algorithms or any(algorithm not in supported for algorithm in algorithms):
            raise ValueError("OIDC algorithms must be an explicit asymmetric allowlist")
        if "*" in self.allowed_cors_origins():
            raise ValueError("Wildcard CORS origins are forbidden")
        self.log_level = self.log_level.upper()
        if self.log_level not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise ValueError("TRIDENT_LOG_LEVEL is invalid")
        return self

    def allowed_oidc_algorithms(self) -> tuple[str, ...]:
        return tuple(item.strip().upper() for item in self.oidc_allowed_algorithms.split(",") if item.strip())

    def allowed_cors_origins(self) -> tuple[str, ...]:
        return tuple(item.strip().rstrip("/") for item in self.cors_allowed_origins.split(",") if item.strip())

    def openai_key(self) -> str:
        """Return the provider key only at the provider boundary."""
        return self.openai_api_key.get_secret_value()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    environment = os.getenv("TRIDENT_ENV", os.getenv("ENVIRONMENT", "development"))
    env_file = None if environment in {"staging", "production"} else ".env"
    return Settings(_env_file=env_file)


settings = get_settings()
