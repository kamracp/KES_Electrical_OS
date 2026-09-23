"""API tests for persisted load and demand runs (EOS-02, Master Prompt A15 (d))."""

from collections.abc import Callable
from typing import Any

import pytest
from httpx import AsyncClient

from app.models.identity import OrganizationRole

pytestmark = pytest.mark.api

LOAD_RUNS_URL = "/api/v1/electrical/load-demand/runs"
FAULT_RUNS_URL = "/api/v1/electrical/fault/runs"

REFERENCE_FIELDS = {
    "jurisdiction_profile",
    "reference_verification_status",
    "assumptions",
}


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


def load_study(
    code: str = "LOAD-RUN-01",
    *,
    coincidence_factor: str | None = "0.90",
    loads: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """A valid load schedule: several loads with a coincidence factor."""

    study: dict[str, Any] = {
        "code": code,
        "name": "Process Pump Loads",
        "loads": loads if loads is not None else [motor()],
        "jurisdiction_profile": "IN",
    }
    if coincidence_factor is not None:
        study["coincidence_factor"] = coincidence_factor

    return study


def fault_study(code: str) -> dict[str, Any]:
    """A valid fault study, used only to create a run of another module."""

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


async def test_create_load_run_persists_frozen_evidence(client: AsyncClient) -> None:
    response = await client.post(
        LOAD_RUNS_URL,
        json={"study": load_study(), "notes": "smoke"},
    )

    assert response.status_code == 201, response.text
    body = response.json()
    run = body["run"]
    result = body["result"]
    assert run["module_code"] == "EOS-02"
    assert run["calculation_type"] == "LOAD_DEMAND"
    assert run["calculation_key"] == "LOAD-RUN-01"
    assert run["revision_number"] == 1
    assert run["run_status"] == "COMPLETED"
    assert run["approval_status"] == "NOT_SUBMITTED"
    assert run["is_immutable"] is False
    assert run["engine_version"] == "load-engine 0.1.0"
    assert len(run["content_hash"]) == 64
    assert run["calculated_by"] == "Test Owner (owner@example.com)"
    assert run["notes"] == "smoke"
    assert run["project_revision_id"] is None
    # Stored values come from the JSON-mode result, never from str(enum).
    assert run["design_check_status"] == result["status"] == "VALID"
    assert run["jurisdiction_profile"] == result["jurisdiction_profile"] == "IN"
    assert result["group_code"] == "LOAD-RUN-01"
    assert result["demand_power_kw"] == "21.1304"

    detail = await client.get(f"{LOAD_RUNS_URL}/{run['id']}")
    assert detail.status_code == 200
    stored = detail.json()
    assert stored["input_snapshot"]["code"] == "LOAD-RUN-01"
    assert stored["result_snapshot"] == result
    assert stored["warnings_snapshot"] == result["warnings"]
    assert set(stored["references_snapshot"]) == REFERENCE_FIELDS
    assert stored["references_snapshot"]["jurisdiction_profile"] == result["jurisdiction_profile"]
    assert stored["references_snapshot"]["assumptions"] == result["assumptions"]
    # The load engine cites no reference of its own, so the profile's state is frozen.
    assert (
        stored["references_snapshot"]["reference_verification_status"]
        == run["reference_verification_status"]
        == "UNVERIFIED"
    )


async def test_identical_load_study_reuses_the_latest_revision(client: AsyncClient) -> None:
    first = await client.post(LOAD_RUNS_URL, json={"study": load_study("LOAD-RUN-02")})
    second = await client.post(LOAD_RUNS_URL, json={"study": load_study("LOAD-RUN-02")})
    # A11: unchanged evidence and engine version create no new revision.
    assert first.status_code == 201, first.text
    assert second.status_code == 200, second.text
    assert second.json()["run"]["id"] == first.json()["run"]["id"]
    assert second.json()["run"]["revision_number"] == 1
    assert second.json()["result"] == first.json()["result"]

    listed = await client.get(LOAD_RUNS_URL, params={"calculation_key": "LOAD-RUN-02"})
    assert listed.status_code == 200
    assert [item["revision_number"] for item in listed.json()["items"]] == [1]


async def test_changed_load_study_creates_a_new_revision_and_lists_by_key(
    client: AsyncClient,
) -> None:
    original = load_study("LOAD-RUN-05")
    changed = load_study("LOAD-RUN-05", coincidence_factor="0.80")

    first = await client.post(LOAD_RUNS_URL, json={"study": original})
    second = await client.post(LOAD_RUNS_URL, json={"study": changed})
    # Returning to the first inputs differs from the latest revision, so it is a new one.
    third = await client.post(LOAD_RUNS_URL, json={"study": original})
    assert [r.status_code for r in (first, second, third)] == [201, 201, 201]
    assert [r.json()["run"]["revision_number"] for r in (first, second, third)] == [1, 2, 3]
    assert second.json()["run"]["content_hash"] != first.json()["run"]["content_hash"]
    # Identical inputs and engine give an identical evidence hash.
    assert third.json()["run"]["content_hash"] == first.json()["run"]["content_hash"]

    listed = await client.get(LOAD_RUNS_URL, params={"calculation_key": "LOAD-RUN-05"})
    assert listed.status_code == 200
    assert [item["revision_number"] for item in listed.json()["items"]] == [3, 2, 1]


async def test_missing_load_run_returns_404(client: AsyncClient) -> None:
    missing = await client.get(f"{LOAD_RUNS_URL}/00000000-0000-0000-0000-000000000000")

    assert missing.status_code == 404
    assert "was not found" in missing.json()["detail"]


async def test_a_blank_coincidence_factor_is_stored_as_review_required(
    client: AsyncClient,
) -> None:
    """A15 (a): the unestablished factor reaches the result and the run summary."""

    response = await client.post(
        LOAD_RUNS_URL,
        json={"study": load_study("LOAD-RUN-06", coincidence_factor=None)},
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["result"]["status"] == "REVIEW_REQUIRED"
    assert [warning["code"] for warning in body["result"]["warnings"]] == [
        "COINCIDENCE_FACTOR_NOT_ESTABLISHED"
    ]
    assert body["run"]["design_check_status"] == "REVIEW_REQUIRED"
    assert body["result"]["coincidence_factor"] == "1"


async def test_an_ac_load_without_a_power_factor_is_refused(client: AsyncClient) -> None:
    """The refusal names the rule and does not echo the submitted values."""

    load = motor()
    del load["power_factor"]

    response = await client.post(
        LOAD_RUNS_URL,
        json={"study": load_study("LOAD-RUN-07", loads=[load])},
    )

    assert response.status_code == 422
    assert "power_factor is required for AC loads" in response.text
    assert "Process Water Pump" not in response.text


async def test_runs_are_isolated_per_module(client: AsyncClient) -> None:
    load = await client.post(LOAD_RUNS_URL, json={"study": load_study("LOAD-RUN-04")})
    fault = await client.post(FAULT_RUNS_URL, json={"study": fault_study("FLT-RUN-ISO")})
    assert load.status_code == 201, load.text
    assert fault.status_code == 201, fault.text
    load_id = load.json()["run"]["id"]
    fault_id = fault.json()["run"]["id"]

    # A run is only visible through its own module's endpoint.
    assert (await client.get(f"{LOAD_RUNS_URL}/{fault_id}")).status_code == 404
    assert (await client.get(f"{FAULT_RUNS_URL}/{load_id}")).status_code == 404
    assert (await client.get(f"{LOAD_RUNS_URL}/{load_id}")).status_code == 200

    recent = await client.get(LOAD_RUNS_URL)
    assert recent.status_code == 200
    items = recent.json()["items"]
    assert items
    assert all(item["module_code"] == "EOS-02" for item in items)


async def test_an_anonymous_caller_reaches_nothing(anonymous_client: AsyncClient) -> None:
    assert (
        await anonymous_client.post(LOAD_RUNS_URL, json={"study": load_study()})
    ).status_code == 401
    assert (await anonymous_client.get(LOAD_RUNS_URL)).status_code == 401


async def test_a_viewer_reads_runs_but_does_not_create_them(
    sign_in_as: Callable[[OrganizationRole], AsyncClient],
) -> None:
    engineer = sign_in_as(OrganizationRole.ENGINEER)
    created = await engineer.post(LOAD_RUNS_URL, json={"study": load_study("LOAD-RUN-08")})
    assert created.status_code == 201, created.text

    viewer = sign_in_as(OrganizationRole.VIEWER)

    assert (await viewer.post(LOAD_RUNS_URL, json={"study": load_study()})).status_code == 403
    listed = await viewer.get(LOAD_RUNS_URL)
    assert listed.status_code == 200
    assert (await viewer.get(f"{LOAD_RUNS_URL}/{created.json()['run']['id']}")).status_code == 200
