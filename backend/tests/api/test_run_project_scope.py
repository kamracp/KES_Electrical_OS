"""API tests for runs that belong to a project revision (EOS-01 b)."""

from collections.abc import Callable
from typing import Any
from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.api.authentication import require_user
from app.main import app
from app.models.identity import OrganizationRole
from app.services.auth import AuthenticatedSession

pytestmark = pytest.mark.api

SITES = "/api/v1/sites"
PROJECTS = "/api/v1/projects"
CABLE_RUNS = "/api/v1/electrical/cable/runs"
FAULT_RUNS = "/api/v1/electrical/fault/runs"


def cable_study(code: str = "CBL-PRJ-01", profile: str = "IN") -> dict[str, Any]:
    return {
        "code": code,
        "name": "Feeder to MCC-1",
        "jurisdiction_profile": profile,
        "circuit": {
            "design_current_a": "250",
            "nominal_voltage_v": "415",
            "route_length_m": "120",
            "system": "THREE_PHASE_FOUR_WIRE",
            "power_factor": "0.85",
            "allowable_voltage_drop_percent": "5",
        },
        "cable": {
            "conductor_material": "COPPER",
            "insulation_material": "XLPE",
            "construction": "MULTICORE",
            "arrangement": "MULTICORE",
            "number_of_loaded_conductors": 3,
            "parallel_runs": 1,
            "neutral_required": True,
        },
        "installation": {
            "method": "CABLE_LADDER",
            "ambient_temperature_c": "45",
            "ambient_derating_factor": "0.87",
            "grouping_derating_factor": "0.80",
            "thermal_insulation_factor": "1",
            "depth_derating_factor": "1",
            "soil_thermal_resistivity_factor": "1",
            "grouped_circuits": 3,
        },
        "size_schedule": {
            "phase_sizes_mm2": ["70", "95", "120", "150", "185", "240"],
            "neutral_sizes_mm2": ["70", "95", "120", "150", "185", "240"],
            "protective_sizes_mm2": ["35", "50", "70", "95", "120"],
        },
    }


def fault_study(code: str = "FLT-PRJ-01") -> dict[str, Any]:
    return {
        "code": code,
        "name": "Main 11 kV Bus Short Circuit Study",
        "calculation_case": "MAXIMUM",
        "fault": {"bus_code": "BUS-01", "fault_type": "THREE_PHASE", "clearing_time_s": "0.20"},
        "buses": [
            {
                "code": "BUS-01",
                "name": "11 kV Switchboard Bus",
                "nominal_voltage_v": "11000",
                "voltage_factor_max": "1.10",
                "voltage_factor_min": "0.95",
                "neutral_earthing_mode": "SOLIDLY_EARTHED",
            }
        ],
        "sources": [
            {
                "code": "GRID-01",
                "name": "Utility 11 kV Incomer",
                "bus_code": "BUS-01",
                "source_type": "UTILITY_GRID",
                "representation": "VOLTAGE_BEHIND_IMPEDANCE",
                "positive_sequence_impedance": {"resistance_ohm": "0.10", "reactance_ohm": "0.20"},
                "negative_sequence_impedance": {"resistance_ohm": "0.10", "reactance_ohm": "0.20"},
                "zero_sequence_impedance": {"resistance_ohm": "0.20", "reactance_ohm": "0.40"},
                "in_service": True,
            }
        ],
        "branches": [],
        "frequency_hz": "50",
    }


@pytest.fixture
def act_as(
    anonymous_client: AsyncClient,
    make_identity: Callable[[OrganizationRole], AuthenticatedSession],
) -> Callable[[str], AsyncClient]:
    """Sign the shared client in as the owner of the named organization, and back again."""

    people: dict[str, AuthenticatedSession] = {}

    def use(organization: str) -> AsyncClient:
        identity = people.setdefault(organization, make_identity(OrganizationRole.OWNER))
        app.dependency_overrides[require_user] = lambda: identity
        return anonymous_client

    return use


