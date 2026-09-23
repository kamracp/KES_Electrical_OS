"""Service tests for TransformerRunService (EOS-03a, Master Prompt A16 and A11)."""

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
from app.schemas.calculation_run import TransformerRunCreateRequest
from app.services.calculation_run import (
    TRANSFORMER_ENGINE_VERSION,
    TRANSFORMER_MODULE_CODE,
    TransformerRunService,
)
from app.services.project import (
    ProjectConflictError,
    ProjectNotFoundError,
    ProjectService,
)

pytestmark = pytest.mark.persistence

ACTOR = "Test Engineer (engineer@example.com)"
STUDY_CODE = "TR-001"


@pytest_asyncio.fixture
async def service(test_engine: AsyncEngine) -> AsyncIterator[TransformerRunService]:
    factory = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as db:
        yield TransformerRunService(
            CalculationRunRepository(db),
            ProjectService(ProjectRepository(db)),
        )


async def seed_organization(service: TransformerRunService, code: str = "KES") -> Organization:
    organization = Organization(code=code, name=f"Organization {code}")
    service.projects.repository.add(organization)
    await service.projects.repository.commit()
    return organization


async def seed_open_revision(
    service: TransformerRunService,
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
        name="Substation",
        jurisdiction_profile=jurisdiction_profile,
        client_name="Client Ltd",
        created_by=ACTOR,
    )
    return revision


def payload(
    *,
    design_margin_factor: str | None = "1.10",
    available_unit_ratings_kva: list[str] | None = None,
    jurisdiction_profile: str = "IN",
    project_revision_id: Any = None,
    notes: str | None = None,
) -> TransformerRunCreateRequest:
    """Build a transformer run request for the standard study code."""

    study: dict[str, Any] = {
        "code": STUDY_CODE,
        "name": "Main Transformer",
        "demand_power_kw": "800",
        "demand_power_factor": "0.80",
        "available_unit_ratings_kva": (
            available_unit_ratings_kva
            if available_unit_ratings_kva is not None
            else ["1000", "1250", "1600"]
        ),
        "future_growth_factor": "1",
        "ambient_derating_factor": "1",
        "altitude_derating_factor": "1",
        "harmonic_derating_factor": "1",
        "jurisdiction_profile": jurisdiction_profile,
    }
    if design_margin_factor is not None:
        study["design_margin_factor"] = design_margin_factor

    request: dict[str, Any] = {"study": study}
    if project_revision_id is not None:
        request["project_revision_id"] = str(project_revision_id)
    if notes is not None:
        request["notes"] = notes

    return TransformerRunCreateRequest.model_validate(request)


async def test_first_run_is_revision_one(service: TransformerRunService) -> None:
    """A transformer run lands in the generic table as an EOS-03 revision."""

    kes = await seed_organization(service)

    run, response, created = await service.create(
        payload(), calculated_by=ACTOR, organization_id=kes.id
    )

    assert created is True
    assert run.revision_number == 1
    assert run.module_code == TRANSFORMER_MODULE_CODE
    assert run.calculation_type == "TRANSFORMER_SIZING"
    assert run.calculation_key == STUDY_CODE
    assert run.engine_version == TRANSFORMER_ENGINE_VERSION
    assert run.design_check_status == "VALID"
    assert run.jurisdiction_profile == "IN"
    assert run.calculated_by == ACTOR
    assert run.project_revision_id is None
    assert response.code == STUDY_CODE
    assert response.selected_unit_rating_kva is not None


async def test_the_references_snapshot_carries_the_profile_state(
    service: TransformerRunService,
) -> None:
    """The engine cites no reference, so the profile's state is frozen instead."""

    kes = await seed_organization(service)

    run, _, _ = await service.create(payload(), calculated_by=ACTOR, organization_id=kes.id)

    assert run.references_snapshot == {
        "jurisdiction_profile": "IN",
        "reference_verification_status": "UNVERIFIED",
    }
    assert run.reference_verification_status == "UNVERIFIED"


async def test_an_identical_study_reuses_the_stored_run(service: TransformerRunService) -> None:
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


