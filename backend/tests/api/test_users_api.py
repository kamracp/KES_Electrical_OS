"""API tests for user administration by an owner (EOS-01 a)."""

from collections.abc import AsyncIterator
from typing import Any
from uuid import uuid4

import pytest
import pytest_asyncio
from argon2 import PasswordHasher
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.core import security
from app.core.security import hash_password
from app.main import app
from app.models.identity import Organization, OrganizationMembership, OrganizationRole, User
from app.repositories.identity import IdentityRepository

pytestmark = pytest.mark.api

OWNER_EMAIL = "owner@example.com"
OWNER_PASSWORD = "correct horse battery staple"
FIRST_PASSWORD = "first password from the owner"
OWN_PASSWORD = "my own long secret passphrase"
USERS = "/api/v1/users"
LOGIN = "/api/v1/auth/login"
ME = "/api/v1/auth/me"
CHANGE_PASSWORD = "/api/v1/auth/password"
STUDY_LIST = "/api/v1/electrical/fault/runs"
NEW_ENGINEER: dict[str, Any] = {
    "email": "Engineer@Example.com",
    "full_name": "Asha Verma",
    "role": "ENGINEER",
    "password": FIRST_PASSWORD,
}


@pytest.fixture(autouse=True)
def cheap_argon2(monkeypatch: pytest.MonkeyPatch) -> None:
    hasher = PasswordHasher(time_cost=1, memory_cost=64, parallelism=1)
    monkeypatch.setattr(security, "_hasher", hasher)


async def sign_in(client: AsyncClient, email: str, password: str) -> None:
    response = await client.post(LOGIN, json={"email": email, "password": password})
    assert response.status_code == 200, response.text


@pytest_asyncio.fixture
async def owner(
    anonymous_client: AsyncClient, test_engine: AsyncEngine
) -> AsyncIterator[AsyncClient]:
    """The shared client, really signed in as the only owner of a real organization."""

    factory = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as db:
        repo = IdentityRepository(db)
        organization = Organization(code="KES", name="Kamra Engineering Solutions")
        user = User(
            email=OWNER_EMAIL,
            full_name="Test Owner",
            password_hash=hash_password(OWNER_PASSWORD),
        )
        repo.add(organization, user)
        await repo.flush()
        repo.add(
            OrganizationMembership(
                organization_id=organization.id, user_id=user.id, role=OrganizationRole.OWNER
            )
        )
        await repo.commit()

    anonymous_client.base_url = "https://testserver"
    await sign_in(anonymous_client, OWNER_EMAIL, OWNER_PASSWORD)
    yield anonymous_client


@pytest_asyncio.fixture
async def second_browser(owner: AsyncClient) -> AsyncIterator[AsyncClient]:
    """Another browser on the same application, with its own cookies."""

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="https://testserver"
    ) as browser:
        yield browser


async def create_engineer(owner: AsyncClient) -> dict[str, Any]:
    response = await owner.post(USERS, json=NEW_ENGINEER)
    assert response.status_code == 201, response.text
    return response.json()


async def test_an_owner_creates_a_user_and_sees_it_in_the_list(owner: AsyncClient) -> None:
    created = await create_engineer(owner)

    assert created["email"] == "engineer@example.com"
    assert created["role"] == "ENGINEER"
    assert created["is_active"] is True
    assert created["must_change_password"] is True
    assert FIRST_PASSWORD not in str(created)
    assert not any("hash" in key for key in created)

    listing = (await owner.get(USERS)).json()
    assert listing["total"] == 2
    assert [item["email"] for item in listing["items"]] == [
        "engineer@example.com",
        OWNER_EMAIL,
    ]


async def test_a_second_user_with_the_same_email_is_refused(owner: AsyncClient) -> None:
    await create_engineer(owner)

    again = await owner.post(USERS, json={**NEW_ENGINEER, "email": "ENGINEER@example.com"})

    assert again.status_code == 409
    assert again.json()["detail"] == "A user with this e-mail already exists."


async def test_a_weak_first_password_is_refused_with_a_readable_message(
    owner: AsyncClient,
) -> None:
    response = await owner.post(USERS, json={**NEW_ENGINEER, "password": "short"})

    assert response.status_code == 422
    assert response.json()["detail"] == "Password must have at least 12 characters."


async def test_a_new_user_reaches_nothing_before_changing_the_first_password(
    owner: AsyncClient, second_browser: AsyncClient
) -> None:
    await create_engineer(owner)
    await sign_in(second_browser, "engineer@example.com", FIRST_PASSWORD)

    assert (await second_browser.get(ME)).json()["user"]["must_change_password"] is True
    blocked = await second_browser.get(STUDY_LIST)
    assert blocked.status_code == 403
    assert blocked.json()["detail"] == "Change your password before you continue."

    changed = await second_browser.post(
        CHANGE_PASSWORD,
        json={"current_password": FIRST_PASSWORD, "new_password": OWN_PASSWORD},
    )
    assert changed.status_code == 204
    assert (await second_browser.get(STUDY_LIST)).status_code not in {401, 403}


