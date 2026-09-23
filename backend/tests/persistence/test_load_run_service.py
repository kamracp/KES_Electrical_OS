"""Service tests for LoadRunService (EOS-02, Master Prompt A15 (d) and A11)."""

from collections.abc import AsyncIterator
from typing import Any
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.domain.electrical.jurisdiction import JurisdictionProfile
from app.models.identity import Organization
from app.repositories.calculation_run import CalculationRunRepository
from app.repositories.project import ProjectRepository
from app.schemas.calculation_run import LoadRunCreateRequest
from app.services.calculation_run import (
    LOAD_ENGINE_VERSION,
    LOAD_MODULE_CODE,
    LoadRunService,
)
from app.services.project import (
    ProjectConflictError,
    ProjectNotFoundError,
    ProjectService,
)

pytestmark = pytest.mark.persistence

ACTOR = "Test Engineer (engineer@example.com)"
STUDY_CODE = "LOAD-001"


@pytest_asyncio.fixture
async def service(test_engine: AsyncEngine) -> AsyncIterator[LoadRunService]:
    factory = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as db:
        yield LoadRunService(
            CalculationRunRepository(db),
            ProjectService(ProjectRepository(db)),
        )


async def seed_organization(service: LoadRunService, code: str = "KES") -> Organization:
    organization = Organization(code=code, name=f"Organization {code}")
    service.projects.repository.add(organization)
    await service.projects.repository.commit()
    return organization


async def seed_open_revision(
    service: LoadRunService,
    organization: Organization,
    *,
    jurisdiction_profile: JurisdictionProfile = JurisdictionProfile.IN,
    project_code: str = "PRJ-001",
    site_code: str = "PLANT-1",
):
    """Create a site, a project and its open revision 1."""

    site = await service.projects.create_site(
        organization.id, code=site_code, name="Plant 1", location=None
    )
    _, revision = await service.projects.create_project(
        organization.id,
        site_id=site.id,
        code=project_code,
        name="Pump House",
        jurisdiction_profile=jurisdiction_profile,
        client_name="Client Ltd",
        created_by=ACTOR,
    )
    return revision


def motor(**overrides: Any) -> dict[str, Any]:
    """One fully established three-phase motor load."""

    load: dict[str, Any] = {
        "code": "MTR-001",
        "name": "Process Water Pump",
        "quantity": 2,
        "rated_power_kw": "15",
        "phase_system": "THREE_PHASE",
        "voltage_v": "415",
        "power_factor": "0.85",
        "efficiency": "0.92",
        "utilization_factor": "0.80",
        "demand_factor": "0.90",
        "power_basis": "MECHANICAL_OUTPUT",
    }
    load.update(overrides)

    return load


def payload(
    *,
    loads: list[dict[str, Any]] | None = None,
    coincidence_factor: str | None = "0.90",
    jurisdiction_profile: str = "IN",
    project_revision_id: Any = None,
) -> LoadRunCreateRequest:
    """Build a load run request for the standard study code."""

    study: dict[str, Any] = {
        "code": STUDY_CODE,
        "name": "Process Pump Loads",
        "loads": loads if loads is not None else [motor()],
        "jurisdiction_profile": jurisdiction_profile,
    }
    if coincidence_factor is not None:
        study["coincidence_factor"] = coincidence_factor

    request: dict[str, Any] = {"study": study}
    if project_revision_id is not None:
        request["project_revision_id"] = str(project_revision_id)

    return LoadRunCreateRequest.model_validate(request)


async def test_first_run_is_revision_one(service: LoadRunService) -> None:
    """A load run lands in the generic table as an EOS-02 LOAD_DEMAND revision."""

    kes = await seed_organization(service)

    run, response, created = await service.create(
        payload(), calculated_by=ACTOR, organization_id=kes.id
    )

    assert created is True
    assert run.revision_number == 1
    assert run.module_code == LOAD_MODULE_CODE
    assert run.calculation_type == "LOAD_DEMAND"
    assert run.calculation_key == STUDY_CODE
    assert run.engine_version == LOAD_ENGINE_VERSION
    assert run.design_check_status == "VALID"
    assert run.jurisdiction_profile == "IN"
    assert run.calculated_by == ACTOR
    assert run.project_revision_id is None
    assert response.group_code == STUDY_CODE


async def test_the_references_snapshot_carries_the_profile_state(service: LoadRunService) -> None:
    """The load engine cites no reference, so the profile's state is frozen instead."""

    kes = await seed_organization(service)

    run, _, _ = await service.create(payload(), calculated_by=ACTOR, organization_id=kes.id)

    assert run.references_snapshot["jurisdiction_profile"] == "IN"
    assert run.references_snapshot["reference_verification_status"] == "UNVERIFIED"
    assert run.reference_verification_status == "UNVERIFIED"
    assert run.references_snapshot["assumptions"] == [
        "The group coincidence factor is applied equally to active and reactive demand."
    ]


