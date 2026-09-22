"""Service tests for ProjectService (EOS-01 b)."""

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.domain.electrical.jurisdiction import JurisdictionProfile
from app.models.identity import Organization
from app.models.project import ProjectRevisionStatus, ProjectStatus
from app.repositories.project import ProjectRepository
from app.services.project import (
    ProjectConflictError,
    ProjectNotFoundError,
    ProjectService,
)

pytestmark = pytest.mark.persistence

NOW = datetime(2026, 9, 22, 12, 0, tzinfo=UTC)
ACTOR = "Test Owner (owner@example.com)"


@pytest_asyncio.fixture
async def service(test_engine: AsyncEngine) -> AsyncIterator[ProjectService]:
    factory = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as db:
        yield ProjectService(ProjectRepository(db), now=lambda: NOW)


async def seed_organization(service: ProjectService, code: str = "KES") -> Organization:
    organization = Organization(code=code, name=f"Organization {code}")
    service.repository.add(organization)
    await service.repository.commit()
    return organization


async def test_create_project_opens_revision_one(service: ProjectService) -> None:
    kes = await seed_organization(service)
    site = await service.create_site(kes.id, code=" PLANT-1 ", name="Plant 1", location=" ")

    project, revision = await service.create_project(
        kes.id,
        site_id=site.id,
        code="PRJ-001",
        name="Substation upgrade",
        jurisdiction_profile=JurisdictionProfile.IN,
        client_name="Client Ltd",
        created_by=ACTOR,
    )

    assert site.code == "PLANT-1" and site.location is None
    assert project.status == ProjectStatus.ACTIVE.value
    assert project.jurisdiction_profile == "IN"
    assert revision.revision_number == 1
    assert revision.label == "Rev 1"
    assert revision.status == ProjectRevisionStatus.OPEN.value
    assert revision.created_by == ACTOR
    assert [r.id for r in await service.list_revisions(kes.id, project.id)] == [revision.id]


async def test_duplicate_codes_are_conflicts(service: ProjectService) -> None:
    kes = await seed_organization(service)
    site = await service.create_site(kes.id, code="PLANT-1", name="Plant 1")
    await service.create_project(
        kes.id,
        site_id=site.id,
        code="PRJ-001",
        name="A",
        jurisdiction_profile=JurisdictionProfile.IN,
    )

    with pytest.raises(ProjectConflictError):
        await service.create_site(kes.id, code="PLANT-1", name="Again")
    with pytest.raises(ProjectConflictError):
        await service.create_project(
            kes.id,
            site_id=site.id,
            code="PRJ-001",
            name="B",
            jurisdiction_profile=JurisdictionProfile.IEC,
        )


async def test_blank_code_or_name_is_a_conflict(service: ProjectService) -> None:
    kes = await seed_organization(service)
    with pytest.raises(ProjectConflictError):
        await service.create_site(kes.id, code="  ", name="Plant")


async def test_site_of_another_organization_is_not_found(service: ProjectService) -> None:
    kes = await seed_organization(service, "KES")
    other = await seed_organization(service, "OTHER")
    foreign_site = await service.create_site(other.id, code="PLANT-1", name="Theirs")

    with pytest.raises(ProjectNotFoundError):
        await service.get_site(kes.id, foreign_site.id)
    with pytest.raises(ProjectNotFoundError):
        await service.create_project(
            kes.id,
            site_id=foreign_site.id,
            code="PRJ-001",
            name="Leak",
            jurisdiction_profile=JurisdictionProfile.IN,
        )
    with pytest.raises(ProjectNotFoundError):
        await service.get_project(kes.id, uuid4())


async def test_inactive_site_takes_no_new_project(service: ProjectService) -> None:
    kes = await seed_organization(service)
    site = await service.create_site(kes.id, code="PLANT-1", name="Plant 1")
    await service.update_site(kes.id, site.id, is_active=False)

    with pytest.raises(ProjectConflictError):
        await service.create_project(
            kes.id,
            site_id=site.id,
            code="PRJ-001",
            name="Late",
            jurisdiction_profile=JurisdictionProfile.IN,
        )
    assert await service.list_sites(kes.id) == []
    assert len(await service.list_sites(kes.id, include_inactive=True)) == 1


