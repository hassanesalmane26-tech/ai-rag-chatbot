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

    model_config = SettingsConfigDict(extra="ignore", populate_by_name=True)

    @model_validator(mode="after")
    def validate_runtime_safety(self):
        if not self.database_url.strip():
            raise ValueError("TRIDENT_DATABASE_URL (or legacy DATABASE_URL) is required")
        if self.environment == "production" and self.debug:
            raise ValueError("Debug mode is forbidden in production")
        self.log_level = self.log_level.upper()
        if self.log_level not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise ValueError("TRIDENT_LOG_LEVEL is invalid")
        return self

    def openai_key(self) -> str:
        """Return the provider key only at the provider boundary."""
        return self.openai_api_key.get_secret_value()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    environment = os.getenv("TRIDENT_ENV", os.getenv("ENVIRONMENT", "development"))
    env_file = None if environment in {"staging", "production"} else ".env"
    return Settings(_env_file=env_file)


settings = get_settings()
