"""Unit tests for the project spine schemas (EOS-01 b)."""

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.domain.electrical.jurisdiction import JurisdictionProfile
from app.models.project import Project, ProjectRevision, ProjectRevisionStatus, ProjectStatus, Site
from app.schemas.project import (
    ProjectCreateRequest,
    ProjectDetailResponse,
    ProjectListResponse,
    ProjectResponse,
    ProjectRevisionCreateRequest,
    ProjectRevisionListResponse,
    ProjectRevisionResponse,
    ProjectRevisionSummary,
    ProjectUpdateRequest,
    SiteCreateRequest,
    SiteListResponse,
    SiteResponse,
    SiteUpdateRequest,
)

pytestmark = pytest.mark.unit

CREATED_AT = datetime(2026, 9, 22, 9, 0, tzinfo=UTC)
SITE_ID = uuid4()
NEW_PROJECT: dict[str, Any] = {
    "site_id": str(SITE_ID),
    "code": "PRJ-001",
    "name": "Pump House",
    "jurisdiction_profile": "IN",
}


def _site() -> Site:
    return Site(
        id=uuid4(),
        organization_id=uuid4(),
        code="PLANT-A",
        name="Plant A",
        location="Ludhiana",
        is_active=True,
        created_at=CREATED_AT,
        updated_at=CREATED_AT,
    )


def _project() -> Project:
    return Project(
        id=uuid4(),
        organization_id=uuid4(),
        site_id=SITE_ID,
        code="PRJ-001",
        name="Pump House",
        client_name="Northern Mills",
        jurisdiction_profile=JurisdictionProfile.IN.value,
        status=ProjectStatus.ACTIVE.value,
        description="Feeder study for the pump house.",
        created_at=CREATED_AT,
        updated_at=CREATED_AT,
    )


def _revision(project_id: object, number: int = 1) -> ProjectRevision:
    return ProjectRevision(
        id=uuid4(),
        project_id=project_id,
        revision_number=number,
        label=f"Rev {number}",
        status=ProjectRevisionStatus.OPEN.value,
        created_by="owner@example.com",
        created_at=CREATED_AT,
        updated_at=CREATED_AT,
    )


# -- requests -----------------------------------------------------------------------------


def test_site_create_cleans_the_code_the_name_and_the_location() -> None:
    request = SiteCreateRequest.model_validate(
        {"code": "  PLANT-A ", "name": "  Plant   A ", "location": " Ludhiana,  Punjab "}
    )

    assert request.code == "PLANT-A"
    assert request.name == "Plant A"
    assert request.location == "Ludhiana, Punjab"


def test_site_create_turns_a_blank_location_into_no_location() -> None:
    assert SiteCreateRequest(code="PLANT-A", name="Plant A", location="   ").location is None
    assert SiteCreateRequest(code="PLANT-A", name="Plant A").location is None


@pytest.mark.parametrize(
    "code",
    ["", "   ", "PLANT A", "PLANT/A", "-PLANT", "A" * 41],
    ids=["blank", "spaces only", "inner space", "slash", "leading dash", "41 characters"],
)
def test_site_create_rejects_a_bad_code(code: str) -> None:
    with pytest.raises(ValidationError):
        SiteCreateRequest.model_validate({"code": code, "name": "Plant A"})


def test_a_bad_code_says_what_is_allowed() -> None:
    with pytest.raises(ValidationError, match="letters, digits, dot, dash or underscore"):
        SiteCreateRequest.model_validate({"code": "PLANT/A", "name": "Plant A"})


def test_site_create_accepts_dots_dashes_and_underscores() -> None:
    assert SiteCreateRequest(code="A1.2_B-3", name="Plant A").code == "A1.2_B-3"


def test_site_create_rejects_a_blank_name_and_an_unknown_field() -> None:
    with pytest.raises(ValidationError, match="Name is required"):
        SiteCreateRequest.model_validate({"code": "PLANT-A", "name": "   "})
    with pytest.raises(ValidationError):
        SiteCreateRequest.model_validate(
            {"code": "PLANT-A", "name": "Plant A", "organization_id": str(uuid4())}
        )


def test_update_requests_change_nothing_by_default() -> None:
    site_update = SiteUpdateRequest()
    project_update = ProjectUpdateRequest()

    assert (site_update.name, site_update.location, site_update.is_active) == (None, None, None)
    assert (project_update.name, project_update.client_name) == (None, None)
    assert project_update.description is None