async def test_user_administration_is_for_owners_only(
    owner: AsyncClient, second_browser: AsyncClient
) -> None:
    await owner.post(USERS, json={**NEW_ENGINEER, "must_change_password": False})
    await sign_in(second_browser, "engineer@example.com", FIRST_PASSWORD)

    for response in (
        await second_browser.get(USERS),
        await second_browser.get(f"{USERS}/events"),
        await second_browser.post(USERS, json={**NEW_ENGINEER, "email": "x@example.com"}),
    ):
        assert response.status_code == 403
        assert response.json()["detail"] == "This action needs the role OWNER."


async def test_an_owner_renames_a_user_and_changes_the_role(owner: AsyncClient) -> None:
    created = await create_engineer(owner)

    response = await owner.patch(
        f"{USERS}/{created['id']}", json={"full_name": " Asha  V. Verma ", "role": "VIEWER"}
    )

    assert response.status_code == 200
    assert response.json()["full_name"] == "Asha V. Verma"
    assert response.json()["role"] == "VIEWER"


async def test_deactivating_a_user_closes_the_open_session_and_blocks_sign_in(
    owner: AsyncClient, second_browser: AsyncClient
) -> None:
    created = await owner.post(USERS, json={**NEW_ENGINEER, "must_change_password": False})
    await sign_in(second_browser, "engineer@example.com", FIRST_PASSWORD)
    assert (await second_browser.get(ME)).status_code == 200

    response = await owner.patch(f"{USERS}/{created.json()['id']}", json={"is_active": False})
    assert response.status_code == 200
    assert response.json()["is_active"] is False

    assert (await second_browser.get(ME)).status_code == 401
    again = await second_browser.post(
        LOGIN, json={"email": "engineer@example.com", "password": FIRST_PASSWORD}
    )
    assert again.status_code == 401


async def test_an_owner_cannot_demote_or_deactivate_the_own_account(owner: AsyncClient) -> None:
    own_id = (await owner.get(ME)).json()["user"]["id"]

    for change in ({"role": "VIEWER"}, {"is_active": False}):
        response = await owner.patch(f"{USERS}/{own_id}", json=change)
        assert response.status_code == 409
        assert "your own" in response.json()["detail"]

    renamed = await owner.patch(f"{USERS}/{own_id}", json={"full_name": "C. P. Kamra"})
    assert renamed.status_code == 200
    assert (await owner.get(ME)).json()["role"] == "OWNER"


async def test_a_password_reset_closes_sessions_and_asks_for_a_change_again(
    owner: AsyncClient, second_browser: AsyncClient
) -> None:
    created = await owner.post(USERS, json={**NEW_ENGINEER, "must_change_password": False})
    user_id = created.json()["id"]
    await sign_in(second_browser, "engineer@example.com", FIRST_PASSWORD)

    response = await owner.post(f"{USERS}/{user_id}/password", json={"new_password": OWN_PASSWORD})
    assert response.status_code == 204

    assert (await second_browser.get(ME)).status_code == 401
    old = await second_browser.post(
        LOGIN, json={"email": "engineer@example.com", "password": FIRST_PASSWORD}
    )
    assert old.status_code == 401
    await sign_in(second_browser, "engineer@example.com", OWN_PASSWORD)
    assert (await second_browser.get(ME)).json()["user"]["must_change_password"] is True

    own_id = (await owner.get(ME)).json()["user"]["id"]
    own = await owner.post(f"{USERS}/{own_id}/password", json={"new_password": OWN_PASSWORD})
    assert own.status_code == 409


async def test_an_unknown_user_is_404_and_an_empty_update_is_422(owner: AsyncClient) -> None:
    unknown = f"{USERS}/{uuid4()}"

    assert (await owner.patch(unknown, json={"is_active": False})).status_code == 404
    assert (
        await owner.post(f"{unknown}/password", json={"new_password": OWN_PASSWORD})
    ).status_code == 404
    assert (await owner.patch(unknown, json={})).status_code == 422


async def test_the_audit_trail_shows_who_did_what(owner: AsyncClient) -> None:
    created = await create_engineer(owner)
    await owner.patch(f"{USERS}/{created['id']}", json={"role": "VIEWER"})

    events = (await owner.get(f"{USERS}/events")).json()["items"]
    by_type = {event["event_type"]: event for event in events}

    assert {"LOGIN_SUCCEEDED", "USER_CREATED", "USER_UPDATED"} <= set(by_type)
    assert by_type["USER_CREATED"]["detail"] == f"created as ENGINEER by {OWNER_EMAIL}"
    assert by_type["USER_UPDATED"]["detail"] == f"role ENGINEER -> VIEWER; by {OWNER_EMAIL}"
    assert by_type["USER_CREATED"]["user_id"] == created["id"]
    assert (await owner.get(f"{USERS}/events", params={"limit": 0})).status_code == 422
