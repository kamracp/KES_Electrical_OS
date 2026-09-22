"""API tests for the project spine: sites, projects and revisions (EOS-01 b)."""

from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import AsyncExitStack
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

SITES = "/api/v1/sites"
PROJECTS = "/api/v1/projects"
LOGIN = "/api/v1/auth/login"
PASSWORD = "correct horse battery staple"

OWNER_EMAIL = "owner@example.com"
ENGINEER_EMAIL = "engineer@example.com"
VIEWER_EMAIL = "viewer@example.com"
RIVAL_OWNER_EMAIL = "owner@rival.example.com"
OWNER_LABEL = f"Test Owner ({OWNER_EMAIL})"

NEW_SITE: dict[str, Any] = {"code": "PLANT-A", "name": "Plant A", "location": "Ludhiana"}
NEW_PROJECT: dict[str, Any] = {
    "code": "PRJ-001",
    "name": "Pump House",
    "jurisdiction_profile": "IN",
    "client_name": "Northern Mills",
}


@pytest.fixture(autouse=True)
def cheap_argon2(monkeypatch: pytest.MonkeyPatch) -> None:
    hasher = PasswordHasher(time_cost=1, memory_cost=64, parallelism=1)
    monkeypatch.setattr(security, "_hasher", hasher)


@pytest_asyncio.fixture
async def organizations(anonymous_client: AsyncClient, test_engine: AsyncEngine) -> None:
    """Two organizations: KES with its three roles, and a second one that owns nothing here."""

    factory = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as db:
        repo = IdentityRepository(db)
        kes = Organization(code="KES", name="Kamra Engineering Solutions")
        rival = Organization(code="RIVAL", name="Another Engineering Office")
        people = {
            OWNER_EMAIL: ("Test Owner", OrganizationRole.OWNER, kes),
            ENGINEER_EMAIL: ("Test Engineer", OrganizationRole.ENGINEER, kes),
            VIEWER_EMAIL: ("Test Viewer", OrganizationRole.VIEWER, kes),
            RIVAL_OWNER_EMAIL: ("Rival Owner", OrganizationRole.OWNER, rival),
        }
        repo.add(kes, rival)
        for email, (full_name, _role, _organization) in people.items():
            repo.add(User(email=email, full_name=full_name, password_hash=hash_password(PASSWORD)))
        await repo.flush()
        for email, (_full_name, role, organization) in people.items():
            user = await repo.get_user_by_email(email)
            assert user is not None
            repo.add(
                OrganizationMembership(organization_id=organization.id, user_id=user.id, role=role)
            )
        await repo.commit()


@pytest_asyncio.fixture
async def sign_in_as_user(
    organizations: None,
) -> AsyncIterator[Callable[[str], Awaitable[AsyncClient]]]:
    """A browser of its own for each person, really signed in through the login route."""

    async with AsyncExitStack() as stack:

        async def sign_in(email: str) -> AsyncClient:
            client = await stack.enter_async_context(
                AsyncClient(transport=ASGITransport(app=app), base_url="https://testserver")
            )
            response = await client.post(LOGIN, json={"email": email, "password": PASSWORD})
            assert response.status_code == 200, response.text
            return client

        yield sign_in


@pytest_asyncio.fixture
async def owner(sign_in_as_user: Callable[[str], Awaitable[AsyncClient]]) -> AsyncClient:
    return await sign_in_as_user(OWNER_EMAIL)


@pytest_asyncio.fixture
async def engineer(sign_in_as_user: Callable[[str], Awaitable[AsyncClient]]) -> AsyncClient:
    return await sign_in_as_user(ENGINEER_EMAIL)


@pytest_asyncio.fixture
async def viewer(sign_in_as_user: Callable[[str], Awaitable[AsyncClient]]) -> AsyncClient:
    return await sign_in_as_user(VIEWER_EMAIL)


@pytest_asyncio.fixture
async def rival_owner(sign_in_as_user: Callable[[str], Awaitable[AsyncClient]]) -> AsyncClient:
    return await sign_in_as_user(RIVAL_OWNER_EMAIL)


