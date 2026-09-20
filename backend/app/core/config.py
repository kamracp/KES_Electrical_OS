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

    DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@localhost:5432/kes_electrical_os"

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
    # Identity and access (EOS-01 a)
    # ------------------------------------------------------------------

    SESSION_COOKIE_NAME: str = Field(default="keos_session", pattern=r"^[A-Za-z0-9_-]+$")
    SESSION_IDLE_TIMEOUT_MINUTES: int = Field(default=720, ge=5, le=1440)
    SESSION_ABSOLUTE_LIFETIME_HOURS: int = Field(default=168, ge=1, le=720)
    # None = decided by the environment, see session_cookie_secure.
    SESSION_COOKIE_SECURE: bool | None = None

    LOGIN_MAX_FAILED_ATTEMPTS: int = Field(default=5, ge=3, le=20)
    LOGIN_LOCKOUT_MINUTES: int = Field(default=15, ge=1, le=1440)

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

            if self.SESSION_COOKIE_SECURE is False:
                raise ValueError("The session cookie must be secure in production")

        return self

    @property
    def session_cookie_secure(self) -> bool:
        """Secure cookie everywhere except plain-http development and testing."""

        if self.SESSION_COOKIE_SECURE is not None:
            return self.SESSION_COOKIE_SECURE
        return self.ENVIRONMENT not in ("development", "testing")

    @property
    def session_cookie_name(self) -> str:
        """
        The name the browser sees: SESSION_COOKIE_NAME with the __Host- prefix when Secure.

        A browser accepts a __Host- cookie only if it is Secure, has Path=/ and names no Domain,
        and only from the host itself. The sibling products on other sub-domains of the same
        registrable domain can therefore neither set nor overwrite it (no "cookie tossing").
        Plain-http development cannot use the prefix, because it needs Secure; there the plain
        name is kept. Derived here, not typed into a server .env, so every secure environment
        gets it and a test can prove it.
        """

        name = self.SESSION_COOKIE_NAME
        if self.session_cookie_secure and not name.startswith("__Host-"):
            return f"__Host-{name}"
        return name


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
