"""
Pure IEC 60909 short-circuit and earth-fault calculation engine.
KESE-S2-M15
"""

from dataclasses import dataclass, replace
from decimal import ROUND_HALF_UP, Decimal, localcontext

from app.domain.electrical.fault.fault_models import (
    FaultBusInput,
    FaultSourceInput,
    FaultType,
    ShortCircuitCase,
    ShortCircuitStudyInput,
    SourceRepresentation,
)
from app.domain.electrical.fault.fault_network import (
    SequenceNetworkReduction,
    reduce_sequence_network,
)
from app.domain.electrical.fault.fault_results import (
    EquivalentSequenceImpedanceResult,
    FaultEngineeringWarning,
    FaultResultStatus,
    FaultSequence,
    FaultSourceContributionResult,
    FaultWarningCode,
    FaultWarningSeverity,
    ShortCircuitStudyResult,
)

CURRENT_QUANTUM = Decimal("0.000000001")
IMPEDANCE_QUANTUM = Decimal("0.000000001")
RATIO_QUANTUM = Decimal("0.000001")

THREE = Decimal("3")
TWO = Decimal("2")
ONE_THOUSAND = Decimal("1000")


@dataclass(frozen=True, slots=True)
class _ComplexDecimal:
    """Minimal Decimal complex arithmetic for fault-loop equations."""

    real: Decimal
    imag: Decimal

    @classmethod
    def from_components(
        cls,
        resistance_ohm: Decimal,
        reactance_ohm: Decimal,
    ) -> "_ComplexDecimal":
        return cls(
            real=resistance_ohm,
            imag=reactance_ohm,
        )

    def __add__(
        self,
        other: "_ComplexDecimal",
    ) -> "_ComplexDecimal":
        return _ComplexDecimal(
            self.real + other.real,
            self.imag + other.imag,
        )

    def __sub__(
        self,
        other: "_ComplexDecimal",
    ) -> "_ComplexDecimal":
        return _ComplexDecimal(
            self.real - other.real,
            self.imag - other.imag,
        )

    def __mul__(
        self,
        other: "_ComplexDecimal",
    ) -> "_ComplexDecimal":
        return _ComplexDecimal(
            self.real * other.real - self.imag * other.imag,
            self.real * other.imag + self.imag * other.real,
        )

    def __truediv__(
        self,
        other: "_ComplexDecimal",
    ) -> "_ComplexDecimal":
        denominator = other.magnitude_squared()

        if denominator == Decimal("0"):
            raise ZeroDivisionError("fault calculation cannot divide by zero impedance")

        return _ComplexDecimal(
            (self.real * other.real + self.imag * other.imag) / denominator,
            (self.imag * other.real - self.real * other.imag) / denominator,
        )

    def __neg__(self) -> "_ComplexDecimal":
        return _ComplexDecimal(
            -self.real,
            -self.imag,
        )

    def scale(
        self,
        factor: Decimal,
    ) -> "_ComplexDecimal":
        return _ComplexDecimal(
            self.real * factor,
            self.imag * factor,
        )

    def magnitude_squared(self) -> Decimal:
        return self.real * self.real + self.imag * self.imag

    def magnitude(self) -> Decimal:
        return self.magnitude_squared().sqrt()


@dataclass(frozen=True, slots=True)
class _PassiveFaultCalculation:
    """Unrounded passive-network fault-current calculation."""

    initial_current_ka: Decimal
    earth_fault_current_ka: Decimal | None
    peak_loop_impedance: _ComplexDecimal | None


def _round_current(
    value: Decimal,
) -> Decimal:
    return value.quantize(
        CURRENT_QUANTUM,
        rounding=ROUND_HALF_UP,
    )


def _round_impedance(
    value: Decimal,
) -> Decimal:
    return value.quantize(
        IMPEDANCE_QUANTUM,
        rounding=ROUND_HALF_UP,
    )


def _round_ratio(
    value: Decimal,
) -> Decimal:
    return value.quantize(
        RATIO_QUANTUM,
        rounding=ROUND_HALF_UP,
    )


def _required_sequences(
    fault_type: FaultType,
) -> tuple[FaultSequence, ...]:
    if fault_type is FaultType.THREE_PHASE:
        return (FaultSequence.POSITIVE,)

    if fault_type is FaultType.TWO_PHASE:
        return (
            FaultSequence.POSITIVE,
            FaultSequence.NEGATIVE,
        )

    return (
        FaultSequence.POSITIVE,
        FaultSequence.NEGATIVE,
        FaultSequence.ZERO,
    )


