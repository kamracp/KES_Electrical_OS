"""
API tests for transformer source-sizing calculations.
KESE-S2-M5
"""

import pytest
from httpx import AsyncClient


TRANSFORMER_SIZING_URL = (
    "/api/v1/electrical/transformer-sizing/calculate"
)


def transformer_payload() -> dict[str, object]:
    """Return a valid transformer-sizing request payload."""

    return {
        "code": "TR-001",
        "name": "Main Transformer",
        "demand_power_kw": "800",
        "demand_power_factor": "0.80",
        "available_unit_ratings_kva": [
            "1000",
            "1250",
            "1600",
        ],
        "future_growth_factor": "1",
        "design_margin_factor": "1.10",
        "ambient_derating_factor": "1",
        "altitude_derating_factor": "1",
        "harmonic_derating_factor": "1",
        "duty_units": 1,
        "standby_units": 0,
        "redundancy_mode": "NONE",
        "scenario": "NORMAL",
        "notes": "Main plant transformer.",
    }


@pytest.mark.api
async def test_calculate_transformer_sizing(
    client: AsyncClient,
) -> None:
    """The API should select the smallest adequate rating."""

    response = await client.post(
        TRANSFORMER_SIZING_URL,
        json=transformer_payload(),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["code"] == "TR-001"
    assert data["name"] == "Main Transformer"
    assert data["scenario"] == "NORMAL"
    assert data["redundancy_mode"] == "NONE"
    assert data["base_demand_kva"] == "1000.0000"
    assert data["design_required_kva"] == "1100.0000"
    assert data["required_unit_rating_kva"] == "1100.0000"
    assert data["selected_unit_rating_kva"] == "1250"
    assert data["installed_nameplate_capacity_kva"] == "1250.0000"
    assert data["derated_duty_capacity_kva"] == "1250.0000"
    assert data["spare_derated_capacity_kva"] == "150.0000"
    assert data["loading_percent"] == "88.0000"
    assert data["status"] == "VALID"
    assert data["warnings"] == []


@pytest.mark.api
async def test_derating_warning_response(
    client: AsyncClient,
) -> None:
    """Applied derating should return a controlled warning."""

    payload = transformer_payload()
    payload["future_growth_factor"] = "1.20"
    payload["ambient_derating_factor"] = "0.95"
    payload["altitude_derating_factor"] = "0.98"
    payload["harmonic_derating_factor"] = "0.90"

    response = await client.post(
        TRANSFORMER_SIZING_URL,
        json=payload,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["combined_derating_factor"] == "0.8379"
    assert data["selected_unit_rating_kva"] == "1600"
    assert data["status"] == "WARNING"

    assert any(
        warning["code"] == "DERATING_APPLIED"
        for warning in data["warnings"]
    )


@pytest.mark.api
async def test_no_standard_rating_available(
    client: AsyncClient,
) -> None:
    """An inadequate rating schedule should return no solution."""

    payload = transformer_payload()
    payload["demand_power_kw"] = "3000"

    response = await client.post(
        TRANSFORMER_SIZING_URL,
        json=payload,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "NO_SOLUTION"
    assert data["selected_unit_rating_kva"] is None
    assert data["installed_nameplate_capacity_kva"] is None
    assert data["derated_duty_capacity_kva"] is None
    assert data["spare_derated_capacity_kva"] is None
    assert data["loading_percent"] is None

    assert any(
        warning["code"]
        == "NO_STANDARD_RATING_AVAILABLE"
        for warning in data["warnings"]
    )


@pytest.mark.api
async def test_n_plus_one_arrangement(
    client: AsyncClient,
) -> None:
    """N+1 should include one standby transformer."""

    payload = transformer_payload()
    payload.update(
        {
            "demand_power_kw": "1600",
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
        TRANSFORMER_SIZING_URL,
        json=payload,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["selected_unit_rating_kva"] == "1000"
    assert data["duty_units"] == 2
    assert data["standby_units"] == 1
    assert data["total_units"] == 3
    assert data["installed_nameplate_capacity_kva"] == "3000.0000"
    assert data["derated_duty_capacity_kva"] == "2000.0000"


@pytest.mark.api
async def test_float_engineering_input_is_rejected(
    client: AsyncClient,
) -> None:
    """JSON floating-point engineering values should fail."""

    payload = transformer_payload()
    payload["demand_power_kw"] = 800.5

    response = await client.post(
        TRANSFORMER_SIZING_URL,
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
async def test_unsorted_rating_schedule_is_rejected(
    client: AsyncClient,
) -> None:
    """Transformer ratings must use controlled ascending order."""

    payload = transformer_payload()
    payload["available_unit_ratings_kva"] = [
        "1250",
        "1000",
        "1600",
    ]

    response = await client.post(
        TRANSFORMER_SIZING_URL,
        json=payload,
    )

    assert response.status_code == 422

    errors = response.json()["detail"]

    assert any(
        "must be in ascending order" in error["msg"]
        for error in errors
    )
