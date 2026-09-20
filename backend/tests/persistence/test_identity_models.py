"""Persistence tests for the identity and access models (EOS-01 a)."""

from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.core.security import generate_session_token, hash_password, hash_session_token
from app.models.identity import (
    AuthEvent,
    AuthEventType,
    Organization,
    OrganizationMembership,
    OrganizationRole,
    User,
    UserSession,
)

pytestmark = pytest.mark.persistence


@pytest_asyncio.fixture
async def session(test_engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    factory = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as db:
        yield db


def make_user(email: str = "owner@example.com") -> User:
    return User(
        email=email,
        full_name="Test Owner",
        password_hash=hash_password("correct horse battery staple"),
    )


async def add_organization_and_user(db: AsyncSession) -> tuple[Organization, User]:
    organization = Organization(code="KES", name="Kamra Engineering Solutions")
    user = make_user()
    db.add_all([organization, user])
    await db.commit()
    return organization, user


async def test_new_rows_get_safe_defaults(session: AsyncSession) -> None:
    organization, user = await add_organization_and_user(session)
    await session.refresh(user)

    assert organization.is_active is True
    assert user.is_active is True
    assert user.must_change_password is False
    assert user.failed_login_count == 0
    assert user.locked_until is None
    assert user.created_at is not None
    assert user.password_hash.startswith("$argon2id$")


async def test_email_is_unique(session: AsyncSession) -> None:
    await add_organization_and_user(session)
    session.add(make_user())

    with pytest.raises(IntegrityError):
        await session.commit()


async def test_email_must_be_lower_case_in_the_database(session: AsyncSession) -> None:
    session.add(make_user("Owner@Example.com"))

    with pytest.raises(IntegrityError):
        await session.commit()


async def test_a_user_has_one_membership_per_organization(session: AsyncSession) -> None:
    organization, user = await add_organization_and_user(session)
    session.add(
        OrganizationMembership(
            organization_id=organization.id, user_id=user.id, role=OrganizationRole.OWNER
        )
    )
    await session.commit()

    session.add(
        OrganizationMembership(
            organization_id=organization.id, user_id=user.id, role=OrganizationRole.VIEWER
        )
    )
    with pytest.raises(IntegrityError):
        await session.commit()


async def test_an_unknown_role_is_rejected(session: AsyncSession) -> None:
    organization, user = await add_organization_and_user(session)
    session.add(
        OrganizationMembership(organization_id=organization.id, user_id=user.id, role="ADMIN")
    )

    with pytest.raises(IntegrityError):
        await session.commit()


async def test_a_session_stores_only_a_unique_sha256_of_the_token(session: AsyncSession) -> None:
    organization, user = await add_organization_and_user(session)
    # Plain values: a rollback expires the ORM objects, and reading user.id afterwards would
    # need database IO outside an await (sqlalchemy MissingGreenlet).
    user_id, organization_id = user.id, organization.id
    token = generate_session_token()
    expires_at = datetime.now(UTC) + timedelta(hours=12)

    def make_session(token_hash: str) -> UserSession:
        return UserSession(
            user_id=user_id,
            organization_id=organization_id,
            token_hash=token_hash,
            expires_at=expires_at,
        )

    first = make_session(hash_session_token(token))
    session.add(first)
    await session.commit()
    await session.refresh(first)

    assert first.token_hash != token
    assert first.revoked_at is None
    assert first.last_seen_at is not None

    session.add(make_session(hash_session_token(token)))
    with pytest.raises(IntegrityError):
        await session.commit()
    await session.rollback()

    session.add(make_session("a" * 63))
    with pytest.raises(IntegrityError):
        await session.commit()


async def test_an_auth_event_may_have_no_user_but_needs_a_known_type(
    session: AsyncSession,
) -> None:
    session.add(
        AuthEvent(event_type=AuthEventType.LOGIN_FAILED, email_attempted="nobody@example.com")
    )
    await session.commit()

    session.add(AuthEvent(event_type="SOMETHING_ELSE"))
    with pytest.raises(IntegrityError):
        await session.commit()


def test_role_and_event_lists_are_the_agreed_ones() -> None:
    assert [role.value for role in OrganizationRole] == ["OWNER", "ENGINEER", "VIEWER"]
    assert "LOGIN_LOCKED" in {event.value for event in AuthEventType}
    assert len(AuthEventType) == 8
