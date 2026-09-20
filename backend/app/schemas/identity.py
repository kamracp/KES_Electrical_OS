"""
Request and response schemas for identity and access (EOS-01 a).

Requests refuse unknown fields. Passwords travel as SecretStr, so a request object that ends up
in a log line or an error report shows ******** instead of the password, and they are never
trimmed or altered. The password policy itself lives in app.core.security and is applied by the
services, which give one readable message. Response schemas list their fields one by one: a
password hash or a session token hash cannot leave through them.
"""

import re
from datetime import datetime
from typing import Annotated, Self
from uuid import UUID

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, SecretStr, model_validator

from app.models.identity import AuthEventType, OrganizationRole

EMAIL_MAX_LENGTH = 254
NAME_MAX_LENGTH = 200
# Far above the policy maximum: it only keeps absurd request bodies away from the services.
PASSWORD_INPUT_MAX_LENGTH = 1024

_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _normalize_email(value: str) -> str:
    cleaned = value.strip().lower()
    if not cleaned:
        raise ValueError("E-mail is required.")
    if len(cleaned) > EMAIL_MAX_LENGTH:
        raise ValueError(f"E-mail must have at most {EMAIL_MAX_LENGTH} characters.")
    return cleaned


def _validate_new_email(value: str) -> str:
    cleaned = _normalize_email(value)
    if _EMAIL_PATTERN.fullmatch(cleaned) is None:
        raise ValueError("Enter a valid e-mail address, for example name@company.com.")
    return cleaned


def _clean_name(value: str) -> str:
    cleaned = " ".join(value.split())
    if not cleaned:
        raise ValueError("Name is required.")
    if len(cleaned) > NAME_MAX_LENGTH:
        raise ValueError(f"Name must have at most {NAME_MAX_LENGTH} characters.")
    return cleaned


# At sign-in the e-mail is only normalised: a badly formed one gets the same "sign-in failed"
# answer from the service as any unknown e-mail.
LoginEmail = Annotated[str, Field(max_length=320), AfterValidator(_normalize_email)]
NewEmail = Annotated[str, Field(max_length=320), AfterValidator(_validate_new_email)]
PersonName = Annotated[str, Field(max_length=400), AfterValidator(_clean_name)]
PasswordInput = Annotated[SecretStr, Field(min_length=1, max_length=PASSWORD_INPUT_MAX_LENGTH)]


class _Request(BaseModel):
    model_config = ConfigDict(extra="forbid")


# -- requests -----------------------------------------------------------------------------


class LoginRequest(_Request):
    email: LoginEmail
    password: PasswordInput


class PasswordChangeRequest(_Request):
    current_password: PasswordInput
    new_password: PasswordInput


class UserCreateRequest(_Request):
    """An owner creates a user with a first password that must be changed at first sign-in."""

    email: NewEmail
    full_name: PersonName
    role: OrganizationRole
    password: PasswordInput
    must_change_password: bool = True


class UserUpdateRequest(_Request):
    """Only the fields that are sent are changed."""

    full_name: PersonName | None = None
    role: OrganizationRole | None = None
    is_active: bool | None = None

    @model_validator(mode="after")
    def _needs_one_change(self) -> Self:
        if self.full_name is None and self.role is None and self.is_active is None:
            raise ValueError("Send at least one of full_name, role or is_active.")
        return self


class PasswordResetRequest(_Request):
    """An owner sets a new first password for a user; the user must change it at sign-in."""

    new_password: PasswordInput


# -- responses ----------------------------------------------------------------------------


class OrganizationSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    name: str


class CurrentUser(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    full_name: str
    must_change_password: bool


class SessionResponse(BaseModel):
    """Who is signed in, where, in which role, and until when."""

    user: CurrentUser
    organization: OrganizationSummary
    role: OrganizationRole
    session_expires_at: datetime
    idle_timeout_minutes: int


class UserResponse(BaseModel):
    """A user as the owner sees it in the user list; the role comes from the membership."""

    id: UUID
    email: str
    full_name: str
    role: OrganizationRole
    is_active: bool
    must_change_password: bool
    locked_until: datetime | None
    last_login_at: datetime | None


class UserListResponse(BaseModel):
    items: list[UserResponse]
    total: int


class AuthEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    event_type: AuthEventType
    user_id: UUID | None
    email_attempted: str | None
    ip_address: str | None
    user_agent: str | None
    detail: str | None
    occurred_at: datetime


class AuthEventListResponse(BaseModel):
    items: list[AuthEventResponse]


__all__ = [
    "AuthEventListResponse",
    "AuthEventResponse",
    "CurrentUser",
    "LoginRequest",
    "OrganizationSummary",
    "PasswordChangeRequest",
    "PasswordResetRequest",
    "SessionResponse",
    "UserCreateRequest",
    "UserListResponse",
    "UserResponse",
    "UserUpdateRequest",
]