async def create_site(client: AsyncClient, **changes: Any) -> dict[str, Any]:
    response = await client.post(SITES, json={**NEW_SITE, **changes})
    assert response.status_code == 201, response.text
    return response.json()


async def create_project(client: AsyncClient, site_id: str, **changes: Any) -> dict[str, Any]:
    response = await client.post(PROJECTS, json={**NEW_PROJECT, "site_id": site_id, **changes})
    assert response.status_code == 201, response.text
    return response.json()


# -- the way through ----------------------------------------------------------------------


async def test_a_site_a_project_and_its_first_revision_are_created_together(
    owner: AsyncClient,
) -> None:
    site = await create_site(owner, code=" plant-a ", name="  Plant   A ")
    assert site["code"] == "plant-a"
    assert site["name"] == "Plant A"
    assert site["location"] == "Ludhiana"
    assert site["is_active"] is True

    project = await create_project(owner, site["id"])

    assert project["code"] == "PRJ-001"
    assert project["site_id"] == site["id"]
    assert project["jurisdiction_profile"] == "IN"
    assert project["status"] == "ACTIVE"
    assert [revision["revision_number"] for revision in project["revisions"]] == [1]
    first = project["revisions"][0]
    assert first["label"] == "Rev 1"
    assert first["status"] == "OPEN"
    assert first["created_by"] == OWNER_LABEL
    assert project["open_revision_id"] == first["id"]

    listing = (await owner.get(PROJECTS)).json()
    assert [item["code"] for item in listing["items"]] == ["PRJ-001"]
    assert (await owner.get(SITES)).json()["items"][0]["id"] == site["id"]


async def test_a_new_revision_supersedes_the_open_one(owner: AsyncClient) -> None:
    site = await create_site(owner)
    project = await create_project(owner, site["id"])

    created = await owner.post(
        f"{PROJECTS}/{project['id']}/revisions",
        json={"label": "  Rev   2 ", "notes": " after the client review "},
    )
    assert created.status_code == 201, created.text
    assert created.json()["revision_number"] == 2
    assert created.json()["label"] == "Rev 2"
    assert created.json()["notes"] == "after the client review"

    detail = (await owner.get(f"{PROJECTS}/{project['id']}")).json()
    assert [revision["revision_number"] for revision in detail["revisions"]] == [2, 1]
    assert [revision["status"] for revision in detail["revisions"]] == ["OPEN", "SUPERSEDED"]
    assert detail["open_revision_id"] == created.json()["id"]

    revisions = (await owner.get(f"{PROJECTS}/{project['id']}/revisions")).json()["items"]
    assert [revision["revision_number"] for revision in revisions] == [2, 1]


async def test_an_owner_issues_a_revision_and_it_is_signed_with_the_own_name(
    owner: AsyncClient,
) -> None:
    site = await create_site(owner)
    project = await create_project(owner, site["id"])
    revision_id = project["open_revision_id"]

    issued = await owner.post(f"{PROJECTS}/{project['id']}/revisions/{revision_id}/issue")

    assert issued.status_code == 200, issued.text
    assert issued.json()["status"] == "ISSUED"
    assert issued.json()["issued_by"] == OWNER_LABEL
    assert issued.json()["issued_at"] is not None

    again = await owner.post(f"{PROJECTS}/{project['id']}/revisions/{revision_id}/issue")
    assert again.status_code == 409
    assert again.json()["detail"] == "Only an open revision can be issued."

    detail = (await owner.get(f"{PROJECTS}/{project['id']}")).json()
    assert detail["open_revision_id"] is None


