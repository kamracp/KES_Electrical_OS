"""
Unit tests for protection relay result models.
KESE-S2-M12
"""

from decimal import Decimal

import pytest

from app.domain.electrical.relay.relay_models import (
    RelayCurveFamily,
    RelayFunction,
    RelayRole,
)
from app.domain.electrical.relay.relay_results import (
    RelayCoordinationStatus,
    RelayCoordinationStudyResult,
    RelayOperatingPointResult,
    RelayOperatingStatus,
    RelayPairCoordinationResult,
    RelayWarning,
    RelayWarningCode,
)


def make_warning() -> RelayWarning:
    return RelayWarning(
        code=RelayWarningCode.GRADING_MARGIN_LOW,
        message="Relay grading margin is low.",
    )


def make_operating_point(
    **overrides: object,
) -> RelayOperatingPointResult:
    values: dict[str, object] = {
        "relay_code": "RLY-DN-01",
        "relay_name": "Downstream Relay",
        "function": RelayFunction.PHASE_OVERCURRENT,
        "role": RelayRole.DOWNSTREAM,
        "curve_family": RelayCurveFamily.IEC_STANDARD_INVERSE,
        "fault_current_a": Decimal("10000"),
        "pickup_current_a": Decimal("800"),
        "current_multiple": Decimal("12.5"),
        "operating_time_s": Decimal("0.30"),
        "instantaneous_operation": False,
        "status": RelayOperatingStatus.OPERATED,
        "warnings": (),
    }

    values.update(overrides)

    return RelayOperatingPointResult(**values)


def make_pair_result(
    **overrides: object,
) -> RelayPairCoordinationResult:
    values: dict[str, object] = {
        "downstream_relay_code": "RLY-DN-01",
        "upstream_relay_code": "RLY-UP-01",
        "downstream_operating_time_s": Decimal("0.30"),
        "upstream_operating_time_s": Decimal("0.70"),
        "grading_margin_s": Decimal("0.40"),
        "required_grading_margin_s": Decimal("0.30"),
        "coordinated": True,
        "curve_crossing_detected": False,
        "instantaneous_overlap": False,
        "warnings": (),
    }

    values.update(overrides)

    return RelayPairCoordinationResult(**values)


def make_study_result(
    **overrides: object,
) -> RelayCoordinationStudyResult:
    operating_points = (
        make_operating_point(),
        make_operating_point(
            relay_code="RLY-UP-01",
            relay_name="Upstream Relay",
            role=RelayRole.UPSTREAM,
            operating_time_s=Decimal("0.70"),
        ),
    )

    pair_results = (make_pair_result(),)

    values: dict[str, object] = {
        "code": "TCC-001",
        "name": "Main Feeder Relay Coordination",
        "fault_current_a": Decimal("10000"),
        "evaluated_relays": 2,
        "evaluated_pairs": 1,
        "coordinated_pairs": 1,
        "operating_points": operating_points,
        "pair_results": pair_results,
        "maximum_operating_time_s": Decimal("0.70"),
        "minimum_grading_margin_s": Decimal("0.40"),
        "status": RelayCoordinationStatus.COORDINATED,
        "warnings": (),
    }

    values.update(overrides)

    return RelayCoordinationStudyResult(**values)


@pytest.mark.unit
def test_create_valid_warning() -> None:
    warning = make_warning()

    assert warning.code is RelayWarningCode.GRADING_MARGIN_LOW
    assert warning.message == "Relay grading margin is low."


@pytest.mark.unit
def test_warning_message_is_trimmed() -> None:
    warning = RelayWarning(
        code=RelayWarningCode.ENGINEERING_REVIEW_REQUIRED,
        message="  Engineering review required.  ",
    )

    assert warning.message == "Engineering review required."


@pytest.mark.unit
def test_create_valid_operating_point() -> None:
    result = make_operating_point()

    assert result.relay_code == "RLY-DN-01"
    assert result.status is RelayOperatingStatus.OPERATED
    assert result.operating_time_s == Decimal("0.30")


@pytest.mark.unit
def test_operated_result_requires_time() -> None:
    with pytest.raises(
        ValueError,
        match="requires operating_time_s",
    ):
        make_operating_point(
            operating_time_s=None,
        )


@pytest.mark.unit
def test_below_pickup_result_rejects_time() -> None:
    with pytest.raises(
        ValueError,
        match="must not contain operating_time_s",
    ):
        make_operating_point(
            status=RelayOperatingStatus.BELOW_PICKUP,
            operating_time_s=Decimal("1"),
        )


@pytest.mark.unit
def test_duplicate_operating_point_warnings_are_rejected() -> None:
    warning = make_warning()

    with pytest.raises(
        ValueError,
        match="operating-point warning codes must be unique",
    ):
        make_operating_point(
            warnings=(warning, warning),
        )


@pytest.mark.unit
def test_create_valid_pair_result() -> None:
    result = make_pair_result()

    assert result.coordinated is True
    assert result.grading_margin_s == Decimal("0.40")


@pytest.mark.unit
def test_duplicate_pair_warnings_are_rejected() -> None:
    warning = make_warning()

    with pytest.raises(
        ValueError,
        match="relay-pair warning codes must be unique",
    ):
        make_pair_result(
            warnings=(warning, warning),
        )


@pytest.mark.unit
def test_create_valid_study_result() -> None:
    result = make_study_result()

    assert result.code == "TCC-001"
    assert result.evaluated_relays == 2
    assert result.coordinated_pairs == 1
    assert result.status is RelayCoordinationStatus.COORDINATED


@pytest.mark.unit
def test_coordinated_pairs_cannot_exceed_evaluated_pairs() -> None:
    with pytest.raises(
        ValueError,
        match="must not exceed evaluated_pairs",
    ):
        make_study_result(
            evaluated_pairs=1,
            coordinated_pairs=2,
        )


@pytest.mark.unit
def test_operating_point_count_must_match() -> None:
    with pytest.raises(
        ValueError,
        match="operating_points count must equal",
    ):
        make_study_result(
            operating_points=(),
        )


@pytest.mark.unit
def test_pair_result_count_must_match() -> None:
    with pytest.raises(
        ValueError,
        match="pair_results count must equal",
    ):
        make_study_result(
            pair_results=(),
        )


@pytest.mark.unit
def test_duplicate_study_warnings_are_rejected() -> None:
    warning = make_warning()

    with pytest.raises(
        ValueError,
        match="study warning codes must be unique",
    ):
        make_study_result(
            status=RelayCoordinationStatus.WARNING,
            warnings=(warning, warning),
        )
