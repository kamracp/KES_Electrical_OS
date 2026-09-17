"""API tests for persisted cable sizing runs (KEOS-15)."""

import pytest
from httpx import AsyncClient

CABLE_RUNS_URL = "/api/v1/electrical/cable/runs"


def cable_study(code: str = "CBL-RUN-01") -> dict[str, object]:
    return {
        "code": code,
        "name": "Feeder to MCC-1",
        "jurisdiction_profile": "IN",
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


@pytest.mark.api
async def test_create_run_persists_frozen_evidence(client: AsyncClient) -> None:
    response = await client.post(
        CABLE_RUNS_URL,
        json={"study": cable_study(), "calculated_by": "C. Kamra", "notes": "smoke"},
    )

    assert response.status_code == 201, response.text
    body = response.json()
    run = body["run"]
    assert run["module_code"] == "EOS-06"
    assert run["calculation_type"] == "CABLE_SIZING"
    assert run["calculation_key"] == "CBL-RUN-01"
    assert run["revision_number"] == 1
    assert run["approval_status"] == "NOT_SUBMITTED"
    assert run["is_immutable"] is False
    assert run["engine_version"]
    assert len(run["content_hash"]) == 64
    assert run["design_check_status"] == body["result"]["status"]
    assert run["jurisdiction_profile"] == "IN"

    detail = await client.get(f"{CABLE_RUNS_URL}/{run['id']}")
    assert detail.status_code == 200
    stored = detail.json()
    assert stored["input_snapshot"]["code"] == "CBL-RUN-01"
    assert stored["result_snapshot"] == body["result"]
    assert stored["references_snapshot"]["jurisdiction_profile"] == "IN"
    assert stored["warnings_snapshot"] == body["result"]["warnings"]


@pytest.mark.api
async def test_revisions_increment_and_list_by_key(client: AsyncClient) -> None:
    first = await client.post(CABLE_RUNS_URL, json={"study": cable_study("CBL-RUN-02")})
    second = await client.post(CABLE_RUNS_URL, json={"study": cable_study("CBL-RUN-02")})
    assert first.status_code == 201 and second.status_code == 201
    assert first.json()["run"]["revision_number"] == 1
    assert second.json()["run"]["revision_number"] == 2
    # Identical inputs and engine give an identical evidence hash.
    assert first.json()["run"]["content_hash"] == second.json()["run"]["content_hash"]

    listed = await client.get(CABLE_RUNS_URL, params={"calculation_key": "CBL-RUN-02"})
    assert listed.status_code == 200
    items = listed.json()["items"]
    assert [item["revision_number"] for item in items] == [2, 1]


@pytest.mark.api
async def test_missing_run_returns_404_and_invalid_study_422(client: AsyncClient) -> None:
    missing = await client.get(f"{CABLE_RUNS_URL}/00000000-0000-0000-0000-000000000000")
    assert missing.status_code == 404

    study = cable_study("CBL-RUN-03")
    study["circuit"]["design_current_a"] = "-1"
    invalid = await client.post(CABLE_RUNS_URL, json={"study": study})
    assert invalid.status_code == 422
