"""
Unit tests for protection relay and TCC engine.
KESE-S2-M12
"""

from decimal import Decimal

import pytest

from app.domain.electrical.relay.relay_engine import (
    calculate_relay_coordination_study,
    calculate_relay_operating_point,
)
from app.domain.electrical.relay.relay_models import (
    CTConnection,
    CurrentTransformerInput,
    ProtectionRelayInput,
    RelayCoordinationStudyInput,
    RelayCurveFamily,
    RelayCurveInput,
    RelayFunction,
    RelayPickupSettings,
    RelayRole,
)
from app.domain.electrical.relay.relay_results import (
    RelayCoordinationStatus,
    RelayOperatingStatus,
    RelayWarningCode,
)


def make_ct() -> CurrentTransformerInput:
    return CurrentTransformerInput(
        primary_current_a=Decimal("800"),
        secondary_current_a=Decimal("1"),
        burden_va=Decimal("15"),
        accuracy_class="5P20",
        connection=CTConnection.STAR,
    )


def make_settings(
    **overrides: object,
) -> RelayPickupSettings:
    values: dict[str, object] = {
        "pickup_current_a": Decimal("800"),
        "time_multiplier": Decimal("0.20"),
        "instantaneous_pickup_a": None,
        "instantaneous_delay_s": Decimal("0"),
        "reset_ratio": Decimal("0.95"),
    }

    values.update(overrides)

    return RelayPickupSettings(**values)


def make_curve(
    **overrides: object,
) -> RelayCurveInput:
    values: dict[str, object] = {
        "family": RelayCurveFamily.IEC_STANDARD_INVERSE,
        "settings": make_settings(),
        "minimum_operating_time_s": Decimal("0"),
        "maximum_operating_time_s": None,
        "reference_document": "IEC 60255",
    }

    values.update(overrides)

    return RelayCurveInput(**values)


def make_relay(
    *,
    code: str = "RLY-DN-01",
    name: str = "Downstream Relay",
    role: RelayRole = RelayRole.DOWNSTREAM,
    curve: RelayCurveInput | None = None,
) -> ProtectionRelayInput:
    return ProtectionRelayInput(
        code=code,
        name=name,
        function=RelayFunction.PHASE_OVERCURRENT,
        role=role,
        ct=make_ct(),
        curve=curve or make_curve(),
        protected_equipment_code="FDR-01",
        breaker_code="VCB-01",
        grading_margin_s=Decimal("0.30"),
        coordination_group="GROUP-01",
        standard_reference="IEC 60255",
    )


@pytest.mark.unit
def test_standard_inverse_operating_point() -> None:
    result = calculate_relay_operating_point(
        make_relay(),
        Decimal("8000"),
    )

    assert result.status is RelayOperatingStatus.OPERATED
    assert result.instantaneous_operation is False
    assert result.current_multiple == Decimal("10.0000")
    assert result.operating_time_s is not None
    assert result.operating_time_s > Decimal("0")


@pytest.mark.unit
def test_very_inverse_operating_point() -> None:
    relay = make_relay(
        curve=make_curve(
            family=RelayCurveFamily.IEC_VERY_INVERSE,
        )
    )

    result = calculate_relay_operating_point(
        relay,
        Decimal("8000"),
    )

    assert result.status is RelayOperatingStatus.OPERATED
    assert result.operating_time_s is not None
    assert result.operating_time_s > Decimal("0")


@pytest.mark.unit
def test_extremely_inverse_operating_point() -> None:
    relay = make_relay(
        curve=make_curve(
            family=RelayCurveFamily.IEC_EXTREMELY_INVERSE,
        )
    )

    result = calculate_relay_operating_point(
        relay,
        Decimal("8000"),
    )

    assert result.status is RelayOperatingStatus.OPERATED
    assert result.operating_time_s is not None
    assert result.operating_time_s > Decimal("0")