async def open_project(
    client: AsyncClient, *, code: str = "PRJ-001", profile: str = "IN"
) -> dict[str, Any]:
    """A site, a project and its open revision 1, created through the project API."""

    site = await client.post(SITES, json={"code": f"SITE-{code}", "name": f"Site {code}"})
    assert site.status_code == 201, site.text
    project = await client.post(
        PROJECTS,
        json={
            "site_id": site.json()["id"],
            "code": code,
            "name": "Pump House",
            "jurisdiction_profile": profile,
        },
    )
    assert project.status_code == 201, project.text
    return project.json()


# -- a run inside a project ---------------------------------------------------------------


async def test_a_run_under_the_open_revision_carries_the_revision_id(
    act_as: Callable[[str], AsyncClient],
) -> None:
    client = act_as("kes")
    project = await open_project(client)
    revision_id = project["open_revision_id"]

    response = await client.post(
        CABLE_RUNS, json={"study": cable_study(), "project_revision_id": revision_id}
    )

    assert response.status_code == 201, response.text
    run = response.json()["run"]
    assert run["project_revision_id"] == revision_id
    assert run["revision_number"] == 1

    in_revision = await client.get(CABLE_RUNS, params={"project_revision_id": revision_id})
    assert [item["id"] for item in in_revision.json()["items"]] == [run["id"]]
    # Without the revision the list shows the runs that belong to no project.
    assert (await client.get(CABLE_RUNS)).json()["items"] == []


async def test_the_same_study_in_the_same_revision_reuses_the_run(
    act_as: Callable[[str], AsyncClient],
) -> None:
    client = act_as("kes")
    revision_id = (await open_project(client))["open_revision_id"]
    payload = {"study": fault_study(), "project_revision_id": revision_id}

    first = await client.post(FAULT_RUNS, json=payload)
    second = await client.post(FAULT_RUNS, json=payload)

    # A11 inside one scope: unchanged evidence creates no second revision.
    assert first.status_code == 201, first.text
    assert second.status_code == 200, second.text
    assert second.json()["run"]["id"] == first.json()["run"]["id"]


async def test_two_revisions_number_the_same_study_key_on_their_own(
    act_as: Callable[[str], AsyncClient],
) -> None:
    client = act_as("kes")
    project = await open_project(client)
    first_revision = project["open_revision_id"]

    # The study is run in revision 1; revision 2 then supersedes it and repeats the study.
    in_first = await client.post(
        CABLE_RUNS, json={"study": cable_study(), "project_revision_id": first_revision}
    )
    next_revision = await client.post(
        f"{PROJECTS}/{project['id']}/revisions", json={"label": "Rev 2"}
    )
    assert next_revision.status_code == 201, next_revision.text
    second_revision = next_revision.json()["id"]
    in_second = await client.post(
        CABLE_RUNS, json={"study": cable_study(), "project_revision_id": second_revision}
    )
    unassigned = await client.post(CABLE_RUNS, json={"study": cable_study()})

    assert [r.status_code for r in (in_first, in_second, unassigned)] == [201, 201, 201]
    # The same study code and the same evidence: revision 1 of three separate scopes.
    assert [r.json()["run"]["revision_number"] for r in (in_first, in_second, unassigned)] == [
        1,
        1,
        1,
    ]
    assert len({r.json()["run"]["id"] for r in (in_first, in_second, unassigned)}) == 3
    assert unassigned.json()["run"]["project_revision_id"] is None


async def test_a_run_without_a_revision_stays_outside_every_project(
    act_as: Callable[[str], AsyncClient],
) -> None:
    client = act_as("kes")

    response = await client.post(CABLE_RUNS, json={"study": cable_study(), "notes": "no project"})

    assert response.status_code == 201, response.text
    assert response.json()["run"]["project_revision_id"] is None
    assert [item["id"] for item in (await client.get(CABLE_RUNS)).json()["items"]] == [
        response.json()["run"]["id"]
    ]


# -- refusals -----------------------------------------------------------------------------


