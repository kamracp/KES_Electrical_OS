"""API tests for persisted transformer sizing runs (EOS-03a, Master Prompt A16)."""

from collections.abc import Callable
from typing import Any

import pytest
from httpx import AsyncClient

from app.models.identity import OrganizationRole

pytestmark = pytest.mark.api

TRANSFORMER_RUNS_URL = "/api/v1/electrical/transformer-sizing/runs"
LOAD_RUNS_URL = "/api/v1/electrical/load-demand/runs"

REFERENCE_FIELDS = {
    "jurisdiction_profile",
    "reference_verification_status",
}


def transformer_study(
    code: str = "TR-RUN-01",
    *,
    design_margin_factor: str | None = "1.10",
    demand_power_factor: str | None = "0.80",
) -> dict[str, Any]:
    """A valid transformer sizing study."""

    study: dict[str, Any] = {
        "code": code,
        "name": "Main Transformer",
        "demand_power_kw": "800",
        "available_unit_ratings_kva": ["1000", "1250", "1600"],
        "future_growth_factor": "1",
        "ambient_derating_factor": "1",
        "altitude_derating_factor": "1",
        "harmonic_derating_factor": "1",
        "jurisdiction_profile": "IN",
    }
    if design_margin_factor is not None:
        study["design_margin_factor"] = design_margin_factor
    if demand_power_factor is not None:
        study["demand_power_factor"] = demand_power_factor

    return study


