"""Unit tests for the load and demand schemas (EOS-02, Master Prompt A15)."""

from decimal import Decimal
from typing import Any
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.domain.electrical.jurisdiction.jurisdiction_models import JurisdictionProfile
from app.domain.electrical.loads.engine import calculate_load_group
from app.domain.electrical.loads.results import (
    GROUP_COINCIDENCE_ASSUMPTION,
    CalculationStatus,
    LoadWarningCode,
)
from app.schemas.calculation_run import LoadRunCreateRequest
from app.schemas.load_demand import (
    LoadCalculationRequest,
    LoadGroupCalculationRequest,
    LoadGroupCalculationResponse,
)

pytestmark = pytest.mark.unit


def motor_payload(**overrides: Any) -> dict[str, Any]:
    """Return a valid three-phase motor request payload."""

    payload: dict[str, Any] = {
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
        "power_basis": "MECHANICAL_OUTPUT",
    }
    payload.update(overrides)

    return payload


def group_payload(**overrides: Any) -> dict[str, Any]:
    """Return a valid load-group request payload."""

    payload: dict[str, Any] = {
        "code": "PUMP-GRP",
        "name": "Process Pump Loads",
        "loads": [motor_payload()],
        "coincidence_factor": "0.90",
    }
    payload.update(overrides)

    return payload


@pytest.mark.parametrize(
    "phase_system",
    [
        "SINGLE_PHASE",
        "THREE_PHASE",
    ],
)
def test_ac_load_without_power_factor_is_rejected(phase_system: str) -> None:
    """An AC load must state its power factor; 1 is never assumed (A15 (a))."""

    payload = motor_payload(phase_system=phase_system)
    del payload["power_factor"]

    with pytest.raises(ValidationError) as error:
        LoadCalculationRequest.model_validate(payload)

    assert "power_factor is required for AC loads" in str(error.value)


def test_dc_load_without_power_factor_is_accepted() -> None:
    """A DC load has no power factor, so a blank value is permitted."""

    payload = motor_payload(phase_system="DC", voltage_v="48")
    del payload["power_factor"]

    request = LoadCalculationRequest.model_validate(payload)

    assert request.power_factor is None
    assert request.to_domain().power_factor is None


def test_dc_load_with_a_non_unity_power_factor_is_rejected() -> None:
    """The existing DC rule and its message are unchanged."""

    payload = motor_payload(
        phase_system="DC",
        voltage_v="48",
        power_factor="0.9",
    )

    with pytest.raises(ValidationError) as error:
        LoadCalculationRequest.model_validate(payload)

    assert "DC loads must use a power_factor of 1" in str(error.value)


@pytest.mark.parametrize(
    "field_name",
    [
        "utilization_factor",
        "demand_factor",
        "efficiency",
    ],
)
def test_blank_load_factor_reaches_the_domain_as_none(field_name: str) -> None:
    """A blank factor is not filled in by the schema (A15 (a))."""

    payload = motor_payload()
    del payload[field_name]

    load = LoadCalculationRequest.model_validate(payload).to_domain()

    assert getattr(load, field_name) is None


def test_blank_group_coincidence_reaches_the_domain_as_none() -> None:
    """A blank coincidence factor is not filled in by the schema."""

    payload = group_payload()
    del payload["coincidence_factor"]

    group = LoadGroupCalculationRequest.model_validate(payload).to_domain()

    assert group.coincidence_factor is None


@pytest.mark.parametrize(
    ("field_name", "field_value"),
    [
        ("utilization_factor", "1.01"),
        ("demand_factor", "-0.01"),
        ("efficiency", "0"),
        ("power_factor", "0"),
    ],
)
def test_given_factors_keep_their_bounds(field_name: str, field_value: str) -> None:
    """A factor that IS given is still bound to its permitted range."""

    with pytest.raises(ValidationError):
        LoadCalculationRequest.model_validate(motor_payload(**{field_name: field_value}))


