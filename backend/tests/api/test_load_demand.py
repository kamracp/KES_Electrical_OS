"""
API tests for electrical load and demand calculations.
KESE-S2-M2
"""

import pytest
from httpx import AsyncClient

LOAD_URL = "/api/v1/electrical/load-demand/calculate"
GROUP_URL = "/api/v1/electrical/load-demand/calculate-group"


def motor_payload() -> dict[str, object]:
    """Return the approved motor-load request payload."""

    return {
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
        "scenario": "NORMAL",
        "power_basis": "MECHANICAL_OUTPUT",
        "notes": "Normal process pump load.",
    }


@pytest.mark.api
async def test_calculate_single_load(
    client: AsyncClient,
) -> None:
    """The API should return the approved motor calculation."""

    response = await client.post(
        LOAD_URL,
        json=motor_payload(),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["load_code"] == "MTR-001"
    assert data["load_name"] == "Process Water Pump"
    assert data["scenario"] == "NORMAL"
    assert data["phase_system"] == "THREE_PHASE"
    assert data["connected_power_kw"] == "32.6087"
    assert data["utilized_power_kw"] == "26.0870"
    assert data["demand_power_kw"] == "23.4783"
    assert data["apparent_power_kva"] == "27.6215"
    assert data["reactive_power_kvar"] == "14.5505"
    assert data["design_current_a"] == "38.4272"
    assert data["status"] == "VALID"
    assert data["warnings"] == []


@pytest.mark.api
async def test_calculate_load_group(
    client: AsyncClient,
) -> None:
    """The API should calculate and aggregate a load group."""

    payload = {
        "code": "PUMP-GRP",
        "name": "Process Pump Loads",
        "loads": [
            motor_payload(),
        ],
        "coincidence_factor": "0.90",
    }

    response = await client.post(
        GROUP_URL,
        json=payload,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["group_code"] == "PUMP-GRP"
    assert data["group_name"] == "Process Pump Loads"
    assert data["coincidence_factor"] == "0.90"
    assert data["connected_power_kw"] == "32.6087"
    assert data["pre_coincidence_demand_kw"] == "23.4783"
    assert data["demand_power_kw"] == "21.1304"
    assert data["apparent_power_kva"] == "24.8593"
    assert data["reactive_power_kvar"] == "13.0955"
    assert data["status"] == "VALID"
    assert len(data["load_results"]) == 1


@pytest.mark.api
async def test_low_power_factor_warning_response(
    client: AsyncClient,
) -> None:
    """Low power factor should return a controlled warning."""

    payload = motor_payload()
    payload["power_factor"] = "0.75"

    response = await client.post(
        LOAD_URL,
        json=payload,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "WARNING"
    assert any(
        warning["code"] == "LOW_POWER_FACTOR"
        for warning in data["warnings"]
    )


@pytest.mark.api
async def test_float_engineering_input_is_rejected(
    client: AsyncClient,
) -> None:
    """JSON floating-point engineering values should fail."""

    payload = motor_payload()
    payload["rated_power_kw"] = 15.5

    response = await client.post(
        LOAD_URL,
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
async def test_invalid_dc_power_factor_is_rejected(
    client: AsyncClient,
) -> None:
    """DC loads must use unity power factor."""

    payload = {
        "code": "DC-001",
        "name": "DC Control Load",
        "quantity": 1,
        "rated_power_kw": "2.4",
        "phase_system": "DC",
        "voltage_v": "48",
        "power_factor": "0.90",
    }

    response = await client.post(
        LOAD_URL,
        json=payload,
    )

    assert response.status_code == 422

    errors = response.json()["detail"]

    assert any(
        "DC loads must use a power_factor of 1"
        in error["msg"]
        for error in errors
    )


@pytest.mark.api
async def test_extra_request_field_is_rejected(
    client: AsyncClient,
) -> None:
    """Unknown request fields should not be silently accepted."""

    payload = motor_payload()
    payload["unexpected_field"] = "not permitted"

    response = await client.post(
        LOAD_URL,
        json=payload,
    )

    assert response.status_code == 422


@pytest.mark.api
async def test_empty_load_group_is_rejected(
    client: AsyncClient,
) -> None:
    """A group request must contain at least one load."""

    payload = {
        "code": "EMPTY-GRP",
        "name": "Empty Load Group",
        "loads": [],
        "coincidence_factor": "1",
    }

    response = await client.post(
        GROUP_URL,
        json=payload,
    )

    assert response.status_code == 422