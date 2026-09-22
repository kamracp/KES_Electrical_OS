"""Persistence tests for ProjectRepository (EOS-01 b)."""

from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
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
from app.repositories.project import ProjectRepository

pytestmark = pytest.mark.persistence

PROFILE = JurisdictionProfile.IN.value


@pytest_asyncio.fixture
async def repo(test_engine: AsyncEngine) -> AsyncIterator[ProjectRepository]:
    factory = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as db:
        yield ProjectRepository(db)


async def seed_organization(repo: ProjectRepository, code: str = "KES") -> Organization:
    organization = Organization(code=code, name=f"Organization {code}")
    repo.add(organization)
    await repo.commit()
    return organization


async def seed_site(
    repo: ProjectRepository, organization: Organization, code: str, *, active: bool = True
) -> Site:
    site = Site(organization_id=organization.id, code=code, name=f"Site {code}", is_active=active)
    repo.add(site)
    await repo.commit()
    return site


async def seed_project(
    repo: ProjectRepository,
    organization: Organization,
    site: Site,
    code: str,
    *,
    status: str = ProjectStatus.ACTIVE.value,
) -> Project:
    project = Project(
        organization_id=organization.id,
        site_id=site.id,
        code=code,
        name=f"Project {code}",
        jurisdiction_profile=PROFILE,
        status=status,
    )
    repo.add(project)
    await repo.commit()
    return project


async def test_sites_are_listed_per_organization_active_first(repo: ProjectRepository) -> None:
    kes = await seed_organization(repo, "KES")
    other = await seed_organization(repo, "OTHER")
    await seed_site(repo, kes, "PLANT-2")
    await seed_site(repo, kes, "PLANT-1")
    await seed_site(repo, kes, "CLOSED", active=False)
    await seed_site(repo, other, "PLANT-1")

    active = await repo.list_sites(kes.id)
    everything = await repo.list_sites(kes.id, include_inactive=True)

    assert [site.code for site in active] == ["PLANT-1", "PLANT-2"]
    assert [site.code for site in everything] == ["CLOSED", "PLANT-1", "PLANT-2"]


async def test_site_by_code_is_scoped_to_the_organization(repo: ProjectRepository) -> None:
    kes = await seed_organization(repo, "KES")
    other = await seed_organization(repo, "OTHER")
    site = await seed_site(repo, kes, "PLANT-1")
    await seed_site(repo, other, "PLANT-1")

    found = await repo.get_site_by_code(kes.id, "PLANT-1")
    assert found is not None and found.id == site.id
    assert await repo.get_site_by_code(kes.id, "MISSING") is None


async def test_projects_are_listed_per_organization_and_status(repo: ProjectRepository) -> None:
    kes = await seed_organization(repo, "KES")
    other = await seed_organization(repo, "OTHER")
    site = await seed_site(repo, kes, "PLANT-1")
    other_site = await seed_site(repo, other, "PLANT-1")
    await seed_project(repo, kes, site, "PRJ-002")
    await seed_project(repo, kes, site, "PRJ-001")
    await seed_project(repo, kes, site, "PRJ-OLD", status=ProjectStatus.ARCHIVED.value)
    await seed_project(repo, other, other_site, "PRJ-001")

    everything = await repo.list_projects(kes.id)
    active = await repo.list_projects(kes.id, status=ProjectStatus.ACTIVE.value)

    assert [project.code for project in everything] == ["PRJ-001", "PRJ-002", "PRJ-OLD"]
    assert [project.code for project in active] == ["PRJ-001", "PRJ-002"]
    assert await repo.count_projects_of_site(site.id) == 3


async def test_project_by_code_is_scoped_to_the_organization(repo: ProjectRepository) -> None:
    kes = await seed_organization(repo, "KES")
    other = await seed_organization(repo, "OTHER")
    site = await seed_site(repo, kes, "PLANT-1")
    other_site = await seed_site(repo, other, "PLANT-1")
    project = await seed_project(repo, kes, site, "PRJ-001")
    await seed_project(repo, other, other_site, "PRJ-001")

    found = await repo.get_project_by_code(kes.id, "PRJ-001")
    assert found is not None and found.id == project.id
    assert await repo.get_project_by_code(kes.id, "PRJ-404") is None


async def test_revisions_newest_first_and_open_revision_lookup(repo: ProjectRepository) -> None:
    kes = await seed_organization(repo)
    site = await seed_site(repo, kes, "PLANT-1")
    project = await seed_project(repo, kes, site, "PRJ-001")
    assert await repo.get_next_revision_number(project.id) == 1
    assert await repo.get_open_revision(project.id) is None

    repo.add(
        ProjectRevision(
            project_id=project.id,
            revision_number=1,
            label="Rev 1",
            status=ProjectRevisionStatus.SUPERSEDED.value,
        ),
        ProjectRevision(project_id=project.id, revision_number=2, label="Rev 2"),
    )
    await repo.commit()

    revisions = await repo.list_revisions(project.id)
    open_revision = await repo.get_open_revision(project.id)

    assert [revision.revision_number for revision in revisions] == [2, 1]
    assert open_revision is not None and open_revision.revision_number == 2
    assert await repo.get_next_revision_number(project.id) == 3


async def test_project_with_first_revision_is_one_unit_of_work(repo: ProjectRepository) -> None:
    kes = await seed_organization(repo)
    site = await seed_site(repo, kes, "PLANT-1")
    project = Project(
        organization_id=kes.id,
        site_id=site.id,
        code="PRJ-001",
        name="Project",
        jurisdiction_profile=PROFILE,
    )
    repo.add(project)
    await repo.flush()
    repo.add(ProjectRevision(project_id=project.id, revision_number=1, label="Rev 1"))
    await repo.commit()

    stored = await repo.get_project(project.id)
    open_revision = await repo.get_open_revision(project.id)
    assert stored is not None
    assert open_revision is not None and open_revision.status == ProjectRevisionStatus.OPEN.value
