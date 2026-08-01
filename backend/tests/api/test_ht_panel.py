

"""
API tests for HT panel engineering.
KESE-S2-M9
"""

import pytest
from httpx import AsyncClient


HT_PANEL_URL = "/api/v1/electrical/ht-panel/calculate"


def ht_panel_payload() -> dict[str, object]:
    """Return a valid HT panel request payload."""

    return {
        "code": "HTP-001",
        "name": "11 kV Main HT Panel",
        "system_voltage": "11_KV",
        "highest_system_voltage_kv": "12",
        "frequency_hz": "50",
        "installation": "INDOOR",
        "construction": "METAL_CLAD",
        "busbar_rated_current_a": "1250",
        "busbar_short_time_withstand_current_ka": "25",
        "busbar_short_time_duration_s": "3",
        "busbar_peak_withstand_current_ka": "63",
        "rated_insulation_level_kv": "28",
        "lightning_impulse_withstand_voltage_kvp": "75",
        "feeders": [
            {
                "code": "HT-IN-01",
                "name": "Main HT Incomer",
                "feeder_type": "INCOMER",
                "switching_device": "VCB",
                "design_current_a": "400",
                "prospective_short_circuit_current_ka": "20",
                "rated_normal_current_a": "630",
                "rated_short_circuit_breaking_current_ka": "25",
                "rated_short_time_withstand_current_ka": "25",
                "short_time_withstand_duration_s": "3",
                "rated_peak_withstand_current_ka": "63",
                "ct_primary_current_a": "600",
                "ct_secondary_current_a": "1",
                "ct_protection_class": "5P20",
                "ct_metering_class": "0.5",
                "relay_functions": [
                    "50_51",
                    "50N_51N",
                ],
                "cable_count": 1,
                "spare_feeder": False,
            }
        ],
        "bus_sections": 1,
        "bus_couplers": 0,
        "spare_feeders": 1,
        "indoor_ip_rating": "IP4X",
        "outdoor_ip_rating": "IP54",
        "earthing_switch_required": True,
        "arc_classification_required": False,
        "remote_operation_required": False,
    }


@pytest.mark.api
async def test_calculate_ht_panel(
    client: AsyncClient,
) -> None:
    response = await client.post(
        HT_PANEL_URL,
        json=ht_panel_payload(),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["code"] == "HTP-001"
    assert data["system_voltage"] == "11_KV"
    assert data["total_feeders"] == 2
    assert data["active_feeders"] == 1
    assert data["spare_feeders"] == 1
    assert data["aggregate_design_current_a"] == "400.0000"
    assert data["busbar_loading_percent"] == "32.0000"
    assert data["maximum_fault_current_ka"] == "20.0000"
    assert len(data["feeder_results"]) == 2


@pytest.mark.api
async def test_low_margin_warning_response(
    client: AsyncClient,
) -> None:
    payload = ht_panel_payload()

    feeders = payload["feeders"]
    assert isinstance(feeders, list)

    feeder = feeders[0]
    assert isinstance(feeder, dict)

    feeder["rated_short_circuit_breaking_current_ka"] = "24"

    response = await client.post(
        HT_PANEL_URL,
        json=payload,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "WARNING"

    assert any(
        warning["code"] == "BREAKING_CAPACITY_MARGIN_LOW"
        for warning in data["feeder_results"][0]["warnings"]
    )


@pytest.mark.api
async def test_float_engineering_input_is_rejected(
    client: AsyncClient,
) -> None:
    payload = ht_panel_payload()
    payload["busbar_rated_current_a"] = 1250.5

    response = await client.post(
        HT_PANEL_URL,
        json=payload,
    )

    assert response.status_code == 422

    errors = response.json()["detail"]

    assert isinstance(errors, list)

    assert any(
        "engineering decimal values must be provided"
        in error["msg"]
        for error in errors
    )


@pytest.mark.api
async def test_invalid_bus_section_arrangement_is_rejected(
    client: AsyncClient,
) -> None:
    payload = ht_panel_payload()
    payload["bus_sections"] = 2
    payload["bus_couplers"] = 0

    response = await client.post(
        HT_PANEL_URL,
        json=payload,
    )

    assert response.status_code == 422

    detail = response.json()["detail"]

    assert isinstance(detail, str)
    assert "multiple bus sections require" in detail


@pytest.mark.api
async def test_extra_field_is_rejected(
    client: AsyncClient,
) -> None:
    payload = ht_panel_payload()
    payload["unexpected_field"] = "not permitted"

    response = await client.post(
        HT_PANEL_URL,
        json=payload,
    )

    assert response.status_code == 422