def _fault_bus(
    study: ShortCircuitStudyInput,
) -> FaultBusInput:
    return next(bus for bus in study.buses if bus.code == study.fault.bus_code)


def _voltage_factor(
    study: ShortCircuitStudyInput,
) -> Decimal:
    bus = _fault_bus(study)

    if study.calculation_case is ShortCircuitCase.MAXIMUM:
        return bus.voltage_factor_max

    return bus.voltage_factor_min


def _fault_impedance(
    study: ShortCircuitStudyInput,
) -> _ComplexDecimal:
    return _ComplexDecimal(
        study.fault.fault_resistance_ohm,
        study.fault.fault_reactance_ohm,
    )


def _sequence_impedance(
    reduction: SequenceNetworkReduction,
) -> _ComplexDecimal | None:
    if (
        not reduction.available
        or reduction.resistance_ohm is None
        or reduction.reactance_ohm is None
    ):
        return None

    return _ComplexDecimal(
        reduction.resistance_ohm,
        reduction.reactance_ohm,
    )


def _equivalent_sequence_result(
    reduction: SequenceNetworkReduction,
) -> EquivalentSequenceImpedanceResult:
    if reduction.available:
        assert reduction.resistance_ohm is not None
        assert reduction.reactance_ohm is not None

        return EquivalentSequenceImpedanceResult(
            sequence=reduction.sequence,
            available=True,
            resistance_ohm=_round_impedance(reduction.resistance_ohm),
            reactance_ohm=_round_impedance(reduction.reactance_ohm),
            path_reference_codes=(reduction.path_reference_codes),
            blocking_reference_codes=(),
        )

    return EquivalentSequenceImpedanceResult(
        sequence=reduction.sequence,
        available=False,
        resistance_ohm=None,
        reactance_ohm=None,
        path_reference_codes=(),
        blocking_reference_codes=(reduction.blocking_reference_codes),
    )


def _append_warning(
    warnings: list[FaultEngineeringWarning],
    *,
    code: FaultWarningCode,
    severity: FaultWarningSeverity,
    message: str,
    reference_code: str | None = None,
) -> None:
    key = (
        code,
        reference_code,
    )

    existing_keys = {
        (
            warning.code,
            warning.reference_code,
        )
        for warning in warnings
    }

    if key in existing_keys:
        return

    warnings.append(
        FaultEngineeringWarning(
            code=code,
            severity=severity,
            message=message,
            reference_code=reference_code,
        )
    )


def _phase_voltage_v(
    study: ShortCircuitStudyInput,
) -> Decimal:
    bus = _fault_bus(study)

    return _voltage_factor(study) * bus.nominal_voltage_v / THREE.sqrt()


def _current_ka(
    voltage_v: Decimal,
    impedance: _ComplexDecimal,
) -> Decimal:
    magnitude = impedance.magnitude()

    if magnitude == Decimal("0"):
        raise ZeroDivisionError("fault loop impedance must not be zero")

    return voltage_v / magnitude / ONE_THOUSAND


def _calculate_three_phase(
    study: ShortCircuitStudyInput,
    positive: _ComplexDecimal,
) -> _PassiveFaultCalculation:
    fault_impedance = _fault_impedance(study)

    loop_impedance = positive + fault_impedance

    current_ka = _current_ka(
        _phase_voltage_v(study),
        loop_impedance,
    )

    return _PassiveFaultCalculation(
        initial_current_ka=current_ka,
        earth_fault_current_ka=None,
        peak_loop_impedance=loop_impedance,
    )


def _calculate_two_phase(
    study: ShortCircuitStudyInput,
    positive: _ComplexDecimal,
    negative: _ComplexDecimal,
) -> _PassiveFaultCalculation:
    fault_impedance = _fault_impedance(study)

    loop_impedance = positive + negative + fault_impedance

    current_ka = THREE.sqrt() * _phase_voltage_v(study) / loop_impedance.magnitude() / ONE_THOUSAND

    return _PassiveFaultCalculation(
        initial_current_ka=current_ka,
        earth_fault_current_ka=None,
        peak_loop_impedance=None,
    )


