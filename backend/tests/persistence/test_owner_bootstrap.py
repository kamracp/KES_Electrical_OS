"""Tests for the first-owner and owner-recovery server command (EOS-01 a)."""

import argparse
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from argon2 import PasswordHasher
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.cli import create_owner as command
from app.core import security
from app.models.identity import OrganizationRole
from app.repositories.identity import IdentityRepository
from app.services.auth import AuthService, InvalidCredentialsError, SessionInvalidError
from app.services.owner_bootstrap import OwnerBootstrapError, OwnerBootstrapService

pytestmark = pytest.mark.persistence

EMAIL = "owner@example.com"
PASSWORD = "correct horse battery staple"
NEW_PASSWORD = "a completely different passphrase"
OWNER = {
    "organization_code": " KES ",
    "organization_name": "Kamra  Engineering Solutions",
    "email": " Owner@Example.com ",
    "full_name": "C. P.  Kamra",
    "password": PASSWORD,
}


@pytest.fixture(autouse=True)
def cheap_argon2(monkeypatch: pytest.MonkeyPatch) -> None:
    hasher = PasswordHasher(time_cost=1, memory_cost=64, parallelism=1)
    monkeypatch.setattr(security, "_hasher", hasher)


@pytest.fixture
def factory(test_engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture
async def repo(factory: async_sessionmaker[AsyncSession]) -> AsyncIterator[IdentityRepository]:
    async with factory() as db:
        yield IdentityRepository(db)


async def test_the_first_owner_is_created_and_can_sign_in(repo: IdentityRepository) -> None:
    result = await OwnerBootstrapService(repo).create_owner(**OWNER)

    assert (result.action, result.email, result.organization_code) == ("created", EMAIL, "KES")
    assert result.organization_created is True

    organization = await repo.get_organization_by_code("KES")
    assert organization is not None
    assert organization.name == "Kamra Engineering Solutions"
    assert await repo.count_active_owners(organization.id) == 1

    _, identity = await AuthService(repo).login(EMAIL, PASSWORD)
    assert identity.role == OrganizationRole.OWNER
    assert identity.user.full_name == "C. P. Kamra"
    assert identity.user.must_change_password is False

    events = [event.detail for event in await repo.list_auth_events()]
    assert "owner created by the server command" in events


async def test_a_second_owner_joins_the_existing_organization(repo: IdentityRepository) -> None:
    service = OwnerBootstrapService(repo)
    await service.create_owner(**OWNER)

    result = await service.create_owner(
        **{**OWNER, "email": "second@example.com", "organization_name": "ignored"}
    )

    assert result.organization_created is False
    organization = await repo.get_organization_by_code("KES")
    assert organization is not None
    assert organization.name == "Kamra Engineering Solutions"
    assert await repo.count_active_owners(organization.id) == 2


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"password": "short"}, "at least 12 characters"),
        ({"email": "not-an-email"}, "valid e-mail address"),
        ({"full_name": "  "}, "Name is required"),
        ({"organization_code": " "}, "Organization code is required"),
        ({"organization_name": " "}, "Organization name is required"),
    ],
)
async def test_bad_input_is_refused_and_nothing_is_stored(
    repo: IdentityRepository, change: dict[str, str], message: str
) -> None:
    with pytest.raises(OwnerBootstrapError, match=message):
        await OwnerBootstrapService(repo).create_owner(**{**OWNER, **change})

    await repo.rollback()
    assert await repo.get_user_by_email(EMAIL) is None
    assert await repo.get_organization_by_code("KES") is None


async def test_an_existing_email_points_to_recovery(repo: IdentityRepository) -> None:
    service = OwnerBootstrapService(repo)
    await service.create_owner(**OWNER)

    with pytest.raises(OwnerBootstrapError, match="--recover"):
        await service.create_owner(**OWNER)


async def test_recovery_restores_a_locked_out_deactivated_and_demoted_owner(
    repo: IdentityRepository,
) -> None:
    service = OwnerBootstrapService(repo)
    await service.create_owner(**OWNER)
    auth = AuthService(repo)
    token, identity = await auth.login(EMAIL, PASSWORD)
    identity.user.is_active = False
    identity.user.locked_until = datetime.now(UTC) + timedelta(minutes=15)
    identity.membership.role = OrganizationRole.VIEWER.value
    identity.membership.is_active = False
    await repo.commit()

    result = await service.recover_owner(
        organization_code="KES", email=EMAIL, password=NEW_PASSWORD
    )

    assert result.action == "recovered"
    with pytest.raises(SessionInvalidError):
        await auth.authenticate(token)
    with pytest.raises(InvalidCredentialsError):
        await auth.login(EMAIL, PASSWORD)
    _, recovered = await auth.login(EMAIL, NEW_PASSWORD)
    assert recovered.role == OrganizationRole.OWNER
    assert "owner access recovered by the server command" in [
        event.detail for event in await repo.list_auth_events()
    ]


async def test_recovery_needs_an_existing_organization_and_user(repo: IdentityRepository) -> None:
    service = OwnerBootstrapService(repo)
    await service.create_owner(**OWNER)

    for code, email in (("NOPE", EMAIL), ("KES", "nobody@example.com")):
        with pytest.raises(OwnerBootstrapError, match="existing organization code"):
            await service.recover_owner(organization_code=code, email=email, password=NEW_PASSWORD)
    with pytest.raises(OwnerBootstrapError, match="at least 12 characters"):
        await service.recover_owner(organization_code="KES", email=EMAIL, password="short")


async def test_the_command_runs_both_modes_against_a_session_factory(
    factory: async_sessionmaker[AsyncSession],
) -> None:
    create = argparse.Namespace(
        recover=False,
        organization_code="KES",
        organization_name="Kamra Engineering Solutions",
        email=EMAIL,
        full_name="C. P. Kamra",
    )
    created = await command.run(create, PASSWORD, factory)
    assert created.action == "created"

    recover = argparse.Namespace(recover=True, organization_code="KES", email=EMAIL)
    recovered = await command.run(recover, NEW_PASSWORD, factory)
    assert recovered.action == "recovered"


def test_the_command_never_takes_a_password_from_the_command_line() -> None:
    options = {
        option for action in command.build_parser()._actions for option in action.option_strings
    }

    assert not any("pass" in option for option in options)
    assert {"--organization-code", "--email", "--recover"} <= options


def test_two_different_passwords_change_nothing(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    answers = iter([PASSWORD, NEW_PASSWORD])
    monkeypatch.setattr(command.getpass, "getpass", lambda prompt: next(answers))
    monkeypatch.setattr(
        command.asyncio, "run", lambda coroutine: pytest.fail("the database was reached")
    )

    exit_code = command.main(
        [
            "--organization-code",
            "KES",
            "--organization-name",
            "Kamra Engineering Solutions",
            "--email",
            EMAIL,
            "--full-name",
            "C. P. Kamra",
        ]
    )

    assert exit_code == 1
    assert "passwords differ" in capsys.readouterr().err
