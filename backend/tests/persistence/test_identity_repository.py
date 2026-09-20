"""Persistence tests for IdentityRepository (EOS-01 a)."""

from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.core.security import generate_session_token, hash_session_token
from app.models.identity import (
    AuthEvent,
    AuthEventType,
    Organization,
    OrganizationMembership,
    OrganizationRole,
    User,
    UserSession,
)
from app.repositories.identity import IdentityRepository, normalize_email

pytestmark = pytest.mark.persistence

# The repository never looks inside the hash, so the tests skip the slow argon2 work.
FAKE_HASH = "$argon2id$not-a-real-hash"
NOW = datetime(2026, 9, 20, 12, 0, tzinfo=UTC)


@pytest_asyncio.fixture
async def repo(test_engine: AsyncEngine) -> AsyncIterator[IdentityRepository]:
    factory = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as db:
        yield IdentityRepository(db)


def make_user(email: str, *, active: bool = True) -> User:
    return User(email=email, full_name=email, password_hash=FAKE_HASH, is_active=active)


async def seed(repo: IdentityRepository) -> tuple[Organization, User]:
    organization = Organization(code="KES", name="Kamra Engineering Solutions")
    owner = make_user("owner@example.com")
    repo.add(organization, owner)
    await repo.flush()
    repo.add(
        OrganizationMembership(
            organization_id=organization.id, user_id=owner.id, role=OrganizationRole.OWNER
        )
    )
    await repo.commit()
    return organization, owner


def make_session(organization: Organization, user: User, **values: object) -> UserSession:
    return UserSession(
        user_id=user.id,
        organization_id=organization.id,
        token_hash=hash_session_token(generate_session_token()),
        expires_at=NOW + timedelta(hours=12),
        **values,
    )


def test_normalize_email_trims_and_lower_cases() -> None:
    assert normalize_email("  Owner@Example.COM ") == "owner@example.com"


async def test_staged_writes_are_discarded_by_rollback_and_kept_by_commit(
    repo: IdentityRepository,
) -> None:
    repo.add(make_user("engineer@example.com"))
    await repo.rollback()
    assert await repo.get_user_by_email("engineer@example.com") is None

    repo.add(make_user("engineer@example.com"))
    await repo.commit()
    assert await repo.get_user_by_email("engineer@example.com") is not None


async def test_email_lookup_ignores_case_and_surrounding_spaces(repo: IdentityRepository) -> None:
    _, owner = await seed(repo)

    found = await repo.get_user_by_email("  Owner@Example.COM ")

    assert found is not None
    assert found.id == owner.id
    assert await repo.get_user_by_email("nobody@example.com") is None


async def test_only_active_memberships_of_active_organizations_are_listed(
    repo: IdentityRepository,
) -> None:
    organization, owner = await seed(repo)
    closed = Organization(code="OLD", name="Closed organization", is_active=False)
    paused = Organization(code="PAUSED", name="Paused membership")
    repo.add(closed, paused)
    await repo.flush()
    repo.add(
        OrganizationMembership(
            organization_id=closed.id, user_id=owner.id, role=OrganizationRole.ENGINEER
        ),
        OrganizationMembership(
            organization_id=paused.id,
            user_id=owner.id,
            role=OrganizationRole.VIEWER,
            is_active=False,
        ),
    )
    await repo.commit()

    memberships = await repo.list_active_memberships(owner.id)

    assert [membership.organization_id for membership in memberships] == [organization.id]
    found = await repo.get_membership(owner.id, organization.id)
    assert found is not None
    assert found.role == OrganizationRole.OWNER


async def test_a_session_is_found_by_the_hash_of_its_token(repo: IdentityRepository) -> None:
    organization, owner = await seed(repo)
    token = generate_session_token()
    repo.add(
        UserSession(
            user_id=owner.id,
            organization_id=organization.id,
            token_hash=hash_session_token(token),
            expires_at=NOW + timedelta(hours=12),
        )
    )
    await repo.commit()

    found = await repo.get_session_by_token_hash(hash_session_token(token))

    assert found is not None
    assert found.user_id == owner.id
    assert await repo.get_session_by_token_hash(hash_session_token("another token")) is None


