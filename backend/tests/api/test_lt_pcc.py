"""
API tests for LT PCC / Main Panel engineering.
KESE-S2-M10
"""

import pytest
from httpx import AsyncClient


LT_PCC_URL = "/api/v1/electrical/lt-pcc/calculate"


def lt_pcc_payload() -> dict[str, object]:
    return {
        "code": "PCC-001",
        "name": "Main LT PCC",
        "system_voltage": "415_V",
        "frequency_hz": "50",
        "installation": "INDOOR",
        "form_of_separation": "FORM_4B",
        "busbar_rated_current_a": "2500",
        "busbar_short_time_withstand_current_ka": "65",
        "busbar_peak_withstand_current_ka": "143",
        "neutral_bus_rating_percent": "100",
        "earth_bus_rating_percent": "50",
        "feeders": [
            {
                "code": "TR-IN-01",
                "name": "Transformer Incomer",
                "feeder_type": "TRANSFORMER_INCOMER",
                "switching_device": "ACB",
                "trip_unit_type": "ELECTRONIC_LSIG",
                "design_current_a": "1400",
                "rated_current_a": "1600",
                "prospective_short_circuit_current_ka": "50",
                "rated_ultimate_breaking_capacity_ka": "65",
                "rated_service_breaking_capacity_ka": "65",
                "rated_short_time_withstand_current_ka": "65",
                "number_of_poles": 4,
                "cable_count": 4,
                "spare_feeder": False,
            }
        ],
        "bus_sections": 1,
        "bus_couplers": 0,
        "spare_feeders": 1,
        "ip_rating": "IP42",
        "apfc_required": False,
        "metering_required": True,
        "remote_operation_required": False,
    }


@pytest.mark.api
async def test_calculate_lt_pcc(
    client: AsyncClient,
) -> None:
    response = await client.post(
        LT_PCC_URL,
        json=lt_pcc_payload(),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["code"] == "PCC-001"
    assert data["system_voltage"] == "415_V"
    assert data["total_feeders"] == 2
    assert data["active_feeders"] == 1
    assert data["spare_feeders"] == 1
    assert data["aggregate_design_current_a"] == "1400.0000"
    assert data["busbar_loading_percent"] == "56.0000"
    assert data["maximum_fault_current_ka"] == "50.0000"


@pytest.mark.api
async def test_lt_pcc_warning_response(
    client: AsyncClient,
) -> None:
    payload = lt_pcc_payload()
    feeders = payload["feeders"]
    assert isinstance(feeders, list)

    feeder = feeders[0]
    assert isinstance(feeder, dict)

    feeder["rated_ultimate_breaking_capacity_ka"] = "60"
    feeder["rated_service_breaking_capacity_ka"] = "60"

    response = await client.post(
        LT_PCC_URL,
        json=payload,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "WARNING"

    assert any(
        warning["code"] == "ICU_MARGIN_LOW"
        for warning in data["feeder_results"][0]["warnings"]
    )


@pytest.mark.api
async def test_float_input_is_rejected(
    client: AsyncClient,
) -> None:
    payload = lt_pcc_payload()
    payload["busbar_rated_current_a"] = 2500.5

    response = await client.post(
        LT_PCC_URL,
        json=payload,
    )

    assert response.status_code == 422


@pytest.mark.api
async def test_invalid_bus_section_arrangement_is_rejected(
    client: AsyncClient,
) -> None:
    payload = lt_pcc_payload()
    payload["bus_sections"] = 2
    payload["bus_couplers"] = 0

    response = await client.post(
        LT_PCC_URL,
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
    payload = lt_pcc_payload()
    payload["unexpected_field"] = "not permitted"

    response = await client.post(
        LT_PCC_URL,
        json=payload,
    )

    assert response.status_code == 422