async def test_a_changed_study_creates_revision_two(service: TransformerRunService) -> None:
    """Different evidence is a new revision, never an overwrite."""

    kes = await seed_organization(service)

    await service.create(payload(), calculated_by=ACTOR, organization_id=kes.id)
    changed, _, created = await service.create(
        payload(design_margin_factor="1.20"), calculated_by=ACTOR, organization_id=kes.id
    )

    assert created is True
    assert changed.revision_number == 2


async def test_returning_to_an_earlier_study_creates_a_third_revision(
    service: TransformerRunService,
) -> None:
    """A11 compares against the latest revision only: A then B then A is three revisions."""

    kes = await seed_organization(service)

    await service.create(payload(), calculated_by=ACTOR, organization_id=kes.id)
    await service.create(
        payload(design_margin_factor="1.20"), calculated_by=ACTOR, organization_id=kes.id
    )
    again, _, created = await service.create(payload(), calculated_by=ACTOR, organization_id=kes.id)

    assert created is True
    assert again.revision_number == 3


async def test_a_blank_design_margin_is_stored_as_review_required(
    service: TransformerRunService,
) -> None:
    """A16 (a): an unestablished factor reaches the run row as REVIEW_REQUIRED."""

    kes = await seed_organization(service)

    run, response, _ = await service.create(
        payload(design_margin_factor=None), calculated_by=ACTOR, organization_id=kes.id
    )

    assert run.design_check_status == "REVIEW_REQUIRED"
    assert str(response.status) == "REVIEW_REQUIRED"
    assert [warning["code"] for warning in run.warnings_snapshot] == [
        "DESIGN_MARGIN_NOT_ESTABLISHED"
    ]
    # Sized with 1, not with the withdrawn 1.10.
    assert run.result_snapshot["design_required_kva"] == "1000.0000"


async def test_a_study_with_no_adequate_rating_is_still_a_run(
    service: TransformerRunService,
) -> None:
    """NO_SOLUTION is engineering evidence too, and is persisted as a run."""

    kes = await seed_organization(service)

    run, response, created = await service.create(
        payload(available_unit_ratings_kva=["100"]),
        calculated_by=ACTOR,
        organization_id=kes.id,
    )

    assert created is True
    assert run.design_check_status == "NO_SOLUTION"
    assert response.selected_unit_rating_kva is None
    assert "NO_STANDARD_RATING_AVAILABLE" in {warning["code"] for warning in run.warnings_snapshot}


async def test_an_open_revision_links_the_run_to_the_project(
    service: TransformerRunService,
) -> None:
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


async def test_a_profile_mismatch_is_refused(service: TransformerRunService) -> None:
    """A16: the study's profile must match the project's design basis."""

    kes = await seed_organization(service)
    revision = await seed_open_revision(service, kes, jurisdiction_profile=JurisdictionProfile.IN)

    with pytest.raises(ProjectConflictError):
        await service.create(
            payload(jurisdiction_profile="US", project_revision_id=revision.id),
            calculated_by=ACTOR,
            organization_id=kes.id,
        )


async def test_another_organizations_revision_is_not_found(
    service: TransformerRunService,
) -> None:
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


async def test_an_unknown_revision_is_not_found(service: TransformerRunService) -> None:
    """An unknown revision id is refused before the engine runs."""

    kes = await seed_organization(service)

    with pytest.raises(ProjectNotFoundError):
        await service.create(
            payload(project_revision_id=uuid4()),
            calculated_by=ACTOR,
            organization_id=kes.id,
        )


async def test_each_scope_counts_its_own_revisions(service: TransformerRunService) -> None:
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


async def test_get_and_list_recent_return_the_stored_run(
    service: TransformerRunService,
) -> None:
    """The run is readable by id and appears in the recent list of its scope."""

    kes = await seed_organization(service)

    run, _, _ = await service.create(
        payload(notes="Preliminary sizing."), calculated_by=ACTOR, organization_id=kes.id
    )

    assert run.notes == "Preliminary sizing."
    assert (await service.get(run.id)) is not None
    assert [recent.id for recent in await service.list_recent()] == [run.id]
