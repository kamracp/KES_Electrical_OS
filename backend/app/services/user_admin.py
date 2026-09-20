"""
User administration by an organization owner (EOS-01 a): list, create, update, reset password.

There is no public sign-up and no deletion: an owner creates users with a first password that
must be changed at the first sign-in, and deactivates them when they leave, so audit records
keep their subject. An owner cannot change the own role or deactivate the own account, which
also guarantees that an organization never loses its last owner through this service. Every
change is stored together with its audit event in one commit.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.exc import IntegrityError

from app.core.security import hash_password, validate_password_policy
from app.models.identity import (
    AuthEvent,
    AuthEventType,
    OrganizationMembership,
    OrganizationRole,
    User,
)
from app.repositories.identity import IdentityRepository, normalize_email
from app.services.auth import AuthenticatedSession, RequestContext


class UserAdminError(Exception):
    """Base class; the message is safe to show to the owner."""


class UserNotFoundError(UserAdminError):
    """No such user in the owner's organization."""


class UserConflictError(UserAdminError):
    """The change contradicts the current state or a rule."""


@dataclass(frozen=True)
class UserRecord:
    """A user together with the membership in the owner's organization."""

    user: User
    membership: OrganizationMembership


class UserAdminService:
    """The actions of an owner on the users of the own organization."""

    def __init__(
        self,
        repository: IdentityRepository,
        *,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self.repository = repository
        self._now = now or (lambda: datetime.now(UTC))

    async def list_users(self, actor: AuthenticatedSession) -> list[UserRecord]:
        rows = await self.repository.list_users_of_organization(actor.organization.id)
        return [UserRecord(user, membership) for user, membership in rows]

    async def list_events(self, *, limit: int = 50) -> list[AuthEvent]:
        return await self.repository.list_auth_events(limit=limit)

    async def create_user(
        self,
        actor: AuthenticatedSession,
        *,
        email: str,
        full_name: str,
        role: OrganizationRole,
        password: str,
        must_change_password: bool = True,
        context: RequestContext | None = None,
    ) -> UserRecord:
        email = normalize_email(email)
        validate_password_policy(password, email=email)
        actor_email = actor.user.email
        organization_id = actor.organization.id

        if await self.repository.get_user_by_email(email) is not None:
            raise UserConflictError("A user with this e-mail already exists.")

        now = self._now()
        user = User(
            email=email,
            full_name=full_name,
            password_hash=hash_password(password),
            must_change_password=must_change_password,
            password_changed_at=now,
        )
        self.repository.add(user)
        try:
            await self.repository.flush()
        except IntegrityError as exc:
            await self.repository.rollback()
            raise UserConflictError("A user with this e-mail already exists.") from exc

        membership = OrganizationMembership(
            organization_id=organization_id,
            user_id=user.id,
            role=role.value,
        )
        self.repository.add(
            membership,
            self._event(
                AuthEventType.USER_CREATED,
                now,
                context,
                user_id=user.id,
                organization_id=organization_id,
                detail=f"created as {role.value} by {actor_email}",
            ),
        )
        await self.repository.commit()
        return UserRecord(user, membership)

    async def update_user(
        self,
        actor: AuthenticatedSession,
        user_id: UUID,
        *,
        full_name: str | None = None,
        role: OrganizationRole | None = None,
        is_active: bool | None = None,
        context: RequestContext | None = None,
    ) -> UserRecord:
        record = await self._member(actor, user_id)
        user, membership = record.user, record.membership
        changes_access = (role is not None and role.value != membership.role) or (
            is_active is not None and is_active != user.is_active
        )
        if user.id == actor.user.id and changes_access:
            raise UserConflictError(
                "You cannot change your own role or deactivate your own account; ask another owner."
            )

        now = self._now()
        changes: list[str] = []
        if full_name is not None and full_name != user.full_name:
            user.full_name = full_name
            changes.append("name changed")
        if role is not None and role.value != membership.role:
            changes.append(f"role {membership.role} -> {role.value}")
            membership.role = role.value
        if is_active is not None and is_active != user.is_active:
            user.is_active = is_active
            if is_active:
                user.failed_login_count = 0
                user.locked_until = None
                changes.append("activated")
            else:
                await self.repository.revoke_sessions_of_user(user.id, revoked_at=now)
                changes.append("deactivated")

        if changes:
            self.repository.add(
                self._event(
                    AuthEventType.USER_UPDATED,
                    now,
                    context,
                    user_id=user.id,
                    organization_id=actor.organization.id,
                    detail=f"{'; '.join(changes)}; by {actor.user.email}",
                )
            )
            await self.repository.commit()
        return record

    async def reset_password(
        self,
        actor: AuthenticatedSession,
        user_id: UUID,
        new_password: str,
        context: RequestContext | None = None,
    ) -> None:
        record = await self._member(actor, user_id)
        user = record.user
        if user.id == actor.user.id:
            raise UserConflictError("Use Change password for your own account.")
        validate_password_policy(new_password, email=user.email)

        now = self._now()
        user.password_hash = hash_password(new_password)
        user.password_changed_at = now
        user.must_change_password = True
        user.failed_login_count = 0
        user.locked_until = None
        await self.repository.revoke_sessions_of_user(user.id, revoked_at=now)
        self.repository.add(
            self._event(
                AuthEventType.PASSWORD_RESET,
                now,
                context,
                user_id=user.id,
                organization_id=actor.organization.id,
                detail=f"reset by {actor.user.email}",
            )
        )
        await self.repository.commit()

    # -- helpers --------------------------------------------------------------------------

    async def _member(self, actor: AuthenticatedSession, user_id: UUID) -> UserRecord:
        user = await self.repository.get_user(user_id)
        membership = (
            await self.repository.get_membership(user_id, actor.organization.id)
            if user is not None
            else None
        )
        if user is None or membership is None:
            raise UserNotFoundError("User not found.")
        return UserRecord(user, membership)

    def _event(
        self,
        event_type: AuthEventType,
        occurred_at: datetime,
        context: RequestContext | None,
        *,
        user_id: UUID,
        organization_id: UUID,
        detail: str,
    ) -> AuthEvent:
        context = context or RequestContext()
        return AuthEvent(
            event_type=event_type,
            user_id=user_id,
            organization_id=organization_id,
            ip_address=(context.ip_address or "")[:45] or None,
            user_agent=(context.user_agent or "")[:300] or None,
            detail=detail[:300],
            occurred_at=occurred_at,
        )


__all__ = [
    "UserAdminError",
    "UserAdminService",
    "UserConflictError",
    "UserNotFoundError",
    "UserRecord",
]