def load_study(code: str) -> dict[str, Any]:
    """A valid load schedule, used only to create a run of another module."""

    return {
        "code": code,
        "name": "Process Pump Loads",
        "coincidence_factor": "0.90",
        "jurisdiction_profile": "IN",
        "loads": [
            {
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
        ],
    }


async def test_create_transformer_run_persists_frozen_evidence(client: AsyncClient) -> None:
    response = await client.post(
        TRANSFORMER_RUNS_URL,
        json={"study": transformer_study(), "notes": "smoke"},
    )

    assert response.status_code == 201, response.text
    body = response.json()
    run = body["run"]
    result = body["result"]
    assert run["module_code"] == "EOS-03"
    assert run["calculation_type"] == "TRANSFORMER_SIZING"
    assert run["calculation_key"] == "TR-RUN-01"
    assert run["revision_number"] == 1
    assert run["run_status"] == "COMPLETED"
    assert run["approval_status"] == "NOT_SUBMITTED"
    assert run["is_immutable"] is False
    assert run["engine_version"] == "transformer-engine 0.1.0"
    assert len(run["content_hash"]) == 64
    assert run["calculated_by"] == "Test Owner (owner@example.com)"
    assert run["notes"] == "smoke"
    assert run["project_revision_id"] is None
    assert run["design_check_status"] == result["status"] == "VALID"
    assert run["jurisdiction_profile"] == result["jurisdiction_profile"] == "IN"
    assert result["selected_unit_rating_kva"] == "1250"

    detail = await client.get(f"{TRANSFORMER_RUNS_URL}/{run['id']}")
    assert detail.status_code == 200
    stored = detail.json()
    assert stored["input_snapshot"]["code"] == "TR-RUN-01"
    assert stored["result_snapshot"] == result
    assert stored["warnings_snapshot"] == result["warnings"]
    assert set(stored["references_snapshot"]) == REFERENCE_FIELDS
    # The engine cites no reference of its own, so the profile's state is frozen.
    assert (
        stored["references_snapshot"]["reference_verification_status"]
        == run["reference_verification_status"]
        == "UNVERIFIED"
    )


async def test_identical_transformer_study_reuses_the_latest_revision(
    client: AsyncClient,
) -> None:
    first = await client.post(TRANSFORMER_RUNS_URL, json={"study": transformer_study("TR-RUN-02")})
    second = await client.post(TRANSFORMER_RUNS_URL, json={"study": transformer_study("TR-RUN-02")})
    # A11: unchanged evidence and engine version create no new revision.
    assert first.status_code == 201, first.text
    assert second.status_code == 200, second.text
    assert second.json()["run"]["id"] == first.json()["run"]["id"]
    assert second.json()["run"]["revision_number"] == 1
    assert second.json()["result"] == first.json()["result"]

    listed = await client.get(TRANSFORMER_RUNS_URL, params={"calculation_key": "TR-RUN-02"})
    assert listed.status_code == 200
    assert [item["revision_number"] for item in listed.json()["items"]] == [1]


async def test_changed_transformer_study_creates_a_new_revision_and_lists_by_key(
    client: AsyncClient,
) -> None:
    original = transformer_study("TR-RUN-05")
    changed = transformer_study("TR-RUN-05", design_margin_factor="1.20")

    first = await client.post(TRANSFORMER_RUNS_URL, json={"study": original})
    second = await client.post(TRANSFORMER_RUNS_URL, json={"study": changed})
    # Returning to the first inputs differs from the latest revision, so it is a new one.
    third = await client.post(TRANSFORMER_RUNS_URL, json={"study": original})
    assert [r.status_code for r in (first, second, third)] == [201, 201, 201]
    assert [r.json()["run"]["revision_number"] for r in (first, second, third)] == [1, 2, 3]
    assert second.json()["run"]["content_hash"] != first.json()["run"]["content_hash"]
    assert third.json()["run"]["content_hash"] == first.json()["run"]["content_hash"]

    listed = await client.get(TRANSFORMER_RUNS_URL, params={"calculation_key": "TR-RUN-05"})
    assert listed.status_code == 200
    assert [item["revision_number"] for item in listed.json()["items"]] == [3, 2, 1]


async def test_missing_transformer_run_returns_404(client: AsyncClient) -> None:
    missing = await client.get(f"{TRANSFORMER_RUNS_URL}/00000000-0000-0000-0000-000000000000")

    assert missing.status_code == 404
    assert "was not found" in missing.json()["detail"]


async def test_a_blank_design_margin_is_stored_as_review_required(client: AsyncClient) -> None:
    """A16 (a): the unestablished factor reaches the result and the run summary."""

    response = await client.post(
        TRANSFORMER_RUNS_URL,
        json={
            "study": transformer_study(
                "TR-RUN-06", design_margin_factor=None, demand_power_factor="1"
            )
        },
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["result"]["status"] == "REVIEW_REQUIRED"
    assert [warning["code"] for warning in body["result"]["warnings"]] == [
        "DESIGN_MARGIN_NOT_ESTABLISHED"
    ]
    assert body["run"]["design_check_status"] == "REVIEW_REQUIRED"
    # Sized with 1, not with the withdrawn 1.10.
    assert body["result"]["design_required_kva"] == "800.0000"
    assert body["result"]["design_margin_factor"] == "1"


async def test_a_study_without_a_demand_power_factor_is_refused(client: AsyncClient) -> None:
    """The refusal names the field and does not echo the submitted values."""

    response = await client.post(
        TRANSFORMER_RUNS_URL,
        json={"study": transformer_study("TR-RUN-07", demand_power_factor=None)},
    )

    assert response.status_code == 422
    assert "demand_power_factor" in response.text
    assert "Main Transformer" not in response.text


async def test_runs_are_isolated_per_module(client: AsyncClient) -> None:
    transformer = await client.post(
        TRANSFORMER_RUNS_URL, json={"study": transformer_study("TR-RUN-04")}
    )
    load = await client.post(LOAD_RUNS_URL, json={"study": load_study("LOAD-RUN-ISO")})
    assert transformer.status_code == 201, transformer.text
    assert load.status_code == 201, load.text
    transformer_id = transformer.json()["run"]["id"]
    load_id = load.json()["run"]["id"]

    # A run is only visible through its own module's endpoint.
    assert (await client.get(f"{TRANSFORMER_RUNS_URL}/{load_id}")).status_code == 404
    assert (await client.get(f"{LOAD_RUNS_URL}/{transformer_id}")).status_code == 404
    assert (await client.get(f"{TRANSFORMER_RUNS_URL}/{transformer_id}")).status_code == 200

    recent = await client.get(TRANSFORMER_RUNS_URL)
    assert recent.status_code == 200
    items = recent.json()["items"]
    assert items
    assert all(item["module_code"] == "EOS-03" for item in items)


async def test_an_anonymous_caller_reaches_nothing(anonymous_client: AsyncClient) -> None:
    created = await anonymous_client.post(TRANSFORMER_RUNS_URL, json={"study": transformer_study()})

    assert created.status_code == 401
    assert (await anonymous_client.get(TRANSFORMER_RUNS_URL)).status_code == 401


async def test_a_viewer_reads_runs_but_does_not_create_them(
    sign_in_as: Callable[[OrganizationRole], AsyncClient],
) -> None:
    engineer = sign_in_as(OrganizationRole.ENGINEER)
    created = await engineer.post(
        TRANSFORMER_RUNS_URL, json={"study": transformer_study("TR-RUN-08")}
    )
    assert created.status_code == 201, created.text

    viewer = sign_in_as(OrganizationRole.VIEWER)

    refused = await viewer.post(TRANSFORMER_RUNS_URL, json={"study": transformer_study()})
    assert refused.status_code == 403
    listed = await viewer.get(TRANSFORMER_RUNS_URL)
    assert listed.status_code == 200
    detail = await viewer.get(f"{TRANSFORMER_RUNS_URL}/{created.json()['run']['id']}")
    assert detail.status_code == 200