def _calculate_single_phase_to_earth(
    study: ShortCircuitStudyInput,
    positive: _ComplexDecimal,
    negative: _ComplexDecimal,
    zero: _ComplexDecimal | None,
) -> _PassiveFaultCalculation:
    if zero is None:
        return _PassiveFaultCalculation(
            initial_current_ka=Decimal("0"),
            earth_fault_current_ka=Decimal("0"),
            peak_loop_impedance=None,
        )

    fault_impedance = _fault_impedance(study).scale(THREE)

    loop_impedance = positive + negative + zero + fault_impedance

    current_ka = THREE * _phase_voltage_v(study) / loop_impedance.magnitude() / ONE_THOUSAND

    return _PassiveFaultCalculation(
        initial_current_ka=current_ka,
        earth_fault_current_ka=current_ka,
        peak_loop_impedance=None,
    )


def _calculate_two_phase_to_earth(
    study: ShortCircuitStudyInput,
    positive: _ComplexDecimal,
    negative: _ComplexDecimal,
    zero: _ComplexDecimal | None,
) -> _PassiveFaultCalculation:
    if zero is None:
        fallback = _calculate_two_phase(
            study,
            positive,
            negative,
        )

        return _PassiveFaultCalculation(
            initial_current_ka=(fallback.initial_current_ka),
            earth_fault_current_ka=Decimal("0"),
            peak_loop_impedance=None,
        )

    fault_impedance = _fault_impedance(study).scale(THREE)

    zero_fault_path = zero + fault_impedance

    parallel_denominator = negative + zero_fault_path

    positive_denominator = positive + (negative * zero_fault_path / parallel_denominator)

    phase_voltage = _phase_voltage_v(study)

    positive_current = (
        _ComplexDecimal(
            phase_voltage,
            Decimal("0"),
        )
        / positive_denominator
    )

    negative_current = -(positive_current * zero_fault_path / parallel_denominator)

    zero_current = -(positive_current * negative / parallel_denominator)

    sqrt_three = THREE.sqrt()

    phase_operator = _ComplexDecimal(
        Decimal("-0.5"),
        sqrt_three / TWO,
    )

    phase_operator_squared = phase_operator * phase_operator

    phase_b_current = (
        phase_operator_squared * positive_current + phase_operator * negative_current + zero_current
    )

    phase_c_current = (
        phase_operator * positive_current + phase_operator_squared * negative_current + zero_current
    )

    maximum_phase_current_ka = (
        max(
            phase_b_current.magnitude(),
            phase_c_current.magnitude(),
        )
        / ONE_THOUSAND
    )

    earth_current_ka = zero_current.scale(THREE).magnitude() / ONE_THOUSAND

    return _PassiveFaultCalculation(
        initial_current_ka=(maximum_phase_current_ka),
        earth_fault_current_ka=(earth_current_ka),
        peak_loop_impedance=None,
    )


def _calculate_passive_fault(
    study: ShortCircuitStudyInput,
    reductions: dict[
        FaultSequence,
        SequenceNetworkReduction,
    ],
) -> _PassiveFaultCalculation:
    positive = _sequence_impedance(reductions[FaultSequence.POSITIVE])

    if positive is None:
        earth_current = (
            Decimal("0")
            if study.fault.fault_type
            in {
                FaultType.TWO_PHASE_TO_EARTH,
                FaultType.SINGLE_PHASE_TO_EARTH,
            }
            else None
        )

        return _PassiveFaultCalculation(
            initial_current_ka=Decimal("0"),
            earth_fault_current_ka=earth_current,
            peak_loop_impedance=None,
        )

    if study.fault.fault_type is FaultType.THREE_PHASE:
        return _calculate_three_phase(
            study,
            positive,
        )

    negative = _sequence_impedance(reductions[FaultSequence.NEGATIVE])

    if negative is None:
        earth_current = (
            Decimal("0")
            if study.fault.fault_type
            in {
                FaultType.TWO_PHASE_TO_EARTH,
                FaultType.SINGLE_PHASE_TO_EARTH,
            }
            else None
        )

        return _PassiveFaultCalculation(
            initial_current_ka=Decimal("0"),
            earth_fault_current_ka=earth_current,
            peak_loop_impedance=None,
        )

    if study.fault.fault_type is FaultType.TWO_PHASE:
        return _calculate_two_phase(
            study,
            positive,
            negative,
        )

    zero = _sequence_impedance(reductions[FaultSequence.ZERO])

    if study.fault.fault_type is FaultType.SINGLE_PHASE_TO_EARTH:
        return _calculate_single_phase_to_earth(
            study,
            positive,
            negative,
            zero,
        )

    return _calculate_two_phase_to_earth(
        study,
        positive,
        negative,
        zero,
    )


