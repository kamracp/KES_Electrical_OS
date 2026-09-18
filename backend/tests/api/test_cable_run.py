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
async def test_identical_study_reuses_the_latest_revision(client: AsyncClient) -> None:
    first = await client.post(CABLE_RUNS_URL, json={"study": cable_study("CBL-RUN-02")})
    second = await client.post(CABLE_RUNS_URL, json={"study": cable_study("CBL-RUN-02")})
    # A11: unchanged evidence and engine version create no new revision.
    assert first.status_code == 201, first.text
    assert second.status_code == 200, second.text
    assert second.json()["run"]["id"] == first.json()["run"]["id"]
    assert second.json()["run"]["revision_number"] == 1
    assert second.json()["result"] == first.json()["result"]

    listed = await client.get(CABLE_RUNS_URL, params={"calculation_key": "CBL-RUN-02"})
    assert listed.status_code == 200
    assert [item["revision_number"] for item in listed.json()["items"]] == [1]


@pytest.mark.api
async def test_changed_study_creates_a_new_revision_and_lists_by_key(client: AsyncClient) -> None:
    original = cable_study("CBL-RUN-04")
    changed = cable_study("CBL-RUN-04")
    changed["circuit"]["design_current_a"] = "260"

    first = await client.post(CABLE_RUNS_URL, json={"study": original})
    second = await client.post(CABLE_RUNS_URL, json={"study": changed})
    # Returning to the first inputs differs from the latest revision, so it is a new one.
    third = await client.post(CABLE_RUNS_URL, json={"study": original})
    assert [r.status_code for r in (first, second, third)] == [201, 201, 201]
    assert [r.json()["run"]["revision_number"] for r in (first, second, third)] == [1, 2, 3]
    assert second.json()["run"]["content_hash"] != first.json()["run"]["content_hash"]
    # Identical inputs and engine give an identical evidence hash.
    assert third.json()["run"]["content_hash"] == first.json()["run"]["content_hash"]

    listed = await client.get(CABLE_RUNS_URL, params={"calculation_key": "CBL-RUN-04"})
    assert listed.status_code == 200
    assert [item["revision_number"] for item in listed.json()["items"]] == [3, 2, 1]


@pytest.mark.api
async def test_missing_run_returns_404_and_invalid_study_422(client: AsyncClient) -> None:
    missing = await client.get(f"{CABLE_RUNS_URL}/00000000-0000-0000-0000-000000000000")
    assert missing.status_code == 404

    study = cable_study("CBL-RUN-03")
    study["circuit"]["design_current_a"] = "-1"
    invalid = await client.post(CABLE_RUNS_URL, json={"study": study})
    assert invalid.status_code == 422
