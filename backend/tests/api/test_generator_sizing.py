"""
API tests for generator source-sizing calculations.
KESE-S2-M7
"""

import pytest
from httpx import AsyncClient


GENERATOR_SIZING_URL = (
    "/api/v1/electrical/generator-sizing/calculate"
)


def generator_payload() -> dict[str, object]:
    """Return a valid generator-sizing request payload."""

    return {
        "code": "DG-001",
        "name": "Emergency Generator",
        "steady_state_demand_kw": "800",
        "steady_state_power_factor": "0.80",
        "transient_step_load_kva": "0",
        "transient_allowance_factor": "1",
        "future_growth_factor": "1",
        "design_margin_factor": "1.10",
        "ambient_derating_factor": "1",
        "altitude_derating_factor": "1",
        "available_unit_ratings_kva": [
            "1000",
            "1250",
            "1600",
        ],
        "duty_units": 1,
        "standby_units": 0,
        "duty_class": "STANDBY",
        "redundancy_mode": "NONE",
        "scenario": "EMERGENCY",
        "notes": "Emergency electrical source.",
    }


@pytest.mark.api
async def test_calculate_generator_sizing(
    client: AsyncClient,
) -> None:
    """API should select the smallest adequate generator rating."""

    response = await client.post(
        GENERATOR_SIZING_URL,
        json=generator_payload(),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["code"] == "DG-001"
    assert data["name"] == "Emergency Generator"
    assert data["scenario"] == "EMERGENCY"
    assert data["duty_class"] == "STANDBY"
    assert data["redundancy_mode"] == "NONE"

    assert data["steady_state_demand_kva"] == "1000.0000"
    assert data["steady_state_required_kva"] == "1100.0000"
    assert data["transient_required_kva"] == "1000.0000"
    assert data["governing_required_kva"] == "1100.0000"

    assert data["required_unit_rating_kva"] == "1100.0000"
    assert data["selected_unit_rating_kva"] == "1250"

    assert (
        data["installed_nameplate_capacity_kva"]
        == "1250.0000"
    )
    assert data["derated_duty_capacity_kva"] == "1250.0000"
    assert data["spare_derated_capacity_kva"] == "150.0000"
    assert data["steady_state_loading_percent"] == "88.0000"

    assert data["status"] == "VALID"
    assert data["warnings"] == []


@pytest.mark.api
async def test_transient_and_derating_warning_response(
    client: AsyncClient,
) -> None:
    """Transient load and derating should return warnings."""

    payload = generator_payload()
    payload.update(
        {
            "transient_step_load_kva": "350",
            "transient_allowance_factor": "1.10",
            "future_growth_factor": "1.10",
            "ambient_derating_factor": "0.95",
            "altitude_derating_factor": "0.98",
            "available_unit_ratings_kva": [
                "1250",
                "1600",
                "2000",
            ],
        }
    )

    response = await client.post(
        GENERATOR_SIZING_URL,
        json=payload,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["future_steady_state_kva"] == "1100.0000"
    assert data["steady_state_required_kva"] == "1210.0000"
    assert data["transient_additional_kva"] == "385.0000"
    assert data["transient_required_kva"] == "1485.0000"
    assert data["governing_required_kva"] == "1485.0000"

    assert data["combined_derating_factor"] == "0.9310"
    assert (
        data["required_nameplate_capacity_kva"]
        == "1595.0591"
    )
    assert data["selected_unit_rating_kva"] == "1600"
    assert data["derated_duty_capacity_kva"] == "1489.6000"
    assert data["spare_derated_capacity_kva"] == "4.6000"

    assert data["status"] == "WARNING"

    warning_codes = {
        warning["code"]
        for warning in data["warnings"]
    }

    assert warning_codes == {
        "DERATING_APPLIED",
        "TRANSIENT_REQUIREMENT_GOVERNS",
    }


@pytest.mark.api
async def test_no_generator_rating_available(
    client: AsyncClient,
) -> None:
    """Inadequate generator rating schedule returns no solution."""

    payload = generator_payload()
    payload["steady_state_demand_kw"] = "3000"

    response = await client.post(
        GENERATOR_SIZING_URL,
        json=payload,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "NO_SOLUTION"
    assert data["selected_unit_rating_kva"] is None
    assert data["installed_nameplate_capacity_kva"] is None
    assert data["derated_duty_capacity_kva"] is None
    assert data["spare_derated_capacity_kva"] is None
    assert data["steady_state_loading_percent"] is None

    assert any(
        warning["code"]
        == "NO_STANDARD_RATING_AVAILABLE"
        for warning in data["warnings"]
    )


@pytest.mark.api
async def test_generator_n_plus_one_arrangement(
    client: AsyncClient,
) -> None:
    """N+1 should include one standby generator."""

    payload = generator_payload()
    payload.update(
        {
            "steady_state_demand_kw": "1600",
            "design_margin_factor": "1",
            "available_unit_ratings_kva": [
                "1000",
                "1250",
            ],
            "duty_units": 2,
            "standby_units": 1,
            "redundancy_mode": "N_PLUS_1",
        }
    )

    response = await client.post(
        GENERATOR_SIZING_URL,
        json=payload,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["selected_unit_rating_kva"] == "1000"
    assert data["duty_units"] == 2
    assert data["standby_units"] == 1
    assert data["total_units"] == 3

    assert (
        data["installed_nameplate_capacity_kva"]
        == "3000.0000"
    )
    assert data["derated_duty_capacity_kva"] == "2000.0000"


@pytest.mark.api
async def test_generator_float_input_is_rejected(
    client: AsyncClient,
) -> None:
    """JSON floating-point engineering values should fail."""

    payload = generator_payload()
    payload["steady_state_demand_kw"] = 800.5

    response = await client.post(
        GENERATOR_SIZING_URL,
        json=payload,
    )

    assert response.status_code == 422

    errors = response.json()["detail"]

    assert any(
        "engineering decimal values must be provided"
        in error["msg"]
        for error in errors
    )


@pytest.mark.api
async def test_unsorted_generator_ratings_are_rejected(
    client: AsyncClient,
) -> None:
    """Generator ratings must follow ascending order."""

    payload = generator_payload()
    payload["available_unit_ratings_kva"] = [
        "1250",
        "1000",
        "1600",
    ]

    response = await client.post(
        GENERATOR_SIZING_URL,
        json=payload,
    )

    assert response.status_code == 422

    errors = response.json()["detail"]

    assert any(
        "must be in ascending order" in error["msg"]
        for error in errors
    )