async def test_an_owner_archives_a_project_and_it_freezes(owner: AsyncClient) -> None:
    site = await create_site(owner)
    project = await create_project(owner, site["id"])

    archived = await owner.post(f"{PROJECTS}/{project['id']}/archive")
    assert archived.status_code == 200, archived.text
    assert archived.json()["status"] == "ARCHIVED"

    changed = await owner.patch(f"{PROJECTS}/{project['id']}", json={"name": "Another name"})
    assert changed.status_code == 409
    assert changed.json()["detail"] == "An archived project cannot be changed."

    revision = await owner.post(f"{PROJECTS}/{project['id']}/revisions", json={"label": "Rev 2"})
    assert revision.status_code == 409
    assert revision.json()["detail"] == "An archived project cannot take a new revision."

    assert (await owner.post(f"{PROJECTS}/{project['id']}/archive")).status_code == 409
    assert (await owner.get(PROJECTS, params={"status": "ACTIVE"})).json()["items"] == []
    assert len((await owner.get(PROJECTS, params={"status": "ARCHIVED"})).json()["items"]) == 1


async def test_a_project_and_a_site_are_updated_in_place(owner: AsyncClient) -> None:
    site = await create_site(owner)
    project = await create_project(owner, site["id"])

    renamed = await owner.patch(
        f"{PROJECTS}/{project['id']}", json={"name": "  Pump   House   B ", "client_name": "  "}
    )
    assert renamed.status_code == 200
    assert renamed.json()["name"] == "Pump House B"
    # A blank entry reads as "no change" today: the schema turns it into None and the service
    # cannot tell that from a field that was not sent at all. Clearing a client name needs a
    # service change, not an API change (follow-up).
    assert renamed.json()["client_name"] == "Northern Mills"

    closed = await owner.patch(f"{SITES}/{site['id']}", json={"is_active": False})
    assert closed.status_code == 200
    assert closed.json()["is_active"] is False
    assert (await owner.get(SITES)).json()["items"] == []
    assert len((await owner.get(SITES, params={"include_inactive": True})).json()["items"]) == 1


# -- refusals -----------------------------------------------------------------------------


async def test_a_second_site_or_project_with_the_same_code_is_refused(
    owner: AsyncClient,
) -> None:
    site = await create_site(owner)
    await create_project(owner, site["id"])

    again_site = await owner.post(SITES, json=NEW_SITE)
    assert again_site.status_code == 409
    assert again_site.json()["detail"] == "A site with this code already exists."

    again_project = await owner.post(PROJECTS, json={**NEW_PROJECT, "site_id": site["id"]})
    assert again_project.status_code == 409
    assert again_project.json()["detail"] == "A project with this code already exists."


async def test_a_project_cannot_be_opened_at_an_inactive_site(owner: AsyncClient) -> None:
    site = await create_site(owner)
    await owner.patch(f"{SITES}/{site['id']}", json={"is_active": False})

    response = await owner.post(PROJECTS, json={**NEW_PROJECT, "site_id": site["id"]})

    assert response.status_code == 409
    assert response.json()["detail"] == "The site is inactive."


async def test_unknown_records_are_404_and_a_bad_code_is_422(owner: AsyncClient) -> None:
    unknown = str(uuid4())

    assert (await owner.patch(f"{SITES}/{unknown}", json={"name": "X"})).status_code == 404
    assert (await owner.get(f"{PROJECTS}/{unknown}")).status_code == 404
    assert (await owner.get(f"{PROJECTS}/{unknown}/revisions")).status_code == 404
    assert (await owner.post(f"{PROJECTS}/{unknown}/archive")).status_code == 404
    assert (await owner.post(PROJECTS, json={**NEW_PROJECT, "site_id": unknown})).status_code == 404
    assert (await owner.post(SITES, json={**NEW_SITE, "code": "PLANT A"})).status_code == 422


