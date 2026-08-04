"""
Pure domain engine for protection relay and TCC calculations.
KESE-S2-M12
"""

from decimal import Decimal, ROUND_HALF_UP, localcontext

from app.domain.electrical.relay.relay_models import (
    ProtectionRelayInput,
    RelayCoordinationStudyInput,
    RelayCurveFamily,
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


DECIMAL_QUANTUM = Decimal("0.0001")


IEC_CURVE_CONSTANTS: dict[
    RelayCurveFamily,
    tuple[Decimal, Decimal],
] = {
    RelayCurveFamily.IEC_STANDARD_INVERSE: (
        Decimal("0.14"),
        Decimal("0.02"),
    ),
    RelayCurveFamily.IEC_VERY_INVERSE: (
        Decimal("13.5"),
        Decimal("1"),
    ),
    RelayCurveFamily.IEC_EXTREMELY_INVERSE: (
        Decimal("80"),
        Decimal("2"),
    ),
    RelayCurveFamily.IEC_LONG_TIME_INVERSE: (
        Decimal("120"),
        Decimal("1"),
    ),
}


def _round_value(
    value: Decimal,
) -> Decimal:
    """Round an engineering value to four decimal places."""

    return value.quantize(
        DECIMAL_QUANTUM,
        rounding=ROUND_HALF_UP,
    )


def _calculate_current_multiple(
    fault_current_a: Decimal,
    pickup_current_a: Decimal,
) -> Decimal:
    """Return fault current divided by relay pickup current."""

    with localcontext() as context:
        context.prec = 50

        return fault_current_a / pickup_current_a


def _calculate_iec_inverse_time(
    *,
    current_multiple: Decimal,
    time_multiplier: Decimal,
    curve_family: RelayCurveFamily,
) -> Decimal:
    """Calculate IEC inverse-time relay operating time."""

    if curve_family not in IEC_CURVE_CONSTANTS:
        raise ValueError("curve_family is not a supported IEC inverse curve")

    if current_multiple <= Decimal("1"):
        raise ValueError("current_multiple must be greater than 1 for inverse-time operation")

    curve_constant, exponent = IEC_CURVE_CONSTANTS[curve_family]

    with localcontext() as context:
        context.prec = 50

        denominator = current_multiple**exponent - Decimal("1")

        operating_time_s = curve_constant * time_multiplier / denominator

    return operating_time_s


def _apply_operating_time_limits(
    relay: ProtectionRelayInput,
    operating_time_s: Decimal,
) -> Decimal:
    """Apply minimum and maximum operating-time limits."""

    limited_time = max(
        operating_time_s,
        relay.curve.minimum_operating_time_s,
    )

    if relay.curve.maximum_operating_time_s is not None:
        limited_time = min(
            limited_time,
            relay.curve.maximum_operating_time_s,
        )

    return limited_time


def _instantaneous_operation_applies(
    relay: ProtectionRelayInput,
    fault_current_a: Decimal,
) -> bool:
    """Return whether instantaneous pickup is reached."""

    instantaneous_pickup_a = relay.curve.settings.instantaneous_pickup_a

    return instantaneous_pickup_a is not None and fault_current_a >= instantaneous_pickup_a


def _calculate_relay_operating_time(
    relay: ProtectionRelayInput,
    fault_current_a: Decimal,
) -> tuple[
    Decimal | None,
    RelayOperatingStatus,
    bool,
]:
    """Calculate one relay operating time and status."""

    pickup_current_a = relay.curve.settings.pickup_current_a

    if fault_current_a < pickup_current_a:
        return (
            None,
            RelayOperatingStatus.BELOW_PICKUP,
            False,
        )

    if _instantaneous_operation_applies(
        relay,
        fault_current_a,
    ):
        return (
            relay.curve.settings.instantaneous_delay_s,
            RelayOperatingStatus.INSTANTANEOUS,
            True,
        )

    if relay.curve.family is RelayCurveFamily.INSTANTANEOUS:
        return (
            Decimal("0"),
            RelayOperatingStatus.INSTANTANEOUS,
            True,
        )

    if relay.curve.family is RelayCurveFamily.DEFINITE_TIME:
        definite_time_delay_s = relay.curve.settings.definite_time_delay_s

        if definite_time_delay_s is None:
            raise ValueError("DEFINITE_TIME relay requires definite_time_delay_s")

        operating_time_s = _apply_operating_time_limits(
            relay,
            definite_time_delay_s,
        )

        return (
            operating_time_s,
            RelayOperatingStatus.OPERATED,
            False,
        )

    current_multiple = _calculate_current_multiple(
        fault_current_a,
        pickup_current_a,
    )

    operating_time_s = _calculate_iec_inverse_time(
        current_multiple=current_multiple,
        time_multiplier=(relay.curve.settings.time_multiplier),
        curve_family=relay.curve.family,
    )

    operating_time_s = _apply_operating_time_limits(
        relay,
        operating_time_s,
    )

    return (
        operating_time_s,
        RelayOperatingStatus.OPERATED,
        False,
    )


def calculate_relay_operating_point(
    relay: ProtectionRelayInput,
    fault_current_a: Decimal,
) -> RelayOperatingPointResult:
    """Calculate one relay operating point."""

    if not isinstance(
        relay,
        ProtectionRelayInput,
    ):
        raise TypeError("relay must be a ProtectionRelayInput record")

    if not isinstance(
        fault_current_a,
        Decimal,
    ):
        raise TypeError("fault_current_a must be a Decimal")

    if fault_current_a <= Decimal("0"):
        raise ValueError("fault_current_a must be greater than zero")

    operating_time_s, status, instantaneous = _calculate_relay_operating_time(
        relay,
        fault_current_a,
    )

    current_multiple = _calculate_current_multiple(
        fault_current_a,
        relay.curve.settings.pickup_current_a,
    )

    warnings: list[RelayWarning] = []

    if status is RelayOperatingStatus.BELOW_PICKUP:
        warnings.append(
            RelayWarning(
                code=RelayWarningCode.BELOW_PICKUP,
                message=("Fault current is below the relay pickup setting."),
            )
        )

    if (
        operating_time_s is not None
        and relay.curve.maximum_operating_time_s is not None
        and operating_time_s >= relay.curve.maximum_operating_time_s
    ):
        warnings.append(
            RelayWarning(
                code=(RelayWarningCode.OPERATING_TIME_EXCEEDED),
                message=(
                    "Relay operating time reached the configured maximum operating-time limit."
                ),
            )
        )

    return RelayOperatingPointResult(
        relay_code=relay.code,
        relay_name=relay.name,
        function=relay.function,
        role=relay.role,
        curve_family=relay.curve.family,
        fault_current_a=_round_value(fault_current_a),
        pickup_current_a=_round_value(relay.curve.settings.pickup_current_a),
        current_multiple=_round_value(current_multiple),
        operating_time_s=(_round_value(operating_time_s) if operating_time_s is not None else None),
        instantaneous_operation=instantaneous,
        status=status,
        warnings=tuple(warnings),
    )


def _calculate_pair_coordination(
    downstream_point: RelayOperatingPointResult,
    upstream_point: RelayOperatingPointResult,
    required_grading_margin_s: Decimal,
) -> RelayPairCoordinationResult:
    """Calculate coordination between one relay pair."""

    if downstream_point.operating_time_s is None:
        raise ValueError("downstream relay must have an operating time")

    if upstream_point.operating_time_s is None:
        raise ValueError("upstream relay must have an operating time")

    grading_margin_s = upstream_point.operating_time_s - downstream_point.operating_time_s

    instantaneous_overlap = (
        downstream_point.instantaneous_operation and upstream_point.instantaneous_operation
    )

    curve_crossing_detected = grading_margin_s < Decimal("0")

    coordinated = (
        grading_margin_s >= required_grading_margin_s
        and not curve_crossing_detected
        and not instantaneous_overlap
    )

    warnings: list[RelayWarning] = []

    if grading_margin_s < required_grading_margin_s:
        warnings.append(
            RelayWarning(
                code=RelayWarningCode.GRADING_MARGIN_LOW,
                message=("Relay grading margin is below the required coordination margin."),
            )
        )

    if curve_crossing_detected:
        warnings.append(
            RelayWarning(
                code=RelayWarningCode.CURVE_CROSSING_DETECTED,
                message=(
                    "The upstream relay operates faster than "
                    "the downstream relay at the study current."
                ),
            )
        )

    if instantaneous_overlap:
        warnings.append(
            RelayWarning(
                code=RelayWarningCode.INSTANTANEOUS_OVERLAP,
                message=(
                    "Both downstream and upstream relays operate "
                    "instantaneously at the study current."
                ),
            )
        )

    return RelayPairCoordinationResult(
        downstream_relay_code=downstream_point.relay_code,
        upstream_relay_code=upstream_point.relay_code,
        downstream_operating_time_s=(downstream_point.operating_time_s),
        upstream_operating_time_s=(upstream_point.operating_time_s),
        grading_margin_s=_round_value(grading_margin_s),
        required_grading_margin_s=_round_value(required_grading_margin_s),
        coordinated=coordinated,
        curve_crossing_detected=curve_crossing_detected,
        instantaneous_overlap=instantaneous_overlap,
        warnings=tuple(warnings),
    )


def calculate_relay_coordination_study(
    sizing_input: RelayCoordinationStudyInput,
) -> RelayCoordinationStudyResult:
    """Calculate a multi-relay coordination study."""

    if not isinstance(
        sizing_input,
        RelayCoordinationStudyInput,
    ):
        raise TypeError("sizing_input must be a RelayCoordinationStudyInput record")

    operating_points = tuple(
        calculate_relay_operating_point(
            relay,
            sizing_input.fault_current_a,
        )
        for relay in sizing_input.relays
    )

    pair_results: list[RelayPairCoordinationResult] = []

    for index in range(len(operating_points) - 1):
        downstream_point = operating_points[index]
        upstream_point = operating_points[index + 1]

        if downstream_point.operating_time_s is None or upstream_point.operating_time_s is None:
            continue

        pair_results.append(
            _calculate_pair_coordination(
                downstream_point,
                upstream_point,
                sizing_input.minimum_grading_margin_s,
            )
        )

    coordinated_pairs = sum(1 for result in pair_results if result.coordinated)

    warnings: list[RelayWarning] = []

    if len(pair_results) != len(operating_points) - 1:
        warnings.append(
            RelayWarning(
                code=RelayWarningCode.ENGINEERING_REVIEW_REQUIRED,
                message=(
                    "One or more relay pairs could not be evaluated "
                    "because an operating time was unavailable."
                ),
            )
        )

    if any(not result.coordinated for result in pair_results):
        warnings.append(
            RelayWarning(
                code=RelayWarningCode.ENGINEERING_REVIEW_REQUIRED,
                message=("One or more relay pairs are not coordinated."),
            )
        )

    operating_times = tuple(
        point.operating_time_s for point in operating_points if point.operating_time_s is not None
    )

    maximum_operating_time_s = max(operating_times) if operating_times else None

    grading_margins = tuple(result.grading_margin_s for result in pair_results)

    minimum_grading_margin_s = min(grading_margins) if grading_margins else None

    if pair_results and all(result.coordinated for result in pair_results):
        status = RelayCoordinationStatus.COORDINATED
    elif pair_results:
        status = RelayCoordinationStatus.NOT_COORDINATED
    else:
        status = RelayCoordinationStatus.WARNING

    return RelayCoordinationStudyResult(
        code=sizing_input.code,
        name=sizing_input.name,
        fault_current_a=_round_value(sizing_input.fault_current_a),
        evaluated_relays=len(operating_points),
        evaluated_pairs=len(pair_results),
        coordinated_pairs=coordinated_pairs,
        operating_points=operating_points,
        pair_results=tuple(pair_results),
        maximum_operating_time_s=(
            _round_value(maximum_operating_time_s) if maximum_operating_time_s is not None else None
        ),
        minimum_grading_margin_s=(
            _round_value(minimum_grading_margin_s) if minimum_grading_margin_s is not None else None
        ),
        status=status,
        warnings=tuple(warnings),
    )


__all__ = [
    "calculate_relay_coordination_study",
    "calculate_relay_operating_point",
]
