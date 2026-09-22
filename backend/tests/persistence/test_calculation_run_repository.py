"""Persistence tests for the project scoping of CalculationRunRepository (EOS-01 b)."""

from collections.abc import AsyncIterator
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.models.calculation_run import CalculationRun, EngineeringCalculationType
from app.models.identity import Organization
from app.models.project import Project, ProjectRevision, Site
from app.repositories.calculation_run import CalculationRunRepository

pytestmark = pytest.mark.persistence

MODULE = "EOS-06"
KEY = "CBL-001"


@pytest_asyncio.fixture
async def repo(test_engine: AsyncEngine) -> AsyncIterator[CalculationRunRepository]:
    factory = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as db:
        yield CalculationRunRepository(db)


async def seed_revisions(repo: CalculationRunRepository) -> tuple[UUID, UUID]:
    """One project with two revisions; their ids are the two project scopes."""

    organization = Organization(code="KES", name="Kamra Engineering Solutions")
    repo.db.add(organization)
    await repo.db.flush()
    site = Site(organization_id=organization.id, code="PLANT-A", name="Plant A")
    repo.db.add(site)
    await repo.db.flush()
    project = Project(
        organization_id=organization.id,
        site_id=site.id,
        code="PRJ-001",
        name="Pump House",
        jurisdiction_profile="IN",
        status="ACTIVE",
    )
    repo.db.add(project)
    await repo.db.flush()
    first = ProjectRevision(project_id=project.id, revision_number=1, label="Rev 1", status="OPEN")
    second = ProjectRevision(project_id=project.id, revision_number=2, label="Rev 2", status="OPEN")
    repo.db.add_all([first, second])
    await repo.db.commit()
    return first.id, second.id


def run(
    *,
    project_revision_id: UUID | None,
    revision_number: int = 1,
    content_hash: str = "a" * 64,
    key: str = KEY,
) -> CalculationRun:
    return CalculationRun(
        project_revision_id=project_revision_id,
        module_code=MODULE,
        calculation_type=EngineeringCalculationType.CABLE_SIZING.value,
        calculation_key=key,
        revision_number=revision_number,
        engine_version="cable-engine 0.1.0",
        design_check_status="PASS",
        jurisdiction_profile="IN",
        reference_verification_status="VERIFIED",
        input_snapshot={"code": key},
        result_snapshot={"status": "PASS"},
        content_hash=content_hash,
    )


async def test_the_same_study_key_lives_in_every_scope_without_colliding(
    repo: CalculationRunRepository,
) -> None:
    first, second = await seed_revisions(repo)

    await repo.create(run(project_revision_id=None))
    await repo.create(run(project_revision_id=first))
    await repo.create(run(project_revision_id=second))

    # Revision 1 of the same study key exists three times: once outside any project and once
    # under each project revision. The two partial unique indexes allow exactly this.
    assert (await repo.get_latest_revision(MODULE, KEY)).project_revision_id is None
    assert (
        await repo.get_latest_revision(MODULE, KEY, project_revision_id=first)
    ).project_revision_id == first
    assert (
        await repo.get_latest_revision(MODULE, KEY, project_revision_id=second)
    ).project_revision_id == second


async def test_one_scope_still_refuses_the_same_key_and_revision_twice(
    repo: CalculationRunRepository,
) -> None:
    first, _second = await seed_revisions(repo)
    await repo.create(run(project_revision_id=first))

    with pytest.raises(IntegrityError):
        await repo.create(run(project_revision_id=first))
    await repo.db.rollback()


async def test_unassigned_runs_still_refuse_the_same_key_and_revision_twice(
    repo: CalculationRunRepository,
) -> None:
    await repo.create(run(project_revision_id=None))

    with pytest.raises(IntegrityError):
        await repo.create(run(project_revision_id=None))
    await repo.db.rollback()


async def test_every_scope_counts_its_own_revision_numbers(
    repo: CalculationRunRepository,
) -> None:
    first, second = await seed_revisions(repo)
    await repo.create(run(project_revision_id=None))
    await repo.create(run(project_revision_id=None, revision_number=2, content_hash="b" * 64))
    await repo.create(run(project_revision_id=first))

    assert await repo.get_next_revision_number(MODULE, KEY) == 3
    assert await repo.get_next_revision_number(MODULE, KEY, project_revision_id=first) == 2
    assert await repo.get_next_revision_number(MODULE, KEY, project_revision_id=second) == 1


async def test_the_listings_show_one_scope_at_a_time(repo: CalculationRunRepository) -> None:
    first, second = await seed_revisions(repo)
    await repo.create(run(project_revision_id=None))
    await repo.create(run(project_revision_id=first))
    await repo.create(run(project_revision_id=first, revision_number=2, content_hash="b" * 64))

    unassigned = await repo.list_by_calculation_key(MODULE, KEY)
    assert [item.revision_number for item in unassigned] == [1]
    in_first = await repo.list_by_calculation_key(MODULE, KEY, project_revision_id=first)
    assert [item.revision_number for item in in_first] == [2, 1]
    assert await repo.list_by_calculation_key(MODULE, KEY, project_revision_id=second) == []

    assert len(await repo.list_recent(MODULE)) == 1
    assert len(await repo.list_recent(MODULE, project_revision_id=first)) == 2
    assert await repo.list_recent(MODULE, project_revision_id=uuid4()) == []
