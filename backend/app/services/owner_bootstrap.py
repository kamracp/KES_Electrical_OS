"""
First owner and owner recovery, for the server command only (EOS-01 a).

Owners create all other users, but nobody can create the first owner through the API, and an
organization whose only owner lost the password cannot help itself either. Both cases are
settled by a person with shell access to the server, which is the root of trust of the
installation anyway. Nothing here is reachable over HTTP.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal

from pydantic import ValidationError

from app.core.security import PasswordPolicyError, hash_password, validate_password_policy
from app.models.identity import (
    AuthEvent,
    AuthEventType,
    Organization,
    OrganizationMembership,
    OrganizationRole,
    User,
)
from app.repositories.identity import IdentityRepository
from app.schemas.identity import UserCreateRequest

ORGANIZATION_CODE_MAX_LENGTH = 40
ORGANIZATION_NAME_MAX_LENGTH = 200


class OwnerBootstrapError(Exception):
    """The request was refused; the message is meant for the person at the terminal."""


@dataclass(frozen=True)
class OwnerBootstrapResult:
    action: Literal["created", "recovered"]
    email: str
    organization_code: str
    organization_created: bool


def _clean(value: str, label: str, max_length: int) -> str:
    cleaned = " ".join(value.split())
    if not cleaned:
        raise OwnerBootstrapError(f"{label} is required.")
    if len(cleaned) > max_length:
        raise OwnerBootstrapError(f"{label} must have at most {max_length} characters.")
    return cleaned


class OwnerBootstrapService:
    """Create the first owner of an organization, or give an existing user owner access back."""

    def __init__(
        self,
        repository: IdentityRepository,
        *,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self.repository = repository
        self._now = now or (lambda: datetime.now(UTC))

    async def create_owner(
        self,
        *,
        organization_code: str,
        organization_name: str,
        email: str,
        full_name: str,
        password: str,
    ) -> OwnerBootstrapResult:
        code = _clean(organization_code, "Organization code", ORGANIZATION_CODE_MAX_LENGTH)
        try:
            person = UserCreateRequest(
                email=email, full_name=full_name, role=OrganizationRole.OWNER, password=password
            )
            validate_password_policy(password, email=person.email)
        except ValidationError as exc:
            raise OwnerBootstrapError(str(exc.errors()[0]["msg"])) from exc
        except PasswordPolicyError as exc:
            raise OwnerBootstrapError(str(exc)) from exc

        if await self.repository.get_user_by_email(person.email) is not None:
            raise OwnerBootstrapError(
                "A user with this e-mail already exists. To regain access, run the command "
                "again with --recover."
            )

        now = self._now()
        organization = await self.repository.get_organization_by_code(code)
        organization_created = organization is None
        if organization is None:
            name = _clean(organization_name, "Organization name", ORGANIZATION_NAME_MAX_LENGTH)
            organization = Organization(code=code, name=name)
            self.repository.add(organization)

        user = User(
            email=person.email,
            full_name=person.full_name,
            password_hash=hash_password(password),
            must_change_password=False,
            password_changed_at=now,
        )
        self.repository.add(user)
        await self.repository.flush()
        self.repository.add(
            OrganizationMembership(
                organization_id=organization.id,
                user_id=user.id,
                role=OrganizationRole.OWNER.value,
            ),
            self._event(
                AuthEventType.USER_CREATED, now, user, organization, "owner created by the server"
            ),
        )
        await self.repository.commit()
        return OwnerBootstrapResult("created", person.email, code, organization_created)

    async def recover_owner(
        self,
        *,
        organization_code: str,
        email: str,
        password: str,
    ) -> OwnerBootstrapResult:
        code = _clean(organization_code, "Organization code", ORGANIZATION_CODE_MAX_LENGTH)
        organization = await self.repository.get_organization_by_code(code)
        user = await self.repository.get_user_by_email(email)
        if organization is None or user is None:
            raise OwnerBootstrapError(
                "Recovery needs an existing organization code and an existing user e-mail."
            )
        try:
            validate_password_policy(password, email=user.email)
        except PasswordPolicyError as exc:
            raise OwnerBootstrapError(str(exc)) from exc

        now = self._now()
        membership = await self.repository.get_membership(user.id, organization.id)
        if membership is None:
            self.repository.add(
                OrganizationMembership(
                    organization_id=organization.id,
                    user_id=user.id,
                    role=OrganizationRole.OWNER.value,
                )
            )
        else:
            membership.role = OrganizationRole.OWNER.value
            membership.is_active = True

        organization.is_active = True
        user.is_active = True
        user.failed_login_count = 0
        user.locked_until = None
        user.password_hash = hash_password(password)
        user.password_changed_at = now
        user.must_change_password = False
        await self.repository.revoke_sessions_of_user(user.id, revoked_at=now)
        self.repository.add(
            self._event(
                AuthEventType.PASSWORD_RESET,
                now,
                user,
                organization,
                "owner access recovered by the server",
            )
        )
        await self.repository.commit()
        return OwnerBootstrapResult("recovered", user.email, code, False)

    def _event(
        self,
        event_type: AuthEventType,
        occurred_at: datetime,
        user: User,
        organization: Organization,
        detail: str,
    ) -> AuthEvent:
        return AuthEvent(
            event_type=event_type,
            user_id=user.id,
            organization_id=organization.id,
            detail=f"{detail} command",
            occurred_at=occurred_at,
        )


__all__ = [
    "OwnerBootstrapError",
    "OwnerBootstrapResult",
    "OwnerBootstrapService",
]
