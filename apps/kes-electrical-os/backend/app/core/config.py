"""
KES Electrical OS
Application Configuration
"""

from functools import lru_cache
from typing import Literal, Self

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

EnvironmentName = Literal["development", "testing", "staging", "production"]
LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="KES_",
        case_sensitive=False,
        extra="ignore",
    )

    # ------------------------------------------------------------------
    # Application
    # ------------------------------------------------------------------

    APP_NAME: str = "KES Electrical OS API"
    APP_VERSION: str = "0.1.0"
    APP_DESCRIPTION: str = "Enterprise Electrical Engineering Platform"

    ENVIRONMENT: EnvironmentName = "development"
    DEBUG: bool = False

    API_V1_PREFIX: str = "/api/v1"

    # ------------------------------------------------------------------
    # Database
    # ------------------------------------------------------------------

    DATABASE_URL: str = (
        "postgresql+psycopg://postgres:postgres@localhost:5432/"
        "kes_electrical_os"
    )

    DATABASE_ECHO: bool = False

    # ------------------------------------------------------------------
    # CORS
    # ------------------------------------------------------------------

    BACKEND_CORS_ORIGINS: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:5173",
        ]
    )

    ALLOWED_HOSTS: list[str] = Field(
        default_factory=lambda: [
            "localhost",
            "127.0.0.1",
        ]
    )

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------

    LOG_LEVEL: LogLevel = "INFO"

    # ------------------------------------------------------------------
    # Validators
    # ------------------------------------------------------------------

    @field_validator("API_V1_PREFIX")
    @classmethod
    def validate_api_prefix(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("API prefix cannot be empty")

        return "/" + value.strip("/")

    @field_validator("BACKEND_CORS_ORIGINS", "ALLOWED_HOSTS")
    @classmethod
    def validate_string_list(cls, values: list[str]) -> list[str]:
        cleaned: list[str] = []

        for value in values:
            item = value.strip().rstrip("/")

            if not item:
                raise ValueError("Configuration values cannot be empty")

            if item not in cleaned:
                cleaned.append(item)

        return cleaned

    @model_validator(mode="after")
    def validate_production(self) -> Self:
        if self.ENVIRONMENT == "production":
            if self.DEBUG:
                raise ValueError("Debug cannot be enabled in production")

            if "*" in self.BACKEND_CORS_ORIGINS:
                raise ValueError("Wildcard CORS is not allowed")

            if "*" in self.ALLOWED_HOSTS:
                raise ValueError("Wildcard hosts are not allowed")

        return self


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()


settings = get_settings()

__all__ = [
    "EnvironmentName",
    "LogLevel",
    "Settings",
    "get_settings",
    "settings",
]