def _current_injection_total(
    study: ShortCircuitStudyInput,
    warnings: list[FaultEngineeringWarning],
) -> Decimal:
    total = Decimal("0")

    for source in study.sources:
        if (
            not source.in_service
            or source.representation is not SourceRepresentation.CURRENT_INJECTION
        ):
            continue

        if study.fault.fault_type is not FaultType.THREE_PHASE:
            _append_warning(
                warnings,
                code=(FaultWarningCode.CURRENT_INJECTION_APPROXIMATION),
                severity=(FaultWarningSeverity.WARNING),
                message=(
                    "Current-injection source was excluded "
                    "from the unbalanced fault current because "
                    "negative- and zero-sequence current-control "
                    "behaviour is not defined by the source input."
                ),
                reference_code=source.code,
            )
            continue

        assert source.current_contribution_ka is not None

        total += source.current_contribution_ka * source.contribution_factor

        _append_warning(
            warnings,
            code=(FaultWarningCode.CURRENT_INJECTION_APPROXIMATION),
            severity=(FaultWarningSeverity.WARNING),
            message=(
                "Current-injection contribution was added "
                "arithmetically to the three-phase initial "
                "symmetrical fault current. Verify converter "
                "fault-current controls for final design."
            ),
            reference_code=source.code,
        )

    return total


def _voltage_source_weight(
    source: FaultSourceInput,
) -> Decimal:
    impedance = source.positive_sequence_impedance

    if impedance is None:
        return Decimal("0")

    magnitude = (
        impedance.resistance_ohm * impedance.resistance_ohm
        + impedance.reactance_ohm * impedance.reactance_ohm
    ).sqrt()

    if magnitude == Decimal("0"):
        return Decimal("0")

    return source.contribution_factor / magnitude


