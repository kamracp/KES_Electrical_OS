"""Unit tests for the identity and access schemas (EOS-01 a)."""

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import pytest
from pydantic import BaseModel, ValidationError

from app.models.identity import AuthEvent, AuthEventType, Organization, OrganizationRole, User
from app.schemas.identity import (
    AuthEventListResponse,
    AuthEventResponse,
    CurrentUser,
    LoginRequest,
    OrganizationSummary,
    PasswordChangeRequest,
    SessionResponse,
    UserCreateRequest,
    UserListResponse,
    UserResponse,
    UserUpdateRequest,
)

pytestmark = pytest.mark.unit

PASSWORD = "correct horse battery staple"
NEW_USER: dict[str, Any] = {
    "email": "engineer@example.com",
    "full_name": "Asha Verma",
    "role": "ENGINEER",
    "password": PASSWORD,
}


def test_login_normalises_the_email_and_hides_the_password() -> None:
    request = LoginRequest(email="  Owner@Example.COM ", password=PASSWORD)

    assert request.email == "owner@example.com"
    assert request.password.get_secret_value() == PASSWORD
    assert PASSWORD not in repr(request)
    assert PASSWORD not in request.model_dump_json()


def test_login_leaves_the_email_format_to_the_service() -> None:
    assert LoginRequest(email="not-an-email", password=PASSWORD).email == "not-an-email"


@pytest.mark.parametrize(
    "payload",
    [
        {"email": "   ", "password": PASSWORD},
        {"email": "owner@example.com", "password": ""},
        {"email": "owner@example.com", "password": "x" * 1025},
        {"email": "owner@example.com", "password": PASSWORD, "remember_me": True},
    ],
    ids=["blank e-mail", "empty password", "oversized password", "unknown field"],
)
def test_login_rejects(payload: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        LoginRequest.model_validate(payload)


def test_passwords_are_never_trimmed() -> None:
    request = PasswordChangeRequest(current_password=" old pass phrase ", new_password="  new  ")

    assert request.current_password.get_secret_value() == " old pass phrase "
    assert request.new_password.get_secret_value() == "  new  "


def test_user_create_normalises_and_asks_for_a_password_change_by_default() -> None:
    request = UserCreateRequest.model_validate(
        {**NEW_USER, "email": " Engineer@Example.com", "full_name": "  Asha   Verma "}
    )

    assert request.email == "engineer@example.com"
    assert request.full_name == "Asha Verma"
    assert request.role is OrganizationRole.ENGINEER
    assert request.must_change_password is True


@pytest.mark.parametrize("email", ["plain", "a@b", "a b@example.com", "@example.com", "a@@b.com"])
def test_user_create_rejects_a_badly_formed_email(email: str) -> None:
    with pytest.raises(ValidationError, match="valid e-mail address"):
        UserCreateRequest.model_validate({**NEW_USER, "email": email})


def test_user_create_rejects_a_blank_name_and_an_unknown_role() -> None:
    with pytest.raises(ValidationError, match="Name is required"):
        UserCreateRequest.model_validate({**NEW_USER, "full_name": "   "})
    with pytest.raises(ValidationError):
        UserCreateRequest.model_validate({**NEW_USER, "role": "ADMIN"})


def test_user_update_needs_at_least_one_change() -> None:
    with pytest.raises(ValidationError, match="at least one"):
        UserUpdateRequest.model_validate({})

    assert UserUpdateRequest(is_active=False).is_active is False
    assert UserUpdateRequest(role="VIEWER").role is OrganizationRole.VIEWER


def test_current_user_is_built_from_the_model_without_the_password_hash() -> None:
    user = User(
        id=uuid4(),
        email="owner@example.com",
        full_name="Test Owner",
        password_hash="$argon2id$never-leaves",
        must_change_password=True,
    )

    dumped = CurrentUser.model_validate(user).model_dump()

    assert set(dumped) == {"id", "email", "full_name", "must_change_password"}
    assert "never-leaves" not in str(dumped)


def test_auth_event_is_built_from_the_model() -> None:
    event = AuthEvent(
        id=uuid4(),
        event_type=AuthEventType.LOGIN_FAILED,
        email_attempted="nobody@example.com",
        occurred_at=datetime(2026, 9, 20, 9, 0, tzinfo=UTC),
    )

    response = AuthEventResponse.model_validate(event)

    assert response.event_type is AuthEventType.LOGIN_FAILED
    assert response.user_id is None
    assert response.email_attempted == "nobody@example.com"


def test_session_response_carries_user_organization_and_role() -> None:
    user = User(id=uuid4(), email="o@example.com", full_name="O", must_change_password=False)
    organization = Organization(id=uuid4(), code="KES", name="Kamra Engineering Solutions")

    response = SessionResponse(
        user=CurrentUser.model_validate(user),
        organization=OrganizationSummary.model_validate(organization),
        role=OrganizationRole.OWNER,
        session_expires_at=datetime(2026, 9, 27, 9, 0, tzinfo=UTC),
        idle_timeout_minutes=720,
    )

    assert response.organization.code == "KES"
    assert response.model_dump(mode="json")["role"] == "OWNER"


@pytest.mark.parametrize(
    "model",
    [
        OrganizationSummary,
        CurrentUser,
        SessionResponse,
        UserResponse,
        UserListResponse,
        AuthEventResponse,
        AuthEventListResponse,
    ],
)
def test_no_response_schema_carries_a_secret(model: type[BaseModel]) -> None:
    for name in model.model_fields:
        assert "hash" not in name
        assert "token" not in name
        assert "password" not in name or name == "must_change_password"
