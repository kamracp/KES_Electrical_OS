"""
API tests for electrical cable sizing and ampacity calculations.
KESE-S2-M13
"""

import pytest
from httpx import AsyncClient

CABLE_SIZING_URL = "/api/v1/electrical/cable/calculate"


def cable_payload() -> dict[str, object]:
    """Return a valid cable sizing request payload."""

    return {
        "code": "CBL-FDR-01",
        "name": "Main LT Feeder Cable",
        "circuit": {
            "design_current_a": "400",
            "nominal_voltage_v": "415",
            "route_length_m": "120",
            "system": "THREE_PHASE_FOUR_WIRE",
            "power_factor": "0.90",
            "allowable_voltage_drop_percent": "3",
            "fault_current_ka": "25",
            "fault_duration_s": "1",
            "harmonic_neutral_factor": "1",
        },
        "cable": {
            "conductor_material": "COPPER",
            "insulation_material": "XLPE",
            "construction": "MULTICORE",
            "arrangement": "MULTICORE",
            "number_of_loaded_conductors": 3,
            "parallel_runs": 2,
            "neutral_required": True,
            "reduced_neutral_permitted": False,
            "protective_conductor_type": "INTEGRAL_CORE",
            "armoured": False,
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
            "phase_sizes_mm2": ["35", "50", "70", "95", "120", "150", "185", "240", "300"],
            "neutral_sizes_mm2": ["35", "50", "70", "95", "120", "150", "185", "240", "300"],
            "protective_sizes_mm2": ["16", "25", "35", "50", "70", "95", "120", "150"],
        },
        "standard_reference": "IEC 60364-5-52",
        "ampacity_reference": "IEC 60287",
        "notes": "Main LT Feeder Cable sizing study.",
    }


@pytest.mark.api
async def test_calculate_cable_sizing_success(
    client: AsyncClient,
) -> None:
    payload = cable_payload()

    response = await client.post(
        CABLE_SIZING_URL,
        json=payload,
    )

    assert response.status_code == 200
    data = response.json()

    assert data["study_code"] == "CBL-FDR-01"
    assert data["status"] == "DESIGN_CHECK_PASSED"
    assert data["standard_reference"] == "IEC 60364-5-52"
    assert data["ampacity_reference"] == "IEC 60287"
    assert data["notes"] == "Main LT Feeder Cable sizing study."

    conductor = data["conductor"]
    assert conductor is not None
    assert conductor["phase_area_mm2"] == "150"
    assert conductor["neutral_area_mm2"] == "150"
    assert conductor["protective_area_mm2"] == "95"
    assert conductor["parallel_runs"] == 2
    assert conductor["neutral_status"] == "PASS"
    assert conductor["protective_status"] == "PASS"

    ampacity = data["ampacity"]
    assert ampacity is not None
    assert ampacity["parallel_runs"] == 2
    assert ampacity["status"] == "PASS"
    assert ampacity["design_current_a"] == "400"

    voltage_drop = data["voltage_drop"]
    assert voltage_drop is not None
    assert voltage_drop["status"] == "PASS"
    assert voltage_drop["allowable_voltage_drop_percent"] == "3"

    short_circuit = data["short_circuit"]
    assert short_circuit is not None
    assert short_circuit["status"] == "PASS"


@pytest.mark.api
async def test_cable_float_input_is_rejected(
    client: AsyncClient,
) -> None:
    payload = cable_payload()
    payload["circuit"]["design_current_a"] = 400.5

    response = await client.post(
        CABLE_SIZING_URL,
        json=payload,
    )

    assert response.status_code == 422
    errors = response.json()["detail"]
    assert isinstance(errors, list)
    assert any("engineering decimal values must be provided" in error["msg"] for error in errors)


@pytest.mark.api
async def test_three_phase_three_wire_with_neutral_is_rejected(
    client: AsyncClient,
) -> None:
    payload = cable_payload()
    payload["circuit"]["system"] = "THREE_PHASE_THREE_WIRE"
    payload["cable"]["neutral_required"] = True

    response = await client.post(
        CABLE_SIZING_URL,
        json=payload,
    )

    assert response.status_code == 422
    errors = response.json()["detail"]
    assert any(
        "THREE_PHASE_THREE_WIRE circuit cannot require a neutral" in str(error) for error in errors
    )


@pytest.mark.api
async def test_three_phase_four_wire_without_neutral_is_rejected(
    client: AsyncClient,
) -> None:
    payload = cable_payload()
    payload["circuit"]["system"] = "THREE_PHASE_FOUR_WIRE"
    payload["cable"]["neutral_required"] = False

    response = await client.post(
        CABLE_SIZING_URL,
        json=payload,
    )

    assert response.status_code == 422
    errors = response.json()["detail"]
    assert any("THREE_PHASE_FOUR_WIRE circuit requires a neutral" in str(error) for error in errors)


@pytest.mark.api
async def test_reduced_neutral_with_harmonics_is_rejected(
    client: AsyncClient,
) -> None:
    payload = cable_payload()
    payload["cable"]["reduced_neutral_permitted"] = True
    payload["circuit"]["harmonic_neutral_factor"] = "1.5"

    response = await client.post(
        CABLE_SIZING_URL,
        json=payload,
    )

    assert response.status_code == 422
    errors = response.json()["detail"]
    assert any(
        "reduced neutral is not permitted when harmonic neutral factor exceeds 1" in str(error)
        for error in errors
    )


@pytest.mark.api
async def test_cable_extra_field_is_rejected(
    client: AsyncClient,
) -> None:
    payload = cable_payload()
    payload["unexpected_field"] = "disallowed"

    response = await client.post(
        CABLE_SIZING_URL,
        json=payload,
    )

    assert response.status_code == 422


@pytest.mark.api
async def test_cable_no_standard_size_returns_explicit_status(
    client: AsyncClient,
) -> None:
    payload = cable_payload()
    payload["circuit"]["design_current_a"] = "2000"
    payload["cable"]["parallel_runs"] = 1

    response = await client.post(
        CABLE_SIZING_URL,
        json=payload,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "NO_STANDARD_SIZE_AVAILABLE"
    assert data["notes"] == "Main LT Feeder Cable sizing study."
    assert len(data["warnings"]) > 0
