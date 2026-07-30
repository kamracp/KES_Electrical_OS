"""
API integration tests for persistent electrical calculation runs.
KESE-S2-M3
"""

from uuid import uuid4

import pytest
from httpx import AsyncClient


BASE_URL = "/api/v1/electrical/calculation-runs"


def calculation_payload(
    *,
    calculation_key: str = "MAIN-LV-DEMAND",
    connected_power_kw: str = "250.000",
    demand_power_kw: str = "200.000",
) -> dict[str, object]:
    """Return a valid persistent calculation-run payload."""

    return {
        "calculation_key": calculation_key,
        "calculation_type": "LOAD_GROUP",
        "scenario": "NORMAL",
        "run_status": "COMPLETED",
        "engine_version": "2.0.0",
        "formula_version": "KESE-LD-1.0",
        "input_snapshot": {
            "connected_power_kw": connected_power_kw,
            "coincidence_factor": "0.80",
            "load_count": 5,
        },
        "result_snapshot": {
            "demand_power_kw": demand_power_kw,
            "status": "VALID",
        },
        "assumptions_snapshot": {
            "voltage_v": "415",
            "frequency_hz": "50",
        },
        "warnings_snapshot": [],
        "standards_snapshot": [
            {
                "code": "IEC 60364",
                "edition": "PROJECT_CONTROLLED",
            }
        ],
        "calculated_by": "Chander Kamra",
        "notes": "KESE-S2-M3 integration test.",
    }


@pytest.mark.api
async def test_create_and_get_calculation_run(
    client: AsyncClient,
) -> None:
    """A calculation run should persist and remain retrievable."""

    create_response = await client.post(
        f"{BASE_URL}/",
        json=calculation_payload(),
    )

    assert create_response.status_code == 201

    created = create_response.json()

    assert created["calculation_key"] == "MAIN-LV-DEMAND"
    assert created["revision_number"] == 1
    assert created["calculation_type"] == "LOAD_GROUP"
    assert created["scenario"] == "NORMAL"
    assert created["run_status"] == "COMPLETED"
    assert created["approval_status"] == "NOT_SUBMITTED"
    assert created["is_immutable"] is False
    assert created["supersedes_run_id"] is None
    assert len(created["content_hash"]) == 64

    get_response = await client.get(
        f"{BASE_URL}/{created['id']}"
    )

    assert get_response.status_code == 200
    assert get_response.json()["id"] == created["id"]
    assert (
        get_response.json()["content_hash"]
        == created["content_hash"]
    )


@pytest.mark.api
async def test_revision_history_and_comparison(
    client: AsyncClient,
) -> None:
    """New calculations should create linked revisions."""

    first_response = await client.post(
        f"{BASE_URL}/",
        json=calculation_payload(),
    )

    assert first_response.status_code == 201

    first_run = first_response.json()

    second_response = await client.post(
        f"{BASE_URL}/",
        json=calculation_payload(
            connected_power_kw="260.000",
            demand_power_kw="208.000",
        ),
    )

    assert second_response.status_code == 201

    second_run = second_response.json()

    assert second_run["revision_number"] == 2
    assert (
        second_run["supersedes_run_id"]
        == first_run["id"]
    )

    history_response = await client.get(
        f"{BASE_URL}/history/MAIN-LV-DEMAND"
    )

    assert history_response.status_code == 200

    history = history_response.json()

    assert len(history) == 2
    assert history[0]["revision_number"] == 2
    assert history[1]["revision_number"] == 1

    comparison_response = await client.get(
        f"{BASE_URL}/compare",
        params={
            "base_run_id": first_run["id"],
            "target_run_id": second_run["id"],
        },
    )

    assert comparison_response.status_code == 200

    comparison = comparison_response.json()

    assert comparison["base_revision_number"] == 1
    assert comparison["target_revision_number"] == 2
    assert (
        "connected_power_kw"
        in comparison["input_differences"]
    )
    assert (
        "demand_power_kw"
        in comparison["result_differences"]
    )


