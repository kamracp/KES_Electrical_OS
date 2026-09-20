"""Unit tests for the identity and access settings (EOS-01 a)."""

import pytest
from pydantic import ValidationError

from app.core.config import Settings

pytestmark = pytest.mark.unit


def make(**overrides: object) -> Settings:
    # _env_file=None: the test must not depend on a developer's backend/.env.
    return Settings(_env_file=None, **overrides)  # type: ignore[arg-type]


def test_defaults_are_the_decided_values() -> None:
    settings = make()

    assert settings.SESSION_COOKIE_NAME == "keos_session"
    assert settings.SESSION_IDLE_TIMEOUT_MINUTES == 720
    assert settings.SESSION_ABSOLUTE_LIFETIME_HOURS == 168
    assert settings.LOGIN_MAX_FAILED_ATTEMPTS == 5
    assert settings.LOGIN_LOCKOUT_MINUTES == 15
    assert settings.SESSION_COOKIE_SECURE is None


@pytest.mark.parametrize(
    ("environment", "secure"),
    [("development", False), ("testing", False), ("staging", True), ("production", True)],
)
def test_cookie_is_secure_except_on_plain_http_environments(environment: str, secure: bool) -> None:
    assert make(ENVIRONMENT=environment).session_cookie_secure is secure


def test_an_explicit_value_wins_outside_production() -> None:
    assert make(ENVIRONMENT="development", SESSION_COOKIE_SECURE=True).session_cookie_secure is True


def test_production_refuses_an_insecure_session_cookie() -> None:
    with pytest.raises(ValidationError, match="must be secure in production"):
        make(ENVIRONMENT="production", SESSION_COOKIE_SECURE=False)


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("LOGIN_MAX_FAILED_ATTEMPTS", 1),
        ("SESSION_IDLE_TIMEOUT_MINUTES", 1),
        ("SESSION_COOKIE_NAME", "bad name"),
    ],
)
def test_out_of_range_values_are_rejected(name: str, value: object) -> None:
    with pytest.raises(ValidationError):
        make(**{name: value})


def test_the_cookie_name_gets_the_host_prefix_whenever_the_cookie_is_secure() -> None:
    assert Settings(_env_file=None, SESSION_COOKIE_SECURE=True).session_cookie_name == (
        "__Host-keos_session"
    )
    assert Settings(_env_file=None, SESSION_COOKIE_SECURE=False).session_cookie_name == (
        "keos_session"
    )


def test_plain_http_development_keeps_the_plain_cookie_name() -> None:
    development = Settings(_env_file=None, ENVIRONMENT="development")

    assert development.session_cookie_secure is False
    assert development.session_cookie_name == "keos_session"


def test_a_name_that_already_has_the_prefix_is_not_prefixed_twice() -> None:
    configured = Settings(
        _env_file=None, SESSION_COOKIE_SECURE=True, SESSION_COOKIE_NAME="__Host-custom"
    )

    assert configured.session_cookie_name == "__Host-custom"
