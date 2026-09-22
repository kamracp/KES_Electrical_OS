"""Persistence tests for the project spine models (EOS-01 b)."""

from collections.abc import AsyncIterator
from datetime import UTC, datetime

import pytest
import pytest_asyncio
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.domain.electrical.jurisdiction import JurisdictionProfile
from app.models.identity import Organization
from app.models.project import (
    Project,
    ProjectRevision,
    ProjectRevisionStatus,
    ProjectStatus,
    Site,
)

pytestmark = pytest.mark.persistence

PROFILE = JurisdictionProfile.IN.value


@pytest_asyncio.fixture
async def session(test_engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    factory = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as db:
        yield db


async def add_organization(db: AsyncSession, code: str = "KES") -> Organization:
    organization = Organization(code=code, name=f"Organization {code}")
    db.add(organization)
    await db.commit()
    return organization


async def add_site(db: AsyncSession, organization: Organization, code: str = "PLANT-1") -> Site:
    site = Site(organization_id=organization.id, code=code, name=f"Site {code}")
    db.add(site)
    await db.commit()
    return site


def make_project(organization: Organization, site: Site, code: str = "PRJ-001") -> Project:
    return Project(
        organization_id=organization.id,
        site_id=site.id,
        code=code,
        name=f"Project {code}",
        jurisdiction_profile=PROFILE,
    )


async def add_project(db: AsyncSession, code: str = "PRJ-001") -> Project:
    organization = await add_organization(db)
    site = await add_site(db, organization)
    project = make_project(organization, site, code)
    db.add(project)
    await db.commit()
    return project


async def test_new_rows_get_safe_defaults(session: AsyncSession) -> None:
    project = await add_project(session)
    revision = ProjectRevision(project_id=project.id, revision_number=1, label="Rev 1")
    session.add(revision)
    await session.commit()
    await session.refresh(project)
    await session.refresh(revision)

    assert project.status == ProjectStatus.ACTIVE.value
    assert project.client_name is None
    assert revision.status == ProjectRevisionStatus.OPEN.value
    assert revision.issued_by is None
    assert revision.issued_at is None
    assert revision.created_at is not None


async def test_site_code_is_unique_within_an_organization(session: AsyncSession) -> None:
    organization = await add_organization(session)
    await add_site(session, organization, "PLANT-1")
    session.add(Site(organization_id=organization.id, code="PLANT-1", name="Duplicate"))

    with pytest.raises(IntegrityError):
        await session.commit()


async def test_two_organizations_may_share_a_site_code(session: AsyncSession) -> None:
    first = await add_organization(session, "KES")
    second = await add_organization(session, "CLIENT")
    await add_site(session, first, "PLANT-1")
    await add_site(session, second, "PLANT-1")

    assert (await session.get(Site, (await add_site(session, second, "PLANT-2")).id)) is not None


async def test_project_code_is_unique_within_an_organization(session: AsyncSession) -> None:
    project = await add_project(session, "PRJ-001")
    site = await session.get(Site, project.site_id)
    organization = await session.get(Organization, project.organization_id)
    assert site is not None and organization is not None
    session.add(make_project(organization, site, "PRJ-001"))

    with pytest.raises(IntegrityError):
        await session.commit()


async def test_project_rejects_an_unknown_jurisdiction_profile(session: AsyncSession) -> None:
    organization = await add_organization(session)
    site = await add_site(session, organization)
    project = make_project(organization, site)
    project.jurisdiction_profile = "XX"
    session.add(project)

    with pytest.raises(IntegrityError):
        await session.commit()


async def test_project_rejects_an_unknown_status(session: AsyncSession) -> None:
    organization = await add_organization(session)
    site = await add_site(session, organization)
    project = make_project(organization, site)
    project.status = "DELETED"
    session.add(project)

    with pytest.raises(IntegrityError):
        await session.commit()


async def test_revision_number_is_unique_per_project(session: AsyncSession) -> None:
    project = await add_project(session)
    session.add(ProjectRevision(project_id=project.id, revision_number=1, label="Rev 1"))
    await session.commit()
    session.add(ProjectRevision(project_id=project.id, revision_number=1, label="Again"))

    with pytest.raises(IntegrityError):
        await session.commit()


async def test_revision_number_must_be_positive(session: AsyncSession) -> None:
    project = await add_project(session)
    session.add(ProjectRevision(project_id=project.id, revision_number=0, label="Rev 0"))

    with pytest.raises(IntegrityError):
        await session.commit()


async def test_issued_revision_needs_issuer_and_time(session: AsyncSession) -> None:
    project = await add_project(session)
    session.add(
        ProjectRevision(
            project_id=project.id,
            revision_number=1,
            label="Rev 1",
            status=ProjectRevisionStatus.ISSUED.value,
        )
    )

    with pytest.raises(IntegrityError):
        await session.commit()


async def test_issued_revision_with_audit_is_accepted(session: AsyncSession) -> None:
    project = await add_project(session)
    revision = ProjectRevision(
        project_id=project.id,
        revision_number=1,
        label="Rev 1",
        status=ProjectRevisionStatus.ISSUED.value,
        issued_by="Test Owner (owner@example.com)",
        issued_at=datetime.now(UTC),
    )
    session.add(revision)
    await session.commit()
    await session.refresh(revision)

    assert revision.status == ProjectRevisionStatus.ISSUED.value


async def test_project_needs_an_existing_site(session: AsyncSession) -> None:
    organization = await add_organization(session)
    site = await add_site(session, organization)
    project = make_project(organization, site)
    project.site_id = project.id  # a UUID that is not a site
    session.add(project)

    with pytest.raises(IntegrityError):
        await session.commit()