@pytest.mark.unit
def test_definite_time_operation() -> None:
    relay = make_relay(
        curve=make_curve(
            family=RelayCurveFamily.DEFINITE_TIME,
            settings=make_settings(
                definite_time_delay_s=Decimal("0.50"),
            ),
        )
    )

    result = calculate_relay_operating_point(
        relay,
        Decimal("2000"),
    )

    assert result.status is RelayOperatingStatus.OPERATED
    assert result.operating_time_s == Decimal("0.5000")


@pytest.mark.unit
def test_instantaneous_operation() -> None:
    relay = make_relay(
        curve=make_curve(
            settings=make_settings(
                instantaneous_pickup_a=Decimal("5000"),
                instantaneous_delay_s=Decimal("0.05"),
            ),
        )
    )

    result = calculate_relay_operating_point(
        relay,
        Decimal("8000"),
    )

    assert result.status is RelayOperatingStatus.INSTANTANEOUS
    assert result.instantaneous_operation is True
    assert result.operating_time_s == Decimal("0.0500")


@pytest.mark.unit
def test_below_pickup_result() -> None:
    result = calculate_relay_operating_point(
        make_relay(),
        Decimal("500"),
    )

    assert result.status is RelayOperatingStatus.BELOW_PICKUP
    assert result.operating_time_s is None

    assert any(warning.code is RelayWarningCode.BELOW_PICKUP for warning in result.warnings)


@pytest.mark.unit
def test_maximum_operating_time_limit() -> None:
    relay = make_relay(
        curve=make_curve(
            maximum_operating_time_s=Decimal("0.10"),
        )
    )

    result = calculate_relay_operating_point(
        relay,
        Decimal("1600"),
    )

    assert result.operating_time_s == Decimal("0.1000")

    assert any(
        warning.code is RelayWarningCode.OPERATING_TIME_EXCEEDED for warning in result.warnings
    )


@pytest.mark.unit
def test_coordinated_relay_pair_study() -> None:
    downstream = make_relay(
        code="RLY-DN-01",
        role=RelayRole.DOWNSTREAM,
        curve=make_curve(
            settings=make_settings(
                time_multiplier=Decimal("0.10"),
            ),
        ),
    )

    upstream = make_relay(
        code="RLY-UP-01",
        name="Upstream Relay",
        role=RelayRole.UPSTREAM,
        curve=make_curve(
            settings=make_settings(
                time_multiplier=Decimal("0.40"),
            ),
        ),
    )

    study = RelayCoordinationStudyInput(
        code="TCC-001",
        name="Main Feeder Relay Coordination",
        fault_current_a=Decimal("8000"),
        relays=(downstream, upstream),
        minimum_grading_margin_s=Decimal("0.30"),
    )

    result = calculate_relay_coordination_study(study)

    assert result.evaluated_relays == 2
    assert result.evaluated_pairs == 1
    assert result.coordinated_pairs == 1
    assert result.status is RelayCoordinationStatus.COORDINATED


@pytest.mark.unit
def test_low_grading_margin_is_not_coordinated() -> None:
    downstream = make_relay(
        code="RLY-DN-01",
        role=RelayRole.DOWNSTREAM,
        curve=make_curve(
            settings=make_settings(
                time_multiplier=Decimal("0.20"),
            ),
        ),
    )

    upstream = make_relay(
        code="RLY-UP-01",
        name="Upstream Relay",
        role=RelayRole.UPSTREAM,
        curve=make_curve(
            settings=make_settings(
                time_multiplier=Decimal("0.21"),
            ),
        ),
    )

    study = RelayCoordinationStudyInput(
        code="TCC-002",
        name="Low Margin Study",
        fault_current_a=Decimal("8000"),
        relays=(downstream, upstream),
        minimum_grading_margin_s=Decimal("0.30"),
    )

    result = calculate_relay_coordination_study(study)

    assert result.status is RelayCoordinationStatus.NOT_COORDINATED

    pair = result.pair_results[0]

    assert pair.coordinated is False

    assert any(warning.code is RelayWarningCode.GRADING_MARGIN_LOW for warning in pair.warnings)