def _source_contributions(
    study: ShortCircuitStudyInput,
    passive_current_ka: Decimal,
    current_injection_total_ka: Decimal,
    positive_reduction: SequenceNetworkReduction,
    peak_factor: Decimal | None,
    warnings: list[FaultEngineeringWarning],
) -> tuple[FaultSourceContributionResult, ...]:
    reachable_voltage_sources = tuple(
        source
        for source in study.sources
        if (
            source.in_service
            and source.representation is SourceRepresentation.VOLTAGE_BEHIND_IMPEDANCE
            and source.code in positive_reduction.path_reference_codes
        )
    )

    weights = {source.code: _voltage_source_weight(source) for source in reachable_voltage_sources}

    total_weight = sum(
        weights.values(),
        Decimal("0"),
    )

    if passive_current_ka > Decimal("0") and len(reachable_voltage_sources) > 1:
        _append_warning(
            warnings,
            code=(FaultWarningCode.ENGINEERING_REVIEW_REQUIRED),
            severity=(FaultWarningSeverity.WARNING),
            message=(
                "Total passive-network short-circuit current "
                "is calculated from the reduced network. "
                "Individual voltage-source contributions are "
                "allocated by positive-sequence source "
                "admittance and require independent review "
                "for meshed multi-source systems."
            ),
            reference_code=("SOURCE_CONTRIBUTION_ALLOCATION"),
        )

    contributions: list[FaultSourceContributionResult] = []

    for source in study.sources:
        if not source.in_service:
            contributions.append(
                FaultSourceContributionResult(
                    source_code=source.code,
                    source_type=source.source_type,
                    representation=(source.representation),
                    included=False,
                    initial_symmetrical_current_ka=(Decimal("0")),
                    peak_current_ka=None,
                    exclusion_reason=("Source is out of service."),
                )
            )
            continue

        if source.representation is SourceRepresentation.CURRENT_INJECTION:
            if study.fault.fault_type is not FaultType.THREE_PHASE:
                contributions.append(
                    FaultSourceContributionResult(
                        source_code=source.code,
                        source_type=source.source_type,
                        representation=(source.representation),
                        included=False,
                        initial_symmetrical_current_ka=(Decimal("0")),
                        peak_current_ka=None,
                        exclusion_reason=(
                            "Unbalanced sequence behaviour "
                            "is not defined for this "
                            "current-injection source."
                        ),
                    )
                )
                continue

            assert source.current_contribution_ka is not None

            source_current = _round_current(
                source.current_contribution_ka * source.contribution_factor
            )

            contributions.append(
                FaultSourceContributionResult(
                    source_code=source.code,
                    source_type=source.source_type,
                    representation=(source.representation),
                    included=True,
                    initial_symmetrical_current_ka=(source_current),
                    peak_current_ka=None,
                )
            )
            continue

        if source.code not in positive_reduction.path_reference_codes:
            contributions.append(
                FaultSourceContributionResult(
                    source_code=source.code,
                    source_type=source.source_type,
                    representation=(source.representation),
                    included=False,
                    initial_symmetrical_current_ka=(Decimal("0")),
                    peak_current_ka=None,
                    exclusion_reason=(
                        "No positive-sequence path exists from this source to the fault bus."
                    ),
                )
            )
            continue

        if passive_current_ka <= Decimal("0") or total_weight <= Decimal("0"):
            contributions.append(
                FaultSourceContributionResult(
                    source_code=source.code,
                    source_type=source.source_type,
                    representation=(source.representation),
                    included=False,
                    initial_symmetrical_current_ka=(Decimal("0")),
                    peak_current_ka=None,
                    exclusion_reason=(
                        "Source has no calculated passive fault-current contribution."
                    ),
                )
            )
            continue

        source_current = _round_current(passive_current_ka * weights[source.code] / total_weight)

        if source_current <= Decimal("0"):
            contributions.append(
                FaultSourceContributionResult(
                    source_code=source.code,
                    source_type=source.source_type,
                    representation=(source.representation),
                    included=False,
                    initial_symmetrical_current_ka=(Decimal("0")),
                    peak_current_ka=None,
                    exclusion_reason=("Calculated contribution is below the reporting quantum."),
                )
            )
            continue

        source_peak = None

        if peak_factor is not None:
            source_peak = _round_current(source_current * peak_factor)

        contributions.append(
            FaultSourceContributionResult(
                source_code=source.code,
                source_type=source.source_type,
                representation=(source.representation),
                included=True,
                initial_symmetrical_current_ka=(source_current),
                peak_current_ka=source_peak,
            )
        )

    if current_injection_total_ka == Decimal("0") and passive_current_ka == Decimal("0"):
        return tuple(contribution for contribution in contributions if not contribution.included)

    reported_total_current = _round_current(passive_current_ka + current_injection_total_ka)

    included_indexes = tuple(
        index for index, contribution in enumerate(contributions) if contribution.included
    )

    reported_contribution_total = sum(
        (contributions[index].initial_symmetrical_current_ka for index in included_indexes),
        Decimal("0"),
    )

    rounding_residual = reported_total_current - reported_contribution_total

    if rounding_residual != Decimal("0") and included_indexes:
        adjustment_index = included_indexes[-1]
        contribution = contributions[adjustment_index]

        adjusted_current = contribution.initial_symmetrical_current_ka + rounding_residual

        if adjusted_current <= Decimal("0"):
            raise ValueError(
                "source contribution rounding reconciliation produced a non-positive current"
            )

        adjusted_peak = contribution.peak_current_ka

        if adjusted_peak is not None and peak_factor is not None:
            adjusted_peak = _round_current(adjusted_current * peak_factor)

        contributions[adjustment_index] = replace(
            contribution,
            initial_symmetrical_current_ka=(adjusted_current),
            peak_current_ka=adjusted_peak,
        )

    return tuple(contributions)


