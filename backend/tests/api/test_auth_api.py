"""API tests for sign-in, sign-out, the current session and password change (EOS-01 a)."""

from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from argon2 import PasswordHasher
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.core import security
from app.core.config import settings
from app.core.security import hash_password
from app.models.identity import Organization, OrganizationMembership, OrganizationRole, User
from app.repositories.identity import IdentityRepository

pytestmark = pytest.mark.api

EMAIL = "owner@example.com"
PASSWORD = "correct horse battery staple"
NEW_PASSWORD = "a completely different passphrase"
LOGIN = "/api/v1/auth/login"
LOGOUT = "/api/v1/auth/logout"
ME = "/api/v1/auth/me"
CHANGE_PASSWORD = "/api/v1/auth/password"


@pytest.fixture(autouse=True)
def cheap_argon2(monkeypatch: pytest.MonkeyPatch) -> None:
    hasher = PasswordHasher(time_cost=1, memory_cost=64, parallelism=1)
    monkeypatch.setattr(security, "_hasher", hasher)


@pytest_asyncio.fixture
async def api(client: AsyncClient, test_engine: AsyncEngine) -> AsyncIterator[AsyncClient]:
    """The shared client over https (a Secure cookie must come back) with one owner in place."""

    factory = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as db:
        repo = IdentityRepository(db)
        organization = Organization(code="KES", name="Kamra Engineering Solutions")
        user = User(email=EMAIL, full_name="Test Owner", password_hash=hash_password(PASSWORD))
        repo.add(organization, user)
        await repo.flush()
        repo.add(
            OrganizationMembership(
                organization_id=organization.id, user_id=user.id, role=OrganizationRole.OWNER
            )
        )
        await repo.commit()

    client.base_url = "https://testserver"
    yield client


async def sign_in(api: AsyncClient, password: str = PASSWORD) -> None:
    response = await api.post(LOGIN, json={"email": EMAIL, "password": password})
    assert response.status_code == 200, response.text


async def test_sign_in_returns_the_identity_and_sets_a_protected_cookie(api: AsyncClient) -> None:
    response = await api.post(LOGIN, json={"email": f" {EMAIL.upper()} ", "password": PASSWORD})

    assert response.status_code == 200
    body = response.json()
    assert body["user"]["email"] == EMAIL
    assert body["organization"]["code"] == "KES"
    assert body["role"] == "OWNER"
    assert body["idle_timeout_minutes"] == settings.SESSION_IDLE_TIMEOUT_MINUTES

    cookie = response.headers["set-cookie"]
    assert cookie.startswith(f"{settings.SESSION_COOKIE_NAME}=")
    assert "HttpOnly" in cookie
    assert "SameSite=strict" in cookie
    assert "Path=/" in cookie
    token = api.cookies[settings.SESSION_COOKIE_NAME]
    assert len(token) >= 43
    assert token not in response.text, "the token must travel only in the cookie"
    assert response.headers["cache-control"] == "no-store"


async def test_wrong_password_and_unknown_email_get_the_same_401(api: AsyncClient) -> None:
    wrong = await api.post(LOGIN, json={"email": EMAIL, "password": "not the password"})
    unknown = await api.post(LOGIN, json={"email": "nobody@example.com", "password": PASSWORD})

    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()
    assert "Sign-in failed" in wrong.json()["detail"]
    assert "set-cookie" not in wrong.headers


async def test_a_refused_request_body_does_not_echo_the_password(api: AsyncClient) -> None:
    oversized = "x" * 1025
    response = await api.post(LOGIN, json={"email": EMAIL, "password": oversized})

    assert response.status_code == 422
    assert oversized not in response.text
    error = response.json()["detail"][0]
    assert error["loc"] == ["body", "password"]
    assert "input" not in error


async def test_me_needs_a_session(api: AsyncClient) -> None:
    anonymous = await api.get(ME)
    assert anonymous.status_code == 401
    assert anonymous.json()["detail"] == "Sign in to continue."

    await sign_in(api)
    signed_in = await api.get(ME)
    assert signed_in.status_code == 200
    assert signed_in.json()["user"]["full_name"] == "Test Owner"


async def test_a_made_up_cookie_is_refused(api: AsyncClient) -> None:
    api.cookies.set(settings.SESSION_COOKIE_NAME, "made-up-token")

    assert (await api.get(ME)).status_code == 401


async def test_sign_out_closes_the_session_on_the_server(api: AsyncClient) -> None:
    await sign_in(api)
    token = api.cookies[settings.SESSION_COOKIE_NAME]

    response = await api.post(LOGOUT)
    assert response.status_code == 204
    assert settings.SESSION_COOKIE_NAME not in api.cookies

    api.cookies.set(settings.SESSION_COOKIE_NAME, token)
    assert (await api.get(ME)).status_code == 401, "a copied cookie must be dead after sign-out"
    assert (await api.post(LOGOUT)).status_code == 204


async def test_password_change_refusals_are_readable(api: AsyncClient) -> None:
    anonymous = await api.post(
        CHANGE_PASSWORD, json={"current_password": PASSWORD, "new_password": NEW_PASSWORD}
    )
    assert anonymous.status_code == 401

    await sign_in(api)
    wrong = await api.post(
        CHANGE_PASSWORD, json={"current_password": "not it", "new_password": NEW_PASSWORD}
    )
    assert wrong.status_code == 400
    assert wrong.json()["detail"] == "The current password is not correct."

    weak = await api.post(
        CHANGE_PASSWORD, json={"current_password": PASSWORD, "new_password": "short"}
    )
    assert weak.status_code == 422
    assert weak.json()["detail"] == "Password must have at least 12 characters."


async def test_password_change_takes_effect_and_keeps_this_session(api: AsyncClient) -> None:
    await sign_in(api)

    response = await api.post(
        CHANGE_PASSWORD, json={"current_password": PASSWORD, "new_password": NEW_PASSWORD}
    )
    assert response.status_code == 204
    assert (await api.get(ME)).status_code == 200

    await api.post(LOGOUT)
    old = await api.post(LOGIN, json={"email": EMAIL, "password": PASSWORD})
    assert old.status_code == 401
    await sign_in(api, NEW_PASSWORD)


async def test_the_client_address_is_taken_from_the_proxy_headers(
    api: AsyncClient, test_engine: AsyncEngine
) -> None:
    await api.post(
        LOGIN,
        json={"email": EMAIL, "password": PASSWORD},
        headers={"X-Forwarded-For": "198.51.100.9, 10.0.0.1", "User-Agent": "pytest-browser"},
    )

    factory = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as db:
        event = (await IdentityRepository(db).list_auth_events())[0]
    assert event.event_type == "LOGIN_SUCCEEDED"
    assert event.ip_address == "198.51.100.9"
    assert event.user_agent == "pytest-browser"
