"""Unit tests for the transformer sizing schemas (EOS-03a, Master Prompt A16)."""

from decimal import Decimal
from typing import Any
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.domain.electrical.jurisdiction.jurisdiction_models import JurisdictionProfile
from app.domain.electrical.sources.engine import calculate_transformer_sizing
from app.schemas.calculation_run import TransformerRunCreateRequest
from app.schemas.transformer_sizing import (
    TransformerSizingRequest,
    TransformerSizingResponse,
)

pytestmark = pytest.mark.unit

FACTORS = (
    "future_growth_factor",
    "design_margin_factor",
    "ambient_derating_factor",
    "altitude_derating_factor",
    "harmonic_derating_factor",
)


def study(**overrides: Any) -> dict[str, Any]:
    """A valid transformer sizing request payload."""

    payload: dict[str, Any] = {
        "code": "TR-001",
        "name": "Main Transformer",
        "demand_power_kw": "800",
        "demand_power_factor": "0.80",
        "available_unit_ratings_kva": ["1000", "1250", "1600"],
        "future_growth_factor": "1",
        "design_margin_factor": "1.10",
        "ambient_derating_factor": "1",
        "altitude_derating_factor": "1",
        "harmonic_derating_factor": "1",
    }
    payload.update(overrides)

    return payload


@pytest.mark.parametrize("field_name", FACTORS)
def test_a_blank_factor_reaches_the_domain_as_none(field_name: str) -> None:
    """A blank factor is not filled in by the schema (A16 (a))."""

    payload = study()
    del payload[field_name]

    sizing_input = TransformerSizingRequest.model_validate(payload).to_domain()

    assert getattr(sizing_input, field_name) is None


def test_every_factor_may_be_left_blank_at_once() -> None:
    """None of the five carries a silent default any more; 1.10 is gone."""

    payload = study()
    for field_name in FACTORS:
        del payload[field_name]

    request = TransformerSizingRequest.model_validate(payload)
    sizing_input = request.to_domain()

    for field_name in FACTORS:
        assert getattr(request, field_name) is None
        assert getattr(sizing_input, field_name) is None
    # The demand power factor is an engineering input, not a margin: still required.
    assert sizing_input.demand_power_factor == Decimal("0.80")


@pytest.mark.parametrize(
    ("field_name", "field_value"),
    [
        ("future_growth_factor", "0.99"),
        ("design_margin_factor", "0.5"),
        ("ambient_derating_factor", "1.01"),
        ("altitude_derating_factor", "0"),
        ("harmonic_derating_factor", "-0.1"),
        ("demand_power_factor", "1.01"),
    ],
)
def test_given_factors_keep_their_bounds(field_name: str, field_value: str) -> None:
    """A factor that IS given is still bound to its permitted range."""

    with pytest.raises(ValidationError):
        TransformerSizingRequest.model_validate(study(**{field_name: field_value}))


def test_a_missing_demand_power_factor_is_refused() -> None:
    """The demand power factor has no default and cannot be left out."""

    payload = study()
    del payload["demand_power_factor"]

    with pytest.raises(ValidationError):
        TransformerSizingRequest.model_validate(payload)


def test_float_engineering_value_is_still_rejected() -> None:
    """Binary floating-point engineering inputs stay refused."""

    with pytest.raises(ValidationError) as error:
        TransformerSizingRequest.model_validate(study(design_margin_factor=1.1))

    assert "must be provided as strings" in str(error.value)


def test_request_without_a_profile_defaults_to_in() -> None:
    """The jurisdiction profile defaults to IN, as Cable, Fault and Load do."""

    assert (
        TransformerSizingRequest.model_validate(study()).jurisdiction_profile
        is JurisdictionProfile.IN
    )


def test_request_accepts_a_named_profile() -> None:
    """A stated jurisdiction profile is carried on the request."""

    request = TransformerSizingRequest.model_validate(study(jurisdiction_profile="US"))

    assert request.jurisdiction_profile is JurisdictionProfile.US


def test_request_rejects_an_unknown_profile() -> None:
    """Only registered jurisdiction profiles are accepted."""

    with pytest.raises(ValidationError):
        TransformerSizingRequest.model_validate(study(jurisdiction_profile="ZZ"))


def test_response_echoes_the_profile_and_stays_exact() -> None:
    """The response carries the requested profile and exact decimal strings."""

    request = TransformerSizingRequest.model_validate(study())

    response = TransformerSizingResponse.from_domain(
        calculate_transformer_sizing(request.to_domain()),
        jurisdiction_profile=request.jurisdiction_profile,
    )
    data = response.model_dump(mode="json")

    assert response.jurisdiction_profile is JurisdictionProfile.IN
    assert data["jurisdiction_profile"] == "IN"
    assert data["base_demand_kva"] == "1000.0000"
    assert data["design_required_kva"] == "1100.0000"
    assert data["selected_unit_rating_kva"] == "1250"
    assert data["status"] == "VALID"


def test_response_reports_a_blank_design_margin() -> None:
    """A blank margin surfaces as REVIEW_REQUIRED on the contract, not as 1.10."""

    payload = study(demand_power_factor="1")
    del payload["design_margin_factor"]

    request = TransformerSizingRequest.model_validate(payload)
    response = TransformerSizingResponse.from_domain(
        calculate_transformer_sizing(request.to_domain()),
        jurisdiction_profile=request.jurisdiction_profile,
    )
    data = response.model_dump(mode="json")

    assert data["status"] == "REVIEW_REQUIRED"
    assert [warning["code"] for warning in data["warnings"]] == ["DESIGN_MARGIN_NOT_ESTABLISHED"]
    # Sized with 1, and the response records the factor it used.
    assert data["design_required_kva"] == "800.0000"
    assert data["design_margin_factor"] == "1"


def test_transformer_run_create_request_minimal_payload() -> None:
    """The persisted study is the sizing request; the revision is optional."""

    request = TransformerRunCreateRequest.model_validate({"study": study()})

    assert request.project_revision_id is None
    assert request.notes is None
    assert request.study.code == "TR-001"


def test_transformer_run_create_request_carries_the_project_revision() -> None:
    """A chosen open revision links the run to that project."""

    revision_id = uuid4()

    request = TransformerRunCreateRequest.model_validate(
        {
            "study": study(),
            "project_revision_id": str(revision_id),
            "notes": "Preliminary sizing.",
        }
    )

    assert request.project_revision_id == revision_id
    assert request.notes == "Preliminary sizing."


def test_transformer_run_create_request_rejects_an_unknown_key() -> None:
    """The run request forbids extra keys, as the cable, fault and load ones do."""

    with pytest.raises(ValidationError):
        TransformerRunCreateRequest.model_validate({"study": study(), "revision_id": str(uuid4())})