async def test_revoking_keeps_the_current_session_and_leaves_old_revocations_alone(
    repo: IdentityRepository,
) -> None:
    organization, owner = await seed(repo)
    earlier = NOW - timedelta(days=1)
    current = make_session(organization, owner)
    other = make_session(organization, owner)
    already_revoked = make_session(organization, owner, revoked_at=earlier)
    repo.add(current, other, already_revoked)
    await repo.commit()
    hashes = (current.token_hash, other.token_hash, already_revoked.token_hash)

    revoked = await repo.revoke_sessions_of_user(
        owner.id, revoked_at=NOW, except_session_id=current.id
    )
    await repo.commit()

    assert revoked == 1
    fresh = [await repo.get_session_by_token_hash(token_hash) for token_hash in hashes]
    assert fresh[0] is not None and fresh[0].revoked_at is None
    assert fresh[1] is not None and fresh[1].revoked_at is not None
    assert fresh[2] is not None and fresh[2].revoked_at is not None
    assert fresh[2].revoked_at.replace(tzinfo=UTC) == earlier


async def test_only_owners_who_can_sign_in_are_counted(repo: IdentityRepository) -> None:
    organization, _ = await seed(repo)
    disabled_owner = make_user("former@example.com", active=False)
    paused_owner = make_user("paused@example.com")
    engineer = make_user("engineer@example.com")
    repo.add(disabled_owner, paused_owner, engineer)
    await repo.flush()
    repo.add(
        OrganizationMembership(
            organization_id=organization.id,
            user_id=disabled_owner.id,
            role=OrganizationRole.OWNER,
        ),
        OrganizationMembership(
            organization_id=organization.id,
            user_id=paused_owner.id,
            role=OrganizationRole.OWNER,
            is_active=False,
        ),
        OrganizationMembership(
            organization_id=organization.id, user_id=engineer.id, role=OrganizationRole.ENGINEER
        ),
    )
    await repo.commit()

    assert await repo.count_active_owners(organization.id) == 1


async def test_users_of_an_organization_come_with_their_role_sorted_by_email(
    repo: IdentityRepository,
) -> None:
    organization, _ = await seed(repo)
    engineer = make_user("engineer@example.com")
    repo.add(engineer)
    await repo.flush()
    repo.add(
        OrganizationMembership(
            organization_id=organization.id, user_id=engineer.id, role=OrganizationRole.ENGINEER
        )
    )
    await repo.commit()

    rows = await repo.list_users_of_organization(organization.id)

    assert [(user.email, membership.role) for user, membership in rows] == [
        ("engineer@example.com", "ENGINEER"),
        ("owner@example.com", "OWNER"),
    ]


async def test_auth_events_come_newest_first_with_limit_and_user_filter(
    repo: IdentityRepository,
) -> None:
    _, owner = await seed(repo)
    repo.add(
        AuthEvent(
            event_type=AuthEventType.LOGIN_FAILED,
            email_attempted="nobody@example.com",
            occurred_at=NOW - timedelta(minutes=2),
        ),
        AuthEvent(
            event_type=AuthEventType.LOGIN_SUCCEEDED,
            user_id=owner.id,
            occurred_at=NOW - timedelta(minutes=1),
        ),
        AuthEvent(event_type=AuthEventType.LOGOUT, user_id=owner.id, occurred_at=NOW),
    )
    await repo.commit()

    newest_two = await repo.list_auth_events(limit=2)
    of_owner = await repo.list_auth_events(user_id=owner.id)

    assert [event.event_type for event in newest_two] == ["LOGOUT", "LOGIN_SUCCEEDED"]
    assert [event.event_type for event in of_owner] == ["LOGOUT", "LOGIN_SUCCEEDED"]
