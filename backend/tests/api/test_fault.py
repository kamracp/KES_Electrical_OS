"""
API tests for short-circuit and earth-fault calculations.
KESE-S2-M15
"""

import pytest
from httpx import AsyncClient

FAULT_URL = "/api/v1/electrical/fault/calculate"


def fault_payload() -> dict[str, object]:
    """Return a valid short-circuit study request payload."""

    return {
        "code": "FAULT-001",
        "name": "Main 11 kV Bus Short Circuit Study",
        "calculation_case": "MAXIMUM",
        "fault": {
            "bus_code": "BUS-01",
            "fault_type": "THREE_PHASE",
            "clearing_time_s": "0.20",
        },
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
                "positive_sequence_impedance": {
                    "resistance_ohm": "0.10",
                    "reactance_ohm": "0.20",
                },
                "negative_sequence_impedance": {
                    "resistance_ohm": "0.10",
                    "reactance_ohm": "0.20",
                },
                "zero_sequence_impedance": {
                    "resistance_ohm": "0.20",
                    "reactance_ohm": "0.40",
                },
                "in_service": True,
            }
        ],
        "branches": [],
        "frequency_hz": "50",
        "standard_reference": "IEC 60909-0:2026",
        "notes": "Main 11 kV fault study.",
    }


@pytest.mark.api
async def test_calculate_short_circuit_success(
    client: AsyncClient,
) -> None:
    payload = fault_payload()

    response = await client.post(
        FAULT_URL,
        json=payload,
    )

    assert response.status_code == 200
    data = response.json()

    assert data["study_code"] == "FAULT-001"
    assert data["study_name"] == "Main 11 kV Bus Short Circuit Study"
    assert data["notes"] == "Main 11 kV fault study."
    assert data["calculation_case"] == "MAXIMUM"
    assert data["fault_type"] == "THREE_PHASE"
    assert data["status"] == "WARNING"
    assert data["initial_symmetrical_short_circuit_current_ka"] is not None
    assert len(data["sequence_results"]) > 0
    assert len(data["source_contributions"]) == 1
    assert data["source_contributions"][0]["source_code"] == "GRID-01"


@pytest.mark.api
async def test_calculate_current_injection_source(
    client: AsyncClient,
) -> None:
    payload = fault_payload()
    payload["sources"] = [
        {
            "code": "IBR-01",
            "name": "Solar Inverter Plant",
            "bus_code": "BUS-01",
            "source_type": "INVERTER_BASED_RESOURCE",
            "representation": "CURRENT_INJECTION",
            "current_contribution_ka": "1.50",
            "in_service": True,
        }
    ]

    response = await client.post(
        FAULT_URL,
        json=payload,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "WARNING"
    assert data["source_contributions"][0]["source_code"] == "IBR-01"
    assert data["source_contributions"][0]["initial_symmetrical_current_ka"] == "1.500000000"


@pytest.mark.api
async def test_calculate_earth_fault_success(
    client: AsyncClient,
) -> None:
    payload = fault_payload()
    payload["fault"]["fault_type"] = "SINGLE_PHASE_TO_EARTH"

    response = await client.post(
        FAULT_URL,
        json=payload,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "WARNING"
    assert data["earth_fault_current_ka"] is not None


@pytest.mark.api
async def test_fault_float_input_is_rejected(
    client: AsyncClient,
) -> None:
    payload = fault_payload()
    payload["frequency_hz"] = 50.0

    response = await client.post(
        FAULT_URL,
        json=payload,
    )

    assert response.status_code == 422
    errors = response.json()["detail"]
    assert isinstance(errors, list)
    assert any("engineering decimal values must be provided" in error["msg"] for error in errors)


@pytest.mark.api
async def test_fault_extra_field_is_rejected(
    client: AsyncClient,
) -> None:
    payload = fault_payload()
    payload["unexpected_field"] = "not_allowed"

    response = await client.post(
        FAULT_URL,
        json=payload,
    )

    assert response.status_code == 422


@pytest.mark.api
async def test_fault_unknown_bus_reference_is_rejected(
    client: AsyncClient,
) -> None:
    payload = fault_payload()
    payload["fault"]["bus_code"] = "BUS-NONEXISTENT"

    response = await client.post(
        FAULT_URL,
        json=payload,
    )

    assert response.status_code == 422