def _calculate_peak(
    study: ShortCircuitStudyInput,
    passive: _PassiveFaultCalculation,
    current_injection_total_ka: Decimal,
    warnings: list[FaultEngineeringWarning],
) -> tuple[
    Decimal | None,
    Decimal | None,
    Decimal | None,
    Decimal | None,
]:
    if study.fault.fault_type is not FaultType.THREE_PHASE:
        _append_warning(
            warnings,
            code=(FaultWarningCode.PEAK_CURRENT_NOT_EVALUATED),
            severity=(FaultWarningSeverity.WARNING),
            message=("Peak current is not yet evaluated for this unbalanced fault configuration."),
            reference_code=study.fault.bus_code,
        )
        return (
            None,
            None,
            None,
            None,
        )

    if current_injection_total_ka > Decimal("0"):
        _append_warning(
            warnings,
            code=(FaultWarningCode.PEAK_CURRENT_NOT_EVALUATED),
            severity=(FaultWarningSeverity.WARNING),
            message=(
                "Peak current was not evaluated because "
                "converter current-injection peak behaviour "
                "is not defined."
            ),
            reference_code=study.fault.bus_code,
        )
        return (
            None,
            None,
            None,
            None,
        )

    loop = passive.peak_loop_impedance

    if loop is None or passive.initial_current_ka <= Decimal("0"):
        return (
            None,
            None,
            None,
            None,
        )

    if loop.real == Decimal("0"):
        _append_warning(
            warnings,
            code=(FaultWarningCode.PEAK_CURRENT_NOT_EVALUATED),
            severity=(FaultWarningSeverity.WARNING),
            message=(
                "Peak current was not evaluated because "
                "the reduced fault-loop resistance is zero "
                "and a finite X/R ratio cannot be reported."
            ),
            reference_code=study.fault.bus_code,
        )
        return (
            None,
            None,
            None,
            None,
        )

    x_r_ratio = loop.imag / loop.real

    if loop.imag == Decimal("0"):
        kappa = Decimal("1.02")
    else:
        r_x_ratio = loop.real / loop.imag

        kappa = Decimal("1.02") + Decimal("0.98") * (-THREE * r_x_ratio).exp()

    if kappa > Decimal("2"):
        kappa = Decimal("2")

    peak_factor = kappa * TWO.sqrt()

    peak_current_ka = passive.initial_current_ka * peak_factor

    return (
        _round_current(peak_current_ka),
        _round_ratio(kappa),
        _round_ratio(x_r_ratio),
        peak_factor,
    )


def _standard_duty_warnings(
    study: ShortCircuitStudyInput,
    warnings: list[FaultEngineeringWarning],
) -> None:
    _append_warning(
        warnings,
        code=(FaultWarningCode.BREAKING_CURRENT_NOT_EVALUATED),
        severity=(FaultWarningSeverity.WARNING),
        message=(
            "Symmetrical breaking current requires "
            "source decay and breaker contact-separation "
            "data and is not inferred from Ik''."
        ),
        reference_code=study.fault.bus_code,
    )

    _append_warning(
        warnings,
        code=(FaultWarningCode.STEADY_STATE_CURRENT_NOT_EVALUATED),
        severity=(FaultWarningSeverity.WARNING),
        message=(
            "Steady-state short-circuit current requires "
            "machine and converter contribution behaviour "
            "that is not present in the study input."
        ),
        reference_code=study.fault.bus_code,
    )

    _append_warning(
        warnings,
        code=(FaultWarningCode.THERMAL_CURRENT_NOT_EVALUATED),
        severity=(FaultWarningSeverity.WARNING),
        message=(
            "Equivalent thermal short-circuit current "
            "requires the time-dependent current envelope "
            "and is not approximated from the initial "
            "symmetrical current."
        ),
        reference_code=study.fault.bus_code,
    )


