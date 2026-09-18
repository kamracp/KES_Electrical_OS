"""API tests for persisted short-circuit study runs (KEOS-16b, EOS-04)."""

import pytest
from httpx import AsyncClient

FAULT_RUNS_URL = "/api/v1/electrical/fault/runs"
CABLE_RUNS_URL = "/api/v1/electrical/cable/runs"

REFERENCE_FIELDS = {
    "standard_reference",
    "earth_current_reference",
    "reference_source",
    "jurisdiction_profile",
    "reference_verification_status",
}


def fault_study(code: str = "FLT-RUN-01") -> dict[str, object]:
    return {
        "code": code,
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
        "notes": "Main 11 kV fault study.",
    }


def cable_study(code: str) -> dict[str, object]:
    """A valid cable study, used only to create a run of another module."""

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
async def test_create_fault_run_persists_frozen_evidence(client: AsyncClient) -> None:
    response = await client.post(
        FAULT_RUNS_URL,
        json={"study": fault_study(), "calculated_by": "C. Kamra", "notes": "smoke"},
    )

    assert response.status_code == 201, response.text
    body = response.json()
    run = body["run"]
    result = body["result"]
    assert run["module_code"] == "EOS-04"
    assert run["calculation_type"] == "SHORT_CIRCUIT"
    assert run["calculation_key"] == "FLT-RUN-01"
    assert run["revision_number"] == 1
    assert run["run_status"] == "COMPLETED"
    assert run["approval_status"] == "NOT_SUBMITTED"
    assert run["is_immutable"] is False
    assert run["engine_version"] == "fault-engine 0.1.0"
    assert len(run["content_hash"]) == 64
    assert run["calculated_by"] == "C. Kamra"
    assert run["notes"] == "smoke"
    # Stored values come from the JSON-mode result, never from str(enum).
    assert run["design_check_status"] == result["status"]
    assert run["jurisdiction_profile"] == result["jurisdiction_profile"] == "IN"
    assert run["reference_verification_status"] == result["reference_verification_status"]
    assert result["study_code"] == "FLT-RUN-01"
    assert result["initial_symmetrical_short_circuit_current_ka"] is not None

    detail = await client.get(f"{FAULT_RUNS_URL}/{run['id']}")
    assert detail.status_code == 200
    stored = detail.json()
    assert stored["input_snapshot"]["code"] == "FLT-RUN-01"
    assert stored["result_snapshot"] == result
    assert stored["warnings_snapshot"] == result["warnings"]
    assert set(stored["references_snapshot"]) == REFERENCE_FIELDS
    for name in REFERENCE_FIELDS:
        assert stored["references_snapshot"][name] == result[name]


@pytest.mark.api
async def test_identical_fault_study_reuses_the_latest_revision(client: AsyncClient) -> None:
    first = await client.post(FAULT_RUNS_URL, json={"study": fault_study("FLT-RUN-02")})
    second = await client.post(FAULT_RUNS_URL, json={"study": fault_study("FLT-RUN-02")})
    # A11: unchanged evidence and engine version create no new revision.
    assert first.status_code == 201, first.text
    assert second.status_code == 200, second.text
    assert second.json()["run"]["id"] == first.json()["run"]["id"]
    assert second.json()["run"]["revision_number"] == 1
    assert second.json()["result"] == first.json()["result"]

    listed = await client.get(FAULT_RUNS_URL, params={"calculation_key": "FLT-RUN-02"})
    assert listed.status_code == 200
    assert [item["revision_number"] for item in listed.json()["items"]] == [1]


@pytest.mark.api
async def test_changed_fault_study_creates_a_new_revision_and_lists_by_key(
    client: AsyncClient,
) -> None:
    original = fault_study("FLT-RUN-05")
    changed = fault_study("FLT-RUN-05")
    changed["sources"][0]["positive_sequence_impedance"]["reactance_ohm"] = "0.25"

    first = await client.post(FAULT_RUNS_URL, json={"study": original})
    second = await client.post(FAULT_RUNS_URL, json={"study": changed})
    # Returning to the first inputs differs from the latest revision, so it is a new one.
    third = await client.post(FAULT_RUNS_URL, json={"study": original})
    assert [r.status_code for r in (first, second, third)] == [201, 201, 201]
    assert [r.json()["run"]["revision_number"] for r in (first, second, third)] == [1, 2, 3]
    assert second.json()["run"]["content_hash"] != first.json()["run"]["content_hash"]
    # Identical inputs and engine give an identical evidence hash.
    assert third.json()["run"]["content_hash"] == first.json()["run"]["content_hash"]

    listed = await client.get(FAULT_RUNS_URL, params={"calculation_key": "FLT-RUN-05"})
    assert listed.status_code == 200
    assert [item["revision_number"] for item in listed.json()["items"]] == [3, 2, 1]


@pytest.mark.api
async def test_missing_fault_run_returns_404_and_invalid_study_422(client: AsyncClient) -> None:
    missing = await client.get(f"{FAULT_RUNS_URL}/00000000-0000-0000-0000-000000000000")
    assert missing.status_code == 404

    study = fault_study("FLT-RUN-03")
    study["buses"] = []
    invalid = await client.post(FAULT_RUNS_URL, json={"study": study})
    assert invalid.status_code == 422


@pytest.mark.api
async def test_runs_are_isolated_per_module(client: AsyncClient) -> None:
    fault = await client.post(FAULT_RUNS_URL, json={"study": fault_study("FLT-RUN-04")})
    cable = await client.post(CABLE_RUNS_URL, json={"study": cable_study("CBL-RUN-ISO")})
    assert fault.status_code == 201, fault.text
    assert cable.status_code == 201, cable.text
    fault_id = fault.json()["run"]["id"]
    cable_id = cable.json()["run"]["id"]

    # A run is only visible through its own module's endpoint.
    assert (await client.get(f"{FAULT_RUNS_URL}/{cable_id}")).status_code == 404
    assert (await client.get(f"{CABLE_RUNS_URL}/{fault_id}")).status_code == 404
    assert (await client.get(f"{FAULT_RUNS_URL}/{fault_id}")).status_code == 200

    recent = await client.get(FAULT_RUNS_URL)
    assert recent.status_code == 200
    items = recent.json()["items"]
    assert items
    assert all(item["module_code"] == "EOS-04" for item in items)
