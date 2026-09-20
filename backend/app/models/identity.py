"""
Identity and access models (EOS-01 a): organizations, users, memberships, sessions, auth events.

Passwords are stored only as argon2id hashes and session tokens only as their SHA-256
(app.core.security). Users are deactivated, never deleted, so audit records keep their subject.
Status-like values are text with a CHECK constraint built from the Python enum, as in
calculation_runs, so the database list and the code list cannot drift apart.
"""

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
    false,
    func,
    text,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class OrganizationRole(StrEnum):
    """Role of a user inside one organization."""

    OWNER = "OWNER"
    ENGINEER = "ENGINEER"
    VIEWER = "VIEWER"


class AuthEventType(StrEnum):
    """Security-relevant events kept as an audit trail."""

    LOGIN_SUCCEEDED = "LOGIN_SUCCEEDED"
    LOGIN_FAILED = "LOGIN_FAILED"
    LOGIN_LOCKED = "LOGIN_LOCKED"
    LOGOUT = "LOGOUT"
    USER_CREATED = "USER_CREATED"
    USER_UPDATED = "USER_UPDATED"
    PASSWORD_CHANGED = "PASSWORD_CHANGED"
    PASSWORD_RESET = "PASSWORD_RESET"


def _in_list(column: str, enum: type[StrEnum]) -> str:
    values = ", ".join(f"'{member.value}'" for member in enum)
    return f"{column} IN ({values})"


class Organization(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A company or consultancy that owns users and, later, sites and projects."""

    __tablename__ = "organizations"

    __table_args__ = (CheckConstraint("code <> '' AND name <> ''", name="code_name_not_blank"),)

    code: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=true(), nullable=False
    )


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A person who can sign in. The e-mail is the login name and is stored in lower case."""

    __tablename__ = "users"

    __table_args__ = (
        CheckConstraint("email = lower(email) AND email <> ''", name="email_lower_case"),
        CheckConstraint("failed_login_count >= 0", name="failed_login_count_not_negative"),
    )

    email: Mapped[str] = mapped_column(String(254), unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=true(), nullable=False
    )
    must_change_password: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=false(), nullable=False
    )
    failed_login_count: Mapped[int] = mapped_column(
        Integer, default=0, server_default=text("0"), nullable=False
    )
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    password_changed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class OrganizationMembership(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Links a user to an organization with one role."""

    __tablename__ = "organization_memberships"

    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "user_id",
            name="organization_memberships_organization_user_unique",
        ),
        CheckConstraint(_in_list("role", OrganizationRole), name="role_valid"),
    )

    organization_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=true(), nullable=False
    )


class UserSession(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    One signed-in browser. Only the SHA-256 of the cookie token is stored; logging out sets
    revoked_at, and a session is valid only while it is neither revoked nor expired.
    """

    __tablename__ = "user_sessions"

    __table_args__ = (CheckConstraint("length(token_hash) = 64", name="token_hash_sha256_hex"),)

    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    organization_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(300), nullable=True)


class AuthEvent(UUIDPrimaryKeyMixin, Base):
    """
    Append-only audit record. user_id is empty for a failed login with an unknown e-mail;
    the attempted e-mail is kept so that guessing shows up in the trail.
    """

    __tablename__ = "auth_events"

    __table_args__ = (CheckConstraint(_in_list("event_type", AuthEventType), name="type_valid"),)

    event_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    user_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    organization_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=True,
    )
    email_attempted: Mapped[str | None] = mapped_column(String(254), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(300), nullable=True)
    detail: Mapped[str | None] = mapped_column(String(300), nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )


__all__ = [
    "AuthEvent",
    "AuthEventType",
    "Organization",
    "OrganizationMembership",
    "OrganizationRole",
    "User",
    "UserSession",
]