async def test_new_revision_supersedes_the_open_one(service: ProjectService) -> None:
    kes = await seed_organization(service)
    site = await service.create_site(kes.id, code="PLANT-1", name="Plant 1")
    project, first = await service.create_project(
        kes.id,
        site_id=site.id,
        code="PRJ-001",
        name="A",
        jurisdiction_profile=JurisdictionProfile.IN,
    )

    second = await service.create_revision(kes.id, project.id, label="Rev 2", created_by=ACTOR)
    await service.repository.refresh(first)

    assert second.revision_number == 2
    assert second.status == ProjectRevisionStatus.OPEN.value
    assert first.status == ProjectRevisionStatus.SUPERSEDED.value
    assert [r.revision_number for r in await service.list_revisions(kes.id, project.id)] == [2, 1]


async def test_issue_freezes_the_revision_and_a_new_one_continues(
    service: ProjectService,
) -> None:
    kes = await seed_organization(service)
    site = await service.create_site(kes.id, code="PLANT-1", name="Plant 1")
    project, first = await service.create_project(
        kes.id,
        site_id=site.id,
        code="PRJ-001",
        name="A",
        jurisdiction_profile=JurisdictionProfile.IN,
    )

    issued = await service.issue_revision(kes.id, first.id, issued_by=ACTOR)
    assert issued.status == ProjectRevisionStatus.ISSUED.value
    assert issued.issued_by == ACTOR
    # SQLite returns naive datetimes; compare on the UTC instant.
    assert issued.issued_at is not None and issued.issued_at.replace(tzinfo=UTC) == NOW
    with pytest.raises(ProjectConflictError):
        await service.issue_revision(kes.id, first.id, issued_by=ACTOR)
    with pytest.raises(ProjectConflictError):
        await service.revision_for_new_run(kes.id, first.id)

    second = await service.create_revision(kes.id, project.id, label="Rev 2")
    await service.repository.refresh(issued)
    assert issued.status == ProjectRevisionStatus.ISSUED.value
    assert second.revision_number == 2
    returned_project, returned = await service.revision_for_new_run(kes.id, second.id)
    assert returned_project.id == project.id and returned.id == second.id


async def test_archived_project_is_frozen(service: ProjectService) -> None:
    kes = await seed_organization(service)
    site = await service.create_site(kes.id, code="PLANT-1", name="Plant 1")
    project, first = await service.create_project(
        kes.id,
        site_id=site.id,
        code="PRJ-001",
        name="A",
        jurisdiction_profile=JurisdictionProfile.IN,
    )

    archived = await service.archive_project(kes.id, project.id)
    assert archived.status == ProjectStatus.ARCHIVED.value
    with pytest.raises(ProjectConflictError):
        await service.archive_project(kes.id, project.id)
    with pytest.raises(ProjectConflictError):
        await service.update_project(kes.id, project.id, name="New name")
    with pytest.raises(ProjectConflictError):
        await service.create_revision(kes.id, project.id, label="Rev 2")
    with pytest.raises(ProjectConflictError):
        await service.revision_for_new_run(kes.id, first.id)
    assert [p.code for p in await service.list_projects(kes.id, status=ProjectStatus.ACTIVE)] == []


async def test_revision_of_another_organization_is_not_found(service: ProjectService) -> None:
    kes = await seed_organization(service, "KES")
    other = await seed_organization(service, "OTHER")
    site = await service.create_site(other.id, code="PLANT-1", name="Theirs")
    _, revision = await service.create_project(
        other.id,
        site_id=site.id,
        code="PRJ-001",
        name="A",
        jurisdiction_profile=JurisdictionProfile.IN,
    )

    with pytest.raises(ProjectNotFoundError):
        await service.revision_for_new_run(kes.id, revision.id)
    with pytest.raises(ProjectNotFoundError):
        await service.issue_revision(kes.id, revision.id, issued_by=ACTOR)
