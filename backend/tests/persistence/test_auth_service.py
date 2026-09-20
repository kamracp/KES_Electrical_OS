"""Service tests for sign-in, lockout, sessions, sign-out and password change (EOS-01 a)."""

from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from argon2 import PasswordHasher
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.core import security
from app.core.config import Settings
from app.core.security import PasswordPolicyError, hash_password, hash_session_token
from app.models.identity import (
    Organization,
    OrganizationMembership,
    OrganizationRole,
    User,
)
from app.repositories.identity import IdentityRepository
from app.services.auth import (
    AuthService,
    InvalidCredentialsError,
    PasswordChangeError,
    RequestContext,
    SessionInvalidError,
)

pytestmark = pytest.mark.persistence

EMAIL = "owner@example.com"
PASSWORD = "correct horse battery staple"
CONTEXT = RequestContext(ip_address="203.0.113.7", user_agent="pytest")


class Clock:
    def __init__(self) -> None:
        self.now = datetime(2026, 9, 20, 9, 0, tzinfo=UTC)

    def __call__(self) -> datetime:
        return self.now

    def advance(self, **delta: float) -> None:
        self.now += timedelta(**delta)


@dataclass
class Env:
    service: AuthService
    repo: IdentityRepository
    clock: Clock
    user: User
    organization: Organization
    membership: OrganizationMembership


@pytest.fixture(autouse=True)
def cheap_argon2(monkeypatch: pytest.MonkeyPatch) -> None:
    # Real parameters cost about 0.1 s per hash; the logic under test does not depend on them.
    monkeypatch.setattr(
        security, "_hasher", PasswordHasher(time_cost=1, memory_cost=64, parallelism=1)
    )


@pytest_asyncio.fixture
async def env(test_engine: AsyncEngine) -> AsyncIterator[Env]:
    factory = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as db:
        repo = IdentityRepository(db)
        organization = Organization(code="KES", name="Kamra Engineering Solutions")
        user = User(email=EMAIL, full_name="Test Owner", password_hash=hash_password(PASSWORD))
        repo.add(organization, user)
        await repo.flush()
        membership = OrganizationMembership(
            organization_id=organization.id, user_id=user.id, role=OrganizationRole.OWNER
        )
        repo.add(membership)
        await repo.commit()

        clock = Clock()
        service = AuthService(repo, settings=Settings(_env_file=None), now=clock)  # type: ignore[call-arg]
        yield Env(service, repo, clock, user, organization, membership)


async def event_types(env: Env) -> list[str]:
    return [event.event_type for event in await env.repo.list_auth_events()]


async def test_sign_in_creates_a_session_that_stores_only_the_token_hash(env: Env) -> None:
    token, identity = await env.service.login(f"  {EMAIL.upper()} ", PASSWORD, CONTEXT)

    stored = await env.repo.get_session_by_token_hash(hash_session_token(token))
    assert stored is not None
    assert stored.token_hash != token
    assert stored.ip_address == "203.0.113.7"
    assert identity.user.id == env.user.id
    assert identity.organization.code == "KES"
    assert identity.role == "OWNER"
    assert env.user.last_login_at == env.clock.now
    assert env.user.failed_login_count == 0
    assert await event_types(env) == ["LOGIN_SUCCEEDED"]


async def test_wrong_password_counts_and_is_recorded(env: Env) -> None:
    with pytest.raises(InvalidCredentialsError):
        await env.service.login(EMAIL, "not the password", CONTEXT)

    assert env.user.failed_login_count == 1
    assert env.user.locked_until is None
    assert await event_types(env) == ["LOGIN_FAILED"]


async def test_unknown_email_gets_the_same_message_and_is_recorded_without_a_user(
    env: Env,
) -> None:
    with pytest.raises(InvalidCredentialsError) as unknown:
        await env.service.login("nobody@example.com", PASSWORD, CONTEXT)
    env.clock.advance(seconds=1)
    with pytest.raises(InvalidCredentialsError) as wrong:
        await env.service.login(EMAIL, "not the password", CONTEXT)

    assert str(unknown.value) == str(wrong.value) == env.service.sign_in_failed_message
    events = await env.repo.list_auth_events()
    first = events[-1]
    assert first.user_id is None
    assert first.email_attempted == "nobody@example.com"


async def test_five_failures_lock_the_account_and_the_lock_ends_by_itself(env: Env) -> None:
    for _ in range(5):
        # The test clock stands still; events at the same instant have no defined order.
        env.clock.advance(seconds=1)
        with pytest.raises(InvalidCredentialsError):
            await env.service.login(EMAIL, "not the password", CONTEXT)

    assert env.user.locked_until == env.clock.now + timedelta(minutes=15)
    assert (await event_types(env))[0] == "LOGIN_LOCKED"

    locked_until = env.user.locked_until
    env.clock.advance(minutes=14)
    with pytest.raises(InvalidCredentialsError) as while_locked:
        await env.service.login(EMAIL, PASSWORD, CONTEXT)
    assert str(while_locked.value) == env.service.sign_in_failed_message
    assert env.user.locked_until == locked_until, "a locked account must not be locked longer"

    env.clock.advance(minutes=2)
    await env.service.login(EMAIL, PASSWORD, CONTEXT)
    assert env.user.locked_until is None
    assert env.user.failed_login_count == 0