@pytest.mark.unit
def test_curve_crossing_is_detected() -> None:
    downstream = make_relay(
        code="RLY-DN-01",
        role=RelayRole.DOWNSTREAM,
        curve=make_curve(
            settings=make_settings(
                time_multiplier=Decimal("0.40"),
            ),
        ),
    )

    upstream = make_relay(
        code="RLY-UP-01",
        name="Upstream Relay",
        role=RelayRole.UPSTREAM,
        curve=make_curve(
            settings=make_settings(
                time_multiplier=Decimal("0.10"),
            ),
        ),
    )

    study = RelayCoordinationStudyInput(
        code="TCC-003",
        name="Curve Crossing Study",
        fault_current_a=Decimal("8000"),
        relays=(downstream, upstream),
        minimum_grading_margin_s=Decimal("0.30"),
    )

    result = calculate_relay_coordination_study(study)

    pair = result.pair_results[0]

    assert pair.curve_crossing_detected is True

    assert any(
        warning.code is RelayWarningCode.CURVE_CROSSING_DETECTED for warning in pair.warnings
    )


@pytest.mark.unit
def test_instantaneous_overlap_is_detected() -> None:
    instantaneous_curve = make_curve(
        settings=make_settings(
            instantaneous_pickup_a=Decimal("5000"),
            instantaneous_delay_s=Decimal("0"),
        ),
    )

    downstream = make_relay(
        code="RLY-DN-01",
        role=RelayRole.DOWNSTREAM,
        curve=instantaneous_curve,
    )

    upstream = make_relay(
        code="RLY-UP-01",
        name="Upstream Relay",
        role=RelayRole.UPSTREAM,
        curve=instantaneous_curve,
    )

    study = RelayCoordinationStudyInput(
        code="TCC-004",
        name="Instantaneous Overlap Study",
        fault_current_a=Decimal("8000"),
        relays=(downstream, upstream),
        minimum_grading_margin_s=Decimal("0.30"),
    )

    result = calculate_relay_coordination_study(study)

    pair = result.pair_results[0]

    assert pair.instantaneous_overlap is True
    assert pair.coordinated is False

    assert any(warning.code is RelayWarningCode.INSTANTANEOUS_OVERLAP for warning in pair.warnings)


@pytest.mark.unit
def test_below_pickup_pair_requires_review() -> None:
    downstream = make_relay(
        code="RLY-DN-01",
        role=RelayRole.DOWNSTREAM,
    )

    upstream = make_relay(
        code="RLY-UP-01",
        name="Upstream Relay",
        role=RelayRole.UPSTREAM,
    )

    study = RelayCoordinationStudyInput(
        code="TCC-005",
        name="Below Pickup Study",
        fault_current_a=Decimal("500"),
        relays=(downstream, upstream),
    )

    result = calculate_relay_coordination_study(study)

    assert result.evaluated_pairs == 0
    assert result.status is RelayCoordinationStatus.WARNING

    assert any(
        warning.code is RelayWarningCode.ENGINEERING_REVIEW_REQUIRED for warning in result.warnings
    )


@pytest.mark.unit
def test_invalid_relay_input_type_is_rejected() -> None:
    with pytest.raises(
        TypeError,
        match="ProtectionRelayInput record",
    ):
        calculate_relay_operating_point(
            "invalid",  # type: ignore[arg-type]
            Decimal("8000"),
        )


@pytest.mark.unit
def test_invalid_fault_current_type_is_rejected() -> None:
    with pytest.raises(
        TypeError,
        match="fault_current_a must be a Decimal",
    ):
        calculate_relay_operating_point(
            make_relay(),
            8000,  # type: ignore[arg-type]
        )


@pytest.mark.unit
def test_invalid_study_input_type_is_rejected() -> None:
    with pytest.raises(
        TypeError,
        match="RelayCoordinationStudyInput record",
    ):
        calculate_relay_coordination_study(
            "invalid"  # type: ignore[arg-type]
        )
