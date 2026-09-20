"""
Repository for identity and access records (EOS-01 a).

Unlike the other repositories, the write methods here only stage changes and the service ends
each operation with one commit(). A failed login raises the user's failure counter, may lock
the account and writes an auth event: these reach the database together or not at all.
"""

from datetime import datetime
from typing import Any, cast
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.identity import (
    AuthEvent,
    Organization,
    OrganizationMembership,
    OrganizationRole,
    User,
    UserSession,
)


def normalize_email(email: str) -> str:
    """The stored form of an e-mail address: trimmed and lower case."""

    return email.strip().lower()


class IdentityRepository:
    """Persistence and retrieval for organizations, users, memberships, sessions and events."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # -- unit of work ---------------------------------------------------------------------

    def add(self, *entities: object) -> None:
        """Stage new records; nothing is written before commit()."""

        self.db.add_all(entities)

    async def flush(self) -> None:
        """Send staged changes so that generated ids are available; still not committed."""

        await self.db.flush()

    async def commit(self) -> None:
        await self.db.commit()

    async def rollback(self) -> None:
        await self.db.rollback()

    async def refresh(self, entity: object) -> None:
        await self.db.refresh(entity)

    # -- users and organizations ----------------------------------------------------------

    async def get_user(self, user_id: UUID) -> User | None:
        return await self.db.get(User, user_id)

    async def get_user_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == normalize_email(email))
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def get_organization(self, organization_id: UUID) -> Organization | None:
        return await self.db.get(Organization, organization_id)

    async def get_organization_by_code(self, code: str) -> Organization | None:
        stmt = select(Organization).where(Organization.code == code.strip())
        return (await self.db.execute(stmt)).scalar_one_or_none()

    # -- memberships ----------------------------------------------------------------------

    async def get_membership(
        self,
        user_id: UUID,
        organization_id: UUID,
    ) -> OrganizationMembership | None:
        stmt = select(OrganizationMembership).where(
            OrganizationMembership.user_id == user_id,
            OrganizationMembership.organization_id == organization_id,
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def list_active_memberships(self, user_id: UUID) -> list[OrganizationMembership]:
        """Active memberships in active organizations, oldest first."""

        stmt = (
            select(OrganizationMembership)
            .join(Organization, Organization.id == OrganizationMembership.organization_id)
            .where(
                OrganizationMembership.user_id == user_id,
                OrganizationMembership.is_active.is_(True),
                Organization.is_active.is_(True),
            )
            .order_by(OrganizationMembership.created_at, OrganizationMembership.id)
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def list_users_of_organization(
        self,
        organization_id: UUID,
    ) -> list[tuple[User, OrganizationMembership]]:
        stmt = (
            select(User, OrganizationMembership)
            .join(OrganizationMembership, OrganizationMembership.user_id == User.id)
            .where(OrganizationMembership.organization_id == organization_id)
            .order_by(User.email)
        )
        return [(row[0], row[1]) for row in (await self.db.execute(stmt)).all()]

    async def count_active_owners(self, organization_id: UUID) -> int:
        """Owners who can actually sign in: active membership and active user."""

        stmt = (
            select(func.count())
            .select_from(OrganizationMembership)
            .join(User, User.id == OrganizationMembership.user_id)
            .where(
                OrganizationMembership.organization_id == organization_id,
                OrganizationMembership.role == OrganizationRole.OWNER,
                OrganizationMembership.is_active.is_(True),
                User.is_active.is_(True),
            )
        )
        return int((await self.db.execute(stmt)).scalar_one())

    # -- sessions -------------------------------------------------------------------------

    async def get_session_by_token_hash(self, token_hash: str) -> UserSession | None:
        """Always the state in the database, never a stale copy from this unit of work."""

        stmt = (
            select(UserSession)
            .where(UserSession.token_hash == token_hash)
            .execution_options(populate_existing=True)
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def revoke_sessions_of_user(
        self,
        user_id: UUID,
        *,
        revoked_at: datetime,
        except_session_id: UUID | None = None,
    ) -> int:
        """Stage the revocation of the user's open sessions; returns how many were open."""

        stmt = update(UserSession).where(
            UserSession.user_id == user_id,
            UserSession.revoked_at.is_(None),
        )
        if except_session_id is not None:
            stmt = stmt.where(UserSession.id != except_session_id)

        result = await self.db.execute(
            stmt.values(revoked_at=revoked_at).execution_options(synchronize_session=False)
        )
        return int(cast(CursorResult[Any], result).rowcount or 0)

    # -- auth events ----------------------------------------------------------------------

    async def list_auth_events(
        self,
        *,
        limit: int = 50,
        user_id: UUID | None = None,
    ) -> list[AuthEvent]:
        stmt = select(AuthEvent)
        if user_id is not None:
            stmt = stmt.where(AuthEvent.user_id == user_id)
        stmt = stmt.order_by(AuthEvent.occurred_at.desc(), AuthEvent.id).limit(limit)
        return list((await self.db.execute(stmt)).scalars().all())


__all__ = ["IdentityRepository", "normalize_email"]