async def test_an_inactive_user_cannot_sign_in(env: Env) -> None:
    env.user.is_active = False
    await env.repo.commit()

    with pytest.raises(InvalidCredentialsError):
        await env.service.login(EMAIL, PASSWORD, CONTEXT)
    assert env.user.failed_login_count == 0


async def test_a_user_without_an_active_membership_cannot_sign_in(env: Env) -> None:
    env.membership.is_active = False
    await env.repo.commit()

    with pytest.raises(InvalidCredentialsError):
        await env.service.login(EMAIL, PASSWORD, CONTEXT)


async def test_an_oversized_password_is_refused_without_hashing_it(env: Env) -> None:
    with pytest.raises(InvalidCredentialsError):
        await env.service.login(EMAIL, "x" * 5000, CONTEXT)
    assert env.user.failed_login_count == 0


async def test_a_weaker_hash_is_upgraded_at_the_next_sign_in(env: Env) -> None:
    env.user.password_hash = PasswordHasher(time_cost=1, memory_cost=8, parallelism=1).hash(
        PASSWORD
    )
    await env.repo.commit()
    weak = env.user.password_hash

    await env.service.login(EMAIL, PASSWORD, CONTEXT)

    assert env.user.password_hash != weak
    assert security.verify_password(PASSWORD, env.user.password_hash) is True


async def test_a_valid_token_is_recognised_and_others_are_not(env: Env) -> None:
    token, _ = await env.service.login(EMAIL, PASSWORD, CONTEXT)

    identity = await env.service.authenticate(token)
    assert identity.user.email == EMAIL
    assert identity.role == "OWNER"

    for bad in (None, "", "not-a-token", token + "x"):
        with pytest.raises(SessionInvalidError):
            await env.service.authenticate(bad)


async def test_an_idle_session_expires_and_is_revoked(env: Env) -> None:
    token, _ = await env.service.login(EMAIL, PASSWORD, CONTEXT)

    env.clock.advance(hours=12, minutes=1)
    with pytest.raises(SessionInvalidError, match="expired"):
        await env.service.authenticate(token)

    stored = await env.repo.get_session_by_token_hash(hash_session_token(token))
    assert stored is not None
    assert stored.revoked_at is not None


async def test_activity_keeps_a_session_alive_until_the_absolute_lifetime(env: Env) -> None:
    token, _ = await env.service.login(EMAIL, PASSWORD, CONTEXT)

    for _ in range(27):
        env.clock.advance(hours=6)
        await env.service.authenticate(token)

    env.clock.advance(hours=6)
    with pytest.raises(SessionInvalidError, match="expired"):
        await env.service.authenticate(token)


async def test_sign_out_revokes_the_session_once(env: Env) -> None:
    token, _ = await env.service.login(EMAIL, PASSWORD, CONTEXT)

    env.clock.advance(seconds=1)
    await env.service.logout(token, CONTEXT)
    await env.service.logout(token, CONTEXT)
    await env.service.logout(None)

    with pytest.raises(SessionInvalidError):
        await env.service.authenticate(token)
    assert await event_types(env) == ["LOGOUT", "LOGIN_SUCCEEDED"]


async def test_deactivating_a_user_ends_the_open_session(env: Env) -> None:
    token, _ = await env.service.login(EMAIL, PASSWORD, CONTEXT)
    env.user.is_active = False
    await env.repo.commit()

    with pytest.raises(SessionInvalidError):
        await env.service.authenticate(token)


async def test_password_change_is_refused_for_a_wrong_weak_or_unchanged_password(
    env: Env,
) -> None:
    _, identity = await env.service.login(EMAIL, PASSWORD, CONTEXT)

    with pytest.raises(PasswordChangeError, match="current password"):
        await env.service.change_password(identity, "not the password", "another long passphrase")
    with pytest.raises(PasswordChangeError, match="must differ"):
        await env.service.change_password(identity, PASSWORD, PASSWORD)
    with pytest.raises(PasswordPolicyError, match="at least 12"):
        await env.service.change_password(identity, PASSWORD, "short")

    assert security.verify_password(PASSWORD, env.user.password_hash) is True


async def test_password_change_closes_the_other_sessions_and_keeps_this_one(env: Env) -> None:
    other_token, _ = await env.service.login(EMAIL, PASSWORD, CONTEXT)
    token, identity = await env.service.login(EMAIL, PASSWORD, CONTEXT)
    new_password = "a completely different passphrase"

    await env.service.change_password(identity, PASSWORD, new_password, CONTEXT)

    await env.service.authenticate(token)
    with pytest.raises(SessionInvalidError):
        await env.service.authenticate(other_token)
    with pytest.raises(InvalidCredentialsError):
        await env.service.login(EMAIL, PASSWORD, CONTEXT)
    await env.service.login(EMAIL, new_password, CONTEXT)
    assert env.user.password_changed_at == env.clock.now
    assert "PASSWORD_CHANGED" in await event_types(env)