async def test_a_revision_of_another_organization_is_not_found(
    act_as: Callable[[str], AsyncClient],
) -> None:
    revision_id = (await open_project(act_as("kes")))["open_revision_id"]

    stranger = act_as("rival")
    response = await stranger.post(
        CABLE_RUNS, json={"study": cable_study(), "project_revision_id": revision_id}
    )

    assert response.status_code == 404
    # The revision exists, but its project belongs to another organization: not found.
    assert response.json()["detail"] == "Project not found."
    listed = await stranger.get(CABLE_RUNS, params={"project_revision_id": revision_id})
    assert listed.status_code == 404
    assert (
        await stranger.post(
            CABLE_RUNS, json={"study": cable_study(), "project_revision_id": str(uuid4())}
        )
    ).status_code == 404


async def test_an_issued_revision_takes_no_more_runs(
    act_as: Callable[[str], AsyncClient],
) -> None:
    client = act_as("kes")
    project = await open_project(client)
    revision_id = project["open_revision_id"]
    issued = await client.post(f"{PROJECTS}/{project['id']}/revisions/{revision_id}/issue")
    assert issued.status_code == 200, issued.text

    response = await client.post(
        CABLE_RUNS, json={"study": cable_study(), "project_revision_id": revision_id}
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Runs can only be added to the open revision."


async def test_an_archived_project_takes_no_more_runs(
    act_as: Callable[[str], AsyncClient],
) -> None:
    client = act_as("kes")
    project = await open_project(client)
    archived = await client.post(f"{PROJECTS}/{project['id']}/archive")
    assert archived.status_code == 200, archived.text

    response = await client.post(
        CABLE_RUNS,
        json={"study": cable_study(), "project_revision_id": project["open_revision_id"]},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "The project is archived; runs cannot be added."


async def test_a_study_of_another_jurisdiction_profile_is_refused(
    act_as: Callable[[str], AsyncClient],
) -> None:
    client = act_as("kes")
    revision_id = (await open_project(client, profile="IN"))["open_revision_id"]

    response = await client.post(
        CABLE_RUNS,
        json={"study": cable_study(profile="IEC"), "project_revision_id": revision_id},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "The study's jurisdiction profile must match the project's."
    # The study is refused before the engine runs, so nothing was stored.
    assert (await client.get(CABLE_RUNS, params={"project_revision_id": revision_id})).json()[
        "items"
    ] == []


# -- the project and revision named on a run ----------------------------------------------


async def test_a_run_names_its_project_and_revision(
    act_as: Callable[[str], AsyncClient],
) -> None:
    client = act_as("kes")
    project = await open_project(client, code="PRJ-009")
    revision_id = project["open_revision_id"]

    created = await client.post(
        CABLE_RUNS, json={"study": cable_study(), "project_revision_id": revision_id}
    )
    assert created.status_code == 201, created.text

    summary = created.json()["run"]["project"]
    assert summary == {
        "revision_id": revision_id,
        "revision_number": 1,
        "revision_label": "Rev 1",
        "project_id": project["id"],
        "project_code": "PRJ-009",
        "project_name": "Pump House",
    }
    # The raw id stays next to the names, for the frontend and for a later run filter.
    assert created.json()["run"]["project_revision_id"] == revision_id

    detail = await client.get(f"{CABLE_RUNS}/{created.json()['run']['id']}")
    assert detail.status_code == 200
    assert detail.json()["project"] == summary


async def test_a_later_revision_is_named_with_its_own_number_and_label(
    act_as: Callable[[str], AsyncClient],
) -> None:
    client = act_as("kes")
    project = await open_project(client)
    next_revision = await client.post(
        f"{PROJECTS}/{project['id']}/revisions", json={"label": "Rev 2 - client review"}
    )
    assert next_revision.status_code == 201, next_revision.text

    created = await client.post(
        FAULT_RUNS,
        json={"study": fault_study(), "project_revision_id": next_revision.json()["id"]},
    )

    assert created.status_code == 201, created.text
    summary = created.json()["run"]["project"]
    assert summary["revision_number"] == 2
    assert summary["revision_label"] == "Rev 2 - client review"
    assert summary["project_code"] == "PRJ-001"


async def test_every_item_of_a_revision_listing_carries_the_same_summary(
    act_as: Callable[[str], AsyncClient],
) -> None:
    client = act_as("kes")
    revision_id = (await open_project(client))["open_revision_id"]
    for code in ("CBL-A", "CBL-B", "CBL-C"):
        created = await client.post(
            CABLE_RUNS,
            json={"study": cable_study(code), "project_revision_id": revision_id},
        )
        assert created.status_code == 201, created.text

    listed = await client.get(CABLE_RUNS, params={"project_revision_id": revision_id})

    assert listed.status_code == 200
    items = listed.json()["items"]
    assert len(items) == 3
    assert {item["project"]["revision_id"] for item in items} == {revision_id}
    assert {item["project"]["project_code"] for item in items} == {"PRJ-001"}


async def test_a_run_outside_any_project_is_named_by_nothing(
    act_as: Callable[[str], AsyncClient],
) -> None:
    client = act_as("kes")

    created = await client.post(CABLE_RUNS, json={"study": cable_study()})
    assert created.status_code == 201, created.text
    assert created.json()["run"]["project"] is None

    detail = await client.get(f"{CABLE_RUNS}/{created.json()['run']['id']}")
    assert detail.json()["project"] is None
    listed = await client.get(CABLE_RUNS)
    assert [item["project"] for item in listed.json()["items"]] == [None]


async def test_another_organization_does_not_reach_a_run_of_this_one(
    act_as: Callable[[str], AsyncClient],
) -> None:
    client = act_as("kes")
    revision_id = (await open_project(client))["open_revision_id"]
    created = await client.post(
        CABLE_RUNS, json={"study": cable_study(), "project_revision_id": revision_id}
    )
    assert created.status_code == 201, created.text
    run_id = created.json()["run"]["id"]

    # The run belongs to a project of another organization: it is not shown, and its
    # existence is not confirmed either - the same answer as for an unknown id.
    stranger = act_as("rival")
    detail = await stranger.get(f"{CABLE_RUNS}/{run_id}")

    assert detail.status_code == 404
    assert detail.json()["detail"] == f"Cable run {run_id} was not found"
    assert (await stranger.get(f"{CABLE_RUNS}/{uuid4()}")).status_code == 404

    # Its own organization still reads it, with the project named.
    own = await act_as("kes").get(f"{CABLE_RUNS}/{run_id}")
    assert own.status_code == 200
    assert own.json()["project"]["project_code"] == "PRJ-001"


async def test_a_fault_run_of_another_organization_is_out_of_reach_too(
    act_as: Callable[[str], AsyncClient],
) -> None:
    client = act_as("kes")
    revision_id = (await open_project(client))["open_revision_id"]
    created = await client.post(
        FAULT_RUNS, json={"study": fault_study(), "project_revision_id": revision_id}
    )
    assert created.status_code == 201, created.text

    stranger = act_as("rival")

    assert (await stranger.get(f"{FAULT_RUNS}/{created.json()['run']['id']}")).status_code == 404


async def test_a_run_outside_any_project_stays_readable_by_every_member(
    act_as: Callable[[str], AsyncClient],
) -> None:
    client = act_as("kes")
    created = await client.post(CABLE_RUNS, json={"study": cable_study()})
    assert created.status_code == 201, created.text
    run_id = created.json()["run"]["id"]

    # A run that belongs to no project carries no organization; it is readable by anybody who
    # is signed in, exactly as before EOS-01 (b). This limit is recorded in the register.
    stranger = act_as("rival")
    detail = await stranger.get(f"{CABLE_RUNS}/{run_id}")

    assert detail.status_code == 200
    assert detail.json()["project"] is None
    assert detail.json()["project_revision_id"] is None