def test_float_engineering_value_is_still_rejected() -> None:
    """Binary floating-point engineering inputs stay refused."""

    with pytest.raises(ValidationError) as error:
        LoadCalculationRequest.model_validate(motor_payload(utilization_factor=0.8))

    assert "must be provided as strings" in str(error.value)


def test_group_without_a_profile_defaults_to_in() -> None:
    """The jurisdiction profile defaults to IN, as Cable and Fault do."""

    request = LoadGroupCalculationRequest.model_validate(group_payload())

    assert request.jurisdiction_profile is JurisdictionProfile.IN


def test_group_accepts_a_named_profile() -> None:
    """A stated jurisdiction profile is carried on the request."""

    request = LoadGroupCalculationRequest.model_validate(group_payload(jurisdiction_profile="US"))

    assert request.jurisdiction_profile is JurisdictionProfile.US


def test_group_rejects_an_unknown_profile() -> None:
    """Only registered jurisdiction profiles are accepted."""

    with pytest.raises(ValidationError):
        LoadGroupCalculationRequest.model_validate(group_payload(jurisdiction_profile="ZZ"))


def test_group_response_carries_profile_and_assumptions() -> None:
    """The group response echoes the profile and states the A15 (e) assumption."""

    request = LoadGroupCalculationRequest.model_validate(group_payload())

    response = LoadGroupCalculationResponse.from_domain(
        calculate_load_group(request.to_domain()),
        jurisdiction_profile=request.jurisdiction_profile,
    )

    assert response.jurisdiction_profile is JurisdictionProfile.IN
    assert response.assumptions == (GROUP_COINCIDENCE_ASSUMPTION,)
    assert response.status is CalculationStatus.VALID


def test_group_response_reports_a_blank_coincidence_factor() -> None:
    """A blank coincidence factor surfaces as REVIEW_REQUIRED on the contract."""

    payload = group_payload()
    del payload["coincidence_factor"]

    request = LoadGroupCalculationRequest.model_validate(payload)

    response = LoadGroupCalculationResponse.from_domain(
        calculate_load_group(request.to_domain()),
        jurisdiction_profile=request.jurisdiction_profile,
    )

    assert response.status is CalculationStatus.REVIEW_REQUIRED
    assert [warning.code for warning in response.warnings] == [
        LoadWarningCode.COINCIDENCE_FACTOR_NOT_ESTABLISHED
    ]
    assert response.coincidence_factor == Decimal("1")


def test_group_response_serializes_decimals_as_exact_strings() -> None:
    """Engineering values leave the API as exact decimal strings, never floats."""

    request = LoadGroupCalculationRequest.model_validate(group_payload())

    response = LoadGroupCalculationResponse.from_domain(
        calculate_load_group(request.to_domain()),
        jurisdiction_profile=request.jurisdiction_profile,
    )

    data = response.model_dump(mode="json")

    assert data["connected_power_kw"] == "32.6087"
    assert data["demand_power_kw"] == "21.1304"
    assert data["load_results"][0]["design_current_a"] == "38.4272"
    assert data["jurisdiction_profile"] == "IN"


def test_load_run_create_request_minimal_payload() -> None:
    """The persisted load study is the group; the revision is optional."""

    request = LoadRunCreateRequest.model_validate({"study": group_payload()})

    assert request.project_revision_id is None
    assert request.notes is None
    assert request.study.code == "PUMP-GRP"


def test_load_run_create_request_carries_the_project_revision() -> None:
    """A chosen open revision links the run to that project."""

    revision_id = uuid4()

    request = LoadRunCreateRequest.model_validate(
        {
            "study": group_payload(),
            "project_revision_id": str(revision_id),
            "notes": "Preliminary schedule.",
        }
    )

    assert request.project_revision_id == revision_id
    assert request.notes == "Preliminary schedule."


def test_load_run_create_request_rejects_an_unknown_key() -> None:
    """The run request forbids extra keys, as the cable and fault ones do."""

    with pytest.raises(ValidationError):
        LoadRunCreateRequest.model_validate(
            {
                "study": group_payload(),
                "revision_id": str(uuid4()),
            }
        )