def test_update_requests_clean_what_is_sent_and_refuse_unknown_fields() -> None:
    assert SiteUpdateRequest(name="  Plant   B ", is_active=False).name == "Plant B"
    assert ProjectUpdateRequest(client_name="  ").client_name is None
    assert ProjectUpdateRequest(description=" line one\n\nline two ").description == (
        "line one\n\nline two"
    )
    with pytest.raises(ValidationError):
        ProjectUpdateRequest.model_validate({"code": "PRJ-002"})


def test_project_create_cleans_its_text_and_opens_rev_1_by_default() -> None:
    request = ProjectCreateRequest.model_validate(
        {
            **NEW_PROJECT,
            "code": " prj-001 ",
            "name": "  Pump   House ",
            "client_name": "  Northern   Mills ",
            "description": "   ",
        }
    )

    assert request.site_id == SITE_ID
    assert request.code == "prj-001"
    assert request.name == "Pump House"
    assert request.client_name == "Northern Mills"
    assert request.description is None
    assert request.jurisdiction_profile is JurisdictionProfile.IN
    assert request.first_revision_label == "Rev 1"


def test_project_create_rejects_an_unknown_jurisdiction_profile() -> None:
    with pytest.raises(ValidationError):
        ProjectCreateRequest.model_validate({**NEW_PROJECT, "jurisdiction_profile": "MARS"})


def test_project_create_rejects_a_blank_first_revision_label() -> None:
    with pytest.raises(ValidationError, match="Label is required"):
        ProjectCreateRequest.model_validate({**NEW_PROJECT, "first_revision_label": "  "})


def test_revision_create_needs_a_label_and_cleans_it() -> None:
    with pytest.raises(ValidationError):
        ProjectRevisionCreateRequest.model_validate({})
    with pytest.raises(ValidationError, match="Label is required"):
        ProjectRevisionCreateRequest.model_validate({"label": " \t "})

    request = ProjectRevisionCreateRequest(label="  Rev   2 ", notes="  ")

    assert request.label == "Rev 2"
    assert request.notes is None


# -- responses ----------------------------------------------------------------------------


def test_site_response_is_built_from_the_model_without_the_organization() -> None:
    site = _site()

    response = SiteResponse.model_validate(site)

    assert response.code == "PLANT-A"
    assert response.location == "Ludhiana"
    assert response.is_active is True
    assert "organization_id" not in response.model_dump()
    assert SiteListResponse(items=[response]).items[0].id == site.id


def test_project_response_carries_the_enums_not_plain_strings() -> None:
    project = _project()

    response = ProjectResponse.model_validate(project)

    assert response.jurisdiction_profile is JurisdictionProfile.IN
    assert response.status is ProjectStatus.ACTIVE
    assert response.site_id == SITE_ID
    assert response.model_dump(mode="json")["status"] == "ACTIVE"
    assert ProjectListResponse(items=[response]).items[0].code == "PRJ-001"


def test_revision_response_is_built_from_the_model() -> None:
    project = _project()
    revision = _revision(project.id)

    response = ProjectRevisionResponse.model_validate(revision)

    assert response.revision_number == 1
    assert response.status is ProjectRevisionStatus.OPEN
    assert response.created_by == "owner@example.com"
    assert response.issued_at is None
    assert response.notes is None
    assert ProjectRevisionListResponse(items=[response]).items[0].label == "Rev 1"


def test_project_detail_lists_the_revisions_newest_first_with_the_open_one() -> None:
    project = _project()
    first = _revision(project.id, 1)
    first.status = ProjectRevisionStatus.SUPERSEDED.value
    second = _revision(project.id, 2)

    revisions = [ProjectRevisionResponse.model_validate(r) for r in (second, first)]
    response = ProjectDetailResponse(
        **ProjectResponse.model_validate(project).model_dump(),
        revisions=revisions,
        open_revision_id=second.id,
    )

    assert [r.revision_number for r in response.revisions] == [2, 1]
    assert response.open_revision_id == second.id
    assert response.code == "PRJ-001"


def test_revision_summary_names_the_project_and_the_revision_of_a_run() -> None:
    project = _project()
    revision = _revision(project.id, 2)

    summary = ProjectRevisionSummary(
        revision_id=revision.id,
        revision_number=revision.revision_number,
        revision_label=revision.label,
        project_id=project.id,
        project_code=project.code,
        project_name=project.name,
    )

    assert summary.revision_label == "Rev 2"
    assert summary.project_code == "PRJ-001"