@pytest.mark.api
async def test_submit_approve_and_immutability(
    client: AsyncClient,
) -> None:
    """Approved calculation runs should become immutable."""

    create_response = await client.post(
        f"{BASE_URL}/",
        json=calculation_payload(),
    )

    run_id = create_response.json()["id"]

    submit_response = await client.post(
        f"{BASE_URL}/{run_id}/submit",
        json={
            "submitted_by": "Electrical Designer",
        },
    )

    assert submit_response.status_code == 200

    submitted = submit_response.json()

    assert submitted["approval_status"] == "PENDING"
    assert submitted["submitted_by"] == "Electrical Designer"
    assert submitted["submitted_at"] is not None

    pending_response = await client.get(
        f"{BASE_URL}/pending-review"
    )

    assert pending_response.status_code == 200
    assert len(pending_response.json()) == 1
    assert pending_response.json()[0]["id"] == run_id

    approve_response = await client.post(
        f"{BASE_URL}/{run_id}/approve",
        json={
            "approved_by": "Engineering Checker",
            "approval_notes": "Calculation reviewed.",
        },
    )

    assert approve_response.status_code == 200

    approved = approve_response.json()

    assert approved["approval_status"] == "APPROVED"
    assert approved["approved_by"] == "Engineering Checker"
    assert approved["approved_at"] is not None
    assert approved["is_immutable"] is True

    second_submit_response = await client.post(
        f"{BASE_URL}/{run_id}/submit",
        json={
            "submitted_by": "Another Designer",
        },
    )

    assert second_submit_response.status_code == 409
    assert "immutable" in second_submit_response.json()["detail"]

    pending_after_approval = await client.get(
        f"{BASE_URL}/pending-review"
    )

    assert pending_after_approval.status_code == 200
    assert pending_after_approval.json() == []


@pytest.mark.api
async def test_reject_pending_calculation_run(
    client: AsyncClient,
) -> None:
    """A pending calculation should support controlled rejection."""

    create_response = await client.post(
        f"{BASE_URL}/",
        json=calculation_payload(
            calculation_key="EMERGENCY-DEMAND",
        ),
    )

    run_id = create_response.json()["id"]

    submit_response = await client.post(
        f"{BASE_URL}/{run_id}/submit",
        json={
            "submitted_by": "Electrical Designer",
        },
    )

    assert submit_response.status_code == 200

    reject_response = await client.post(
        f"{BASE_URL}/{run_id}/reject",
        json={
            "rejected_by": "Engineering Checker",
            "rejection_reason": (
                "Demand-factor evidence is required."
            ),
        },
    )

    assert reject_response.status_code == 200

    rejected = reject_response.json()

    assert rejected["approval_status"] == "REJECTED"
    assert rejected["rejected_by"] == "Engineering Checker"
    assert rejected["rejected_at"] is not None
    assert rejected["rejection_reason"] == (
        "Demand-factor evidence is required."
    )
    assert rejected["is_immutable"] is False


@pytest.mark.api
async def test_duplicate_calculation_run_is_rejected(
    client: AsyncClient,
) -> None:
    """An identical calculation revision should not be duplicated."""

    payload = calculation_payload()

    first_response = await client.post(
        f"{BASE_URL}/",
        json=payload,
    )

    assert first_response.status_code == 201

    duplicate_response = await client.post(
        f"{BASE_URL}/",
        json=payload,
    )

    assert duplicate_response.status_code == 409
    assert "identical calculation run" in (
        duplicate_response.json()["detail"]
    )


@pytest.mark.api
async def test_float_snapshot_value_is_rejected(
    client: AsyncClient,
) -> None:
    """Binary floating-point snapshot values should fail validation."""

    payload = calculation_payload()

    payload["input_snapshot"] = {
        "connected_power_kw": 250.5,
    }

    response = await client.post(
        f"{BASE_URL}/",
        json=payload,
    )

    assert response.status_code == 422

    errors = response.json()["detail"]

    assert any(
        "must not contain floating-point values"
        in error["msg"]
        for error in errors
    )


@pytest.mark.api
async def test_unknown_calculation_run_returns_not_found(
    client: AsyncClient,
) -> None:
    """An unknown calculation-run UUID should return HTTP 404."""

    response = await client.get(
        f"{BASE_URL}/{uuid4()}"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "calculation run not found"
    )