def calculate_short_circuit(
    study: ShortCircuitStudyInput,
) -> ShortCircuitStudyResult:
    """
    Calculate an IEC 60909 short-circuit study.

    The calculation remains pure: no database, API, environment,
    manufacturer catalogue, or mutable global state is accessed.
    """

    if not isinstance(
        study,
        ShortCircuitStudyInput,
    ):
        raise TypeError("study must be a ShortCircuitStudyInput record")

    with localcontext() as context:
        context.prec = 50

        reductions = {
            sequence: reduce_sequence_network(
                study,
                sequence,
            )
            for sequence in _required_sequences(study.fault.fault_type)
        }

        sequence_results = tuple(
            _equivalent_sequence_result(reductions[sequence])
            for sequence in _required_sequences(study.fault.fault_type)
        )

        warnings: list[FaultEngineeringWarning] = []

        if (
            study.fault.fault_type
            in {
                FaultType.TWO_PHASE_TO_EARTH,
                FaultType.SINGLE_PHASE_TO_EARTH,
            }
            and not reductions[FaultSequence.ZERO].available
        ):
            _append_warning(
                warnings,
                code=(FaultWarningCode.ZERO_SEQUENCE_PATH_BLOCKED),
                severity=(FaultWarningSeverity.WARNING),
                message=(
                    "No complete zero-sequence source path exists to the earth-fault location."
                ),
                reference_code=study.fault.bus_code,
            )

        try:
            passive = _calculate_passive_fault(
                study,
                reductions,
            )
        except (
            ArithmeticError,
            ValueError,
            ZeroDivisionError,
        ) as exc:
            _append_warning(
                warnings,
                code=(FaultWarningCode.CALCULATION_FAILED),
                severity=(FaultWarningSeverity.ERROR),
                message=(f"Short-circuit calculation failed: {exc}"),
                reference_code=study.fault.bus_code,
            )

            excluded_sources = tuple(
                FaultSourceContributionResult(
                    source_code=source.code,
                    source_type=source.source_type,
                    representation=(source.representation),
                    included=False,
                    initial_symmetrical_current_ka=(Decimal("0")),
                    peak_current_ka=None,
                    exclusion_reason=("Calculation is indeterminate."),
                )
                for source in study.sources
            )

            fault_bus = _fault_bus(study)

            return ShortCircuitStudyResult(
                study_code=study.code,
                study_name=study.name,
                calculation_case=(study.calculation_case),
                fault_bus_code=(study.fault.bus_code),
                fault_type=(study.fault.fault_type),
                nominal_voltage_v=(fault_bus.nominal_voltage_v),
                frequency_hz=study.frequency_hz,
                status=(FaultResultStatus.INDETERMINATE),
                initial_symmetrical_short_circuit_current_ka=None,
                peak_short_circuit_current_ka=None,
                symmetrical_breaking_current_ka=None,
                steady_state_short_circuit_current_ka=None,
                thermal_equivalent_short_circuit_current_ka=None,
                earth_fault_current_ka=None,
                kappa_factor=None,
                x_r_ratio=None,
                clearing_time_s=None,
                sequence_results=(sequence_results),
                source_contributions=(excluded_sources),
                warnings=tuple(warnings),
                standard_reference=(study.standard_reference),
                earth_current_reference=(study.earth_current_reference),
                operating_state_code=(study.operating_state_code),
            )

        current_injection_total = _current_injection_total(
            study,
            warnings,
        )

        initial_current = passive.initial_current_ka + current_injection_total

        if initial_current == Decimal("0"):
            _append_warning(
                warnings,
                code=(FaultWarningCode.NO_FAULT_CURRENT_PATH),
                severity=(FaultWarningSeverity.WARNING),
                message=(
                    "No contributing fault-current path exists for the selected operating state."
                ),
                reference_code=study.fault.bus_code,
            )

        (
            peak_current,
            kappa,
            x_r_ratio,
            peak_factor,
        ) = _calculate_peak(
            study,
            passive,
            current_injection_total,
            warnings,
        )

        _standard_duty_warnings(
            study,
            warnings,
        )

        positive_reduction = reductions[FaultSequence.POSITIVE]

        source_contributions = _source_contributions(
            study,
            passive.initial_current_ka,
            current_injection_total,
            positive_reduction,
            peak_factor,
            warnings,
        )

        status = FaultResultStatus.WARNING if warnings else FaultResultStatus.CALCULATED

        fault_bus = _fault_bus(study)

        earth_fault_current = passive.earth_fault_current_ka

        if earth_fault_current is not None:
            earth_fault_current = _round_current(earth_fault_current)

        return ShortCircuitStudyResult(
            study_code=study.code,
            study_name=study.name,
            calculation_case=(study.calculation_case),
            fault_bus_code=(study.fault.bus_code),
            fault_type=(study.fault.fault_type),
            nominal_voltage_v=(fault_bus.nominal_voltage_v),
            frequency_hz=study.frequency_hz,
            status=status,
            initial_symmetrical_short_circuit_current_ka=(_round_current(initial_current)),
            peak_short_circuit_current_ka=(peak_current),
            symmetrical_breaking_current_ka=None,
            steady_state_short_circuit_current_ka=None,
            thermal_equivalent_short_circuit_current_ka=None,
            earth_fault_current_ka=(earth_fault_current),
            kappa_factor=kappa,
            x_r_ratio=x_r_ratio,
            clearing_time_s=None,
            sequence_results=(sequence_results),
            source_contributions=(source_contributions),
            warnings=tuple(warnings),
            standard_reference=(study.standard_reference),
            earth_current_reference=(study.earth_current_reference),
            operating_state_code=(study.operating_state_code),
        )


__all__ = [
    "calculate_short_circuit",
]