async def test_an_identical_study_reuses_the_stored_run(service: LoadRunService) -> None:
    """A11: the same evidence and engine version return the stored revision."""

    kes = await seed_organization(service)

    first, _, first_created = await service.create(
        payload(), calculated_by=ACTOR, organization_id=kes.id
    )
    second, _, second_created = await service.create(
        payload(), calculated_by=ACTOR, organization_id=kes.id
    )

    assert first_created is True
    assert second_created is False
    assert second.id == first.id
    assert second.revision_number == 1


async def test_a_changed_study_creates_revision_two(service: LoadRunService) -> None:
    """Different evidence is a new revision, never an overwrite."""

    kes = await seed_organization(service)

    await service.create(payload(), calculated_by=ACTOR, organization_id=kes.id)
    changed, _, created = await service.create(
        payload(coincidence_factor="0.80"), calculated_by=ACTOR, organization_id=kes.id
    )

    assert created is True
    assert changed.revision_number == 2


async def test_returning_to_an_earlier_study_creates_a_third_revision(
    service: LoadRunService,
) -> None:
    """A11 compares against the latest revision only: A then B then A is three revisions."""

    kes = await seed_organization(service)

    await service.create(payload(), calculated_by=ACTOR, organization_id=kes.id)
    await service.create(
        payload(coincidence_factor="0.80"), calculated_by=ACTOR, organization_id=kes.id
    )
    again, _, created = await service.create(payload(), calculated_by=ACTOR, organization_id=kes.id)

    assert created is True
    assert again.revision_number == 3


async def test_a_blank_coincidence_factor_is_stored_as_review_required(
    service: LoadRunService,
) -> None:
    """A15 (a): an unestablished factor reaches the run row as REVIEW_REQUIRED."""

    kes = await seed_organization(service)

    run, response, _ = await service.create(
        payload(coincidence_factor=None), calculated_by=ACTOR, organization_id=kes.id
    )

    assert run.design_check_status == "REVIEW_REQUIRED"
    assert str(response.status) == "REVIEW_REQUIRED"
    assert [warning["code"] for warning in run.warnings_snapshot] == [
        "COINCIDENCE_FACTOR_NOT_ESTABLISHED"
    ]


async def test_an_open_revision_links_the_run_to_the_project(service: LoadRunService) -> None:
    """A chosen open revision scopes the run to that project."""

    kes = await seed_organization(service)
    revision = await seed_open_revision(service, kes)

    run, _, created = await service.create(
        payload(project_revision_id=revision.id),
        calculated_by=ACTOR,
        organization_id=kes.id,
    )

    assert created is True
    assert run.project_revision_id == revision.id
    assert run.revision_number == 1


async def test_a_profile_mismatch_is_refused(service: LoadRunService) -> None:
    """A15 (c): the study's profile must match the project's design basis."""

    kes = await seed_organization(service)
    revision = await seed_open_revision(service, kes, jurisdiction_profile=JurisdictionProfile.IN)

    with pytest.raises(ProjectConflictError):
        await service.create(
            payload(jurisdiction_profile="US", project_revision_id=revision.id),
            calculated_by=ACTOR,
            organization_id=kes.id,
        )


async def test_another_organizations_revision_is_not_found(service: LoadRunService) -> None:
    """A revision outside the caller's organization does not exist for them."""

    kes = await seed_organization(service)
    other = await seed_organization(service, code="OTHER")
    revision = await seed_open_revision(service, other, project_code="PRJ-900", site_code="PLANT-9")

    with pytest.raises(ProjectNotFoundError):
        await service.create(
            payload(project_revision_id=revision.id),
            calculated_by=ACTOR,
            organization_id=kes.id,
        )


async def test_an_unknown_revision_is_not_found(service: LoadRunService) -> None:
    """An unknown revision id is refused before the engine runs."""

    kes = await seed_organization(service)

    with pytest.raises(ProjectNotFoundError):
        await service.create(
            payload(project_revision_id=uuid4()),
            calculated_by=ACTOR,
            organization_id=kes.id,
        )


async def test_each_scope_counts_its_own_revisions(service: LoadRunService) -> None:
    """The unassigned line and the project line number independently."""

    kes = await seed_organization(service)
    revision = await seed_open_revision(service, kes)

    unassigned, _, _ = await service.create(payload(), calculated_by=ACTOR, organization_id=kes.id)
    scoped, _, _ = await service.create(
        payload(project_revision_id=revision.id),
        calculated_by=ACTOR,
        organization_id=kes.id,
    )

    assert unassigned.revision_number == 1
    assert scoped.revision_number == 1
    assert unassigned.id != scoped.id

    assert [run.id for run in await service.list_for_key(STUDY_CODE)] == [unassigned.id]
    assert [
        run.id for run in await service.list_for_key(STUDY_CODE, project_revision_id=revision.id)
    ] == [scoped.id]


async def test_get_and_list_recent_return_the_stored_run(service: LoadRunService) -> None:
    """The run is readable by id and appears in the recent list of its scope."""

    kes = await seed_organization(service)

    run, _, _ = await service.create(payload(), calculated_by=ACTOR, organization_id=kes.id)

    assert (await service.get(run.id)) is not None
    assert [recent.id for recent in await service.list_recent()] == [run.id]