async def test_a_revision_of_another_project_is_not_issued_through_this_one(
    owner: AsyncClient,
) -> None:
    site = await create_site(owner)
    first = await create_project(owner, site["id"])
    second = await create_project(owner, site["id"], code="PRJ-002", name="Workshop")

    response = await owner.post(
        f"{PROJECTS}/{second['id']}/revisions/{first['open_revision_id']}/issue"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Revision not found."


# -- roles and organizations --------------------------------------------------------------


async def test_a_viewer_reads_but_writes_nothing(owner: AsyncClient, viewer: AsyncClient) -> None:
    site = await create_site(owner)
    project = await create_project(owner, site["id"])
    revision_id = project["open_revision_id"]

    assert (await viewer.get(SITES)).status_code == 200
    assert (await viewer.get(f"{PROJECTS}/{project['id']}")).json()["code"] == "PRJ-001"

    writes = [
        ("POST", SITES, {**NEW_SITE, "code": "PLANT-B"}),
        ("PATCH", f"{SITES}/{site['id']}", {"name": "Plant B"}),
        ("POST", PROJECTS, {**NEW_PROJECT, "code": "PRJ-002", "site_id": site["id"]}),
        ("PATCH", f"{PROJECTS}/{project['id']}", {"name": "Another name"}),
        ("POST", f"{PROJECTS}/{project['id']}/archive", None),
        ("POST", f"{PROJECTS}/{project['id']}/revisions", {"label": "Rev 2"}),
        ("POST", f"{PROJECTS}/{project['id']}/revisions/{revision_id}/issue", None),
    ]
    for method, path, payload in writes:
        response = await viewer.request(method, path, json=payload)
        assert response.status_code == 403, f"{method} {path} -> {response.status_code}"
        assert response.json()["detail"] == "This action needs the role ENGINEER or OWNER."


async def test_an_engineer_keeps_the_projects_but_does_not_archive_or_issue(
    engineer: AsyncClient,
) -> None:
    site = await create_site(engineer)
    project = await create_project(engineer, site["id"])
    revision_id = project["open_revision_id"]
    assert project["revisions"][0]["created_by"] == f"Test Engineer ({ENGINEER_EMAIL})"

    assert (
        await engineer.post(f"{PROJECTS}/{project['id']}/revisions", json={"label": "Rev 2"})
    ).status_code == 201
    assert (
        await engineer.patch(f"{PROJECTS}/{project['id']}", json={"name": "Pump House B"})
    ).status_code == 200

    for path in (
        f"{PROJECTS}/{project['id']}/archive",
        f"{PROJECTS}/{project['id']}/revisions/{revision_id}/issue",
    ):
        response = await engineer.post(path)
        assert response.status_code == 403, f"{path} -> {response.status_code}"
        assert response.json()["detail"] == "This action needs the role OWNER."


async def test_nobody_reaches_the_project_spine_without_a_session(
    anonymous_client: AsyncClient,
) -> None:
    assert (await anonymous_client.get(SITES)).status_code == 401
    assert (await anonymous_client.get(PROJECTS)).status_code == 401
    assert (await anonymous_client.post(SITES, json=NEW_SITE)).status_code == 401
    assert (await anonymous_client.get(f"{PROJECTS}/{uuid4()}")).status_code == 401


async def test_another_organization_sees_nothing_of_this_one(
    owner: AsyncClient, rival_owner: AsyncClient
) -> None:
    site = await create_site(owner)
    project = await create_project(owner, site["id"])
    revision_id = project["open_revision_id"]

    assert (await rival_owner.get(SITES)).json()["items"] == []
    assert (await rival_owner.get(PROJECTS)).json()["items"] == []
    assert (await rival_owner.get(f"{PROJECTS}/{project['id']}")).status_code == 404
    assert (
        await rival_owner.patch(f"{PROJECTS}/{project['id']}", json={"name": "Theirs now"})
    ).status_code == 404
    assert (await rival_owner.post(f"{PROJECTS}/{project['id']}/archive")).status_code == 404
    assert (
        await rival_owner.post(f"{PROJECTS}/{project['id']}/revisions/{revision_id}/issue")
    ).status_code == 404

    stolen_site = await rival_owner.post(PROJECTS, json={**NEW_PROJECT, "site_id": site["id"]})
    assert stolen_site.status_code == 404
    assert stolen_site.json()["detail"] == "Site not found."

    assert (
        await rival_owner.patch(f"{SITES}/{site['id']}", json={"name": "Theirs"})
    ).status_code == 404
