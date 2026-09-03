"""
Unit tests for the IEC 60909 short-circuit and earth-fault engine.
KESE-S2-M15
"""

from decimal import Decimal
from typing import Any, cast

import pytest

from app.domain.electrical.fault.fault_engine import calculate_short_circuit
from app.domain.electrical.fault.fault_models import (
    FaultBusInput,
    FaultLocationInput,
    FaultSourceInput,
    FaultSourceType,
    FaultType,
    NeutralEarthingMode,
    SequenceImpedanceInput,
    ShortCircuitCase,
    ShortCircuitStudyInput,
    SourceRepresentation,
)
from app.domain.electrical.fault.fault_results import (
    FaultResultStatus,
    FaultSequence,
    FaultWarningCode,
)


def make_impedance(
    resistance_ohm: str,
    reactance_ohm: str,
) -> SequenceImpedanceInput:
    return SequenceImpedanceInput(
        resistance_ohm=Decimal(resistance_ohm),
        reactance_ohm=Decimal(reactance_ohm),
    )


def make_bus(
    *,
    earthing_mode: NeutralEarthingMode = NeutralEarthingMode.SOLIDLY_EARTHED,
    neutral_resistance_ohm: Decimal = Decimal("0"),
    neutral_reactance_ohm: Decimal = Decimal("0"),
) -> FaultBusInput:
    return FaultBusInput(
        code="BUS-01",
        name="11 kV Main Bus",
        nominal_voltage_v=Decimal("11000"),
        voltage_factor_max=Decimal("1.10"),
        voltage_factor_min=Decimal("0.95"),
        neutral_earthing_mode=earthing_mode,
        neutral_resistance_ohm=neutral_resistance_ohm,
        neutral_reactance_ohm=neutral_reactance_ohm,
    )


def make_voltage_source(
    code: str = "GRID-01",
    *,
    positive: SequenceImpedanceInput | None = None,
    negative: SequenceImpedanceInput | None = None,
    zero: SequenceImpedanceInput | None = None,
    in_service: bool = True,
) -> FaultSourceInput:
    return FaultSourceInput(
        code=code,
        name=code,
        bus_code="BUS-01",
        source_type=FaultSourceType.UTILITY_GRID,
        representation=SourceRepresentation.VOLTAGE_BEHIND_IMPEDANCE,
        positive_sequence_impedance=positive or make_impedance("0.10", "0.20"),
        negative_sequence_impedance=negative or make_impedance("0.10", "0.20"),
        zero_sequence_impedance=zero or make_impedance("0.20", "0.40"),
        current_contribution_ka=None,
        in_service=in_service,
    )


def make_current_source(
    *,
    current_ka: Decimal = Decimal("1.25"),
) -> FaultSourceInput:
    return FaultSourceInput(
        code="PV-01",
        name="PV-01",
        bus_code="BUS-01",
        source_type=FaultSourceType.INVERTER_BASED_RESOURCE,
        representation=SourceRepresentation.CURRENT_INJECTION,
        positive_sequence_impedance=None,
        negative_sequence_impedance=None,
        zero_sequence_impedance=None,
        current_contribution_ka=current_ka,
    )


def make_study(
    *,
    fault_type: FaultType = FaultType.THREE_PHASE,
    calculation_case: ShortCircuitCase = ShortCircuitCase.MAXIMUM,
    bus: FaultBusInput | None = None,
    sources: tuple[FaultSourceInput, ...] | None = None,
    fault_resistance_ohm: Decimal = Decimal("0"),
    fault_reactance_ohm: Decimal = Decimal("0"),
) -> ShortCircuitStudyInput:
    return ShortCircuitStudyInput(
        code="SC-ENGINE-01",
        name="Fault Engine Test",
        calculation_case=calculation_case,
        fault=FaultLocationInput(
            bus_code="BUS-01",
            fault_type=fault_type,
            fault_resistance_ohm=fault_resistance_ohm,
            fault_reactance_ohm=fault_reactance_ohm,
        ),
        buses=(bus or make_bus(),),
        sources=sources or (make_voltage_source(),),
    )


@pytest.mark.unit
def test_engine_rejects_invalid_study_type() -> None:
    with pytest.raises(
        TypeError,
        match="study must be a ShortCircuitStudyInput",
    ):
        calculate_short_circuit(cast(Any, "invalid"))


@pytest.mark.unit
def test_three_phase_fault_calculates_initial_and_peak_current() -> None:
    result = calculate_short_circuit(make_study())

    assert result.status is FaultResultStatus.WARNING
    assert result.initial_symmetrical_short_circuit_current_ka == Decimal("31.242065659")
    assert result.peak_short_circuit_current_ka == Decimal("54.727990417")
    assert result.kappa_factor == Decimal("1.238668")
    assert result.x_r_ratio == Decimal("2.000000")
    assert result.earth_fault_current_ka is None

    assert len(result.sequence_results) == 1
    assert result.sequence_results[0].sequence is FaultSequence.POSITIVE
    assert result.sequence_results[0].available is True


@pytest.mark.unit
def test_minimum_case_uses_minimum_voltage_factor() -> None:
    result = calculate_short_circuit(
        make_study(
            calculation_case=ShortCircuitCase.MINIMUM,
        )
    )

    assert result.initial_symmetrical_short_circuit_current_ka == Decimal("26.981783979")


@pytest.mark.unit
def test_three_phase_fault_impedance_reduces_fault_current() -> None:
    result = calculate_short_circuit(
        make_study(
            fault_resistance_ohm=Decimal("0.05"),
            fault_reactance_ohm=Decimal("0.10"),
        )
    )

    assert result.initial_symmetrical_short_circuit_current_ka == Decimal("20.828043773")


@pytest.mark.unit
def test_two_phase_fault_uses_positive_and_negative_sequences() -> None:
    result = calculate_short_circuit(
        make_study(
            fault_type=FaultType.TWO_PHASE,
        )
    )

    assert result.initial_symmetrical_short_circuit_current_ka == Decimal("27.056422528")
    assert result.earth_fault_current_ka is None

    assert {item.sequence for item in result.sequence_results} == {
        FaultSequence.POSITIVE,
        FaultSequence.NEGATIVE,
    }

    warning_codes = {warning.code for warning in result.warnings}

    assert FaultWarningCode.PEAK_CURRENT_NOT_EVALUATED in warning_codes


@pytest.mark.unit
def test_single_phase_to_earth_fault_uses_all_sequences() -> None:
    result = calculate_short_circuit(
        make_study(
            fault_type=FaultType.SINGLE_PHASE_TO_EARTH,
        )
    )

    assert result.initial_symmetrical_short_circuit_current_ka == Decimal("23.431549245")
    assert result.earth_fault_current_ka == Decimal("23.431549245")

    assert {item.sequence for item in result.sequence_results} == {
        FaultSequence.POSITIVE,
        FaultSequence.NEGATIVE,
        FaultSequence.ZERO,
    }


@pytest.mark.unit
def test_two_phase_to_earth_fault_calculates_phase_and_earth_current() -> None:
    result = calculate_short_circuit(
        make_study(
            fault_type=FaultType.TWO_PHASE_TO_EARTH,
        )
    )

    assert result.initial_symmetrical_short_circuit_current_ka == Decimal("28.633826150")
    assert result.earth_fault_current_ka == Decimal("18.745239396")


@pytest.mark.unit
def test_isolated_neutral_blocks_single_phase_earth_fault_current() -> None:
    isolated_bus = make_bus(
        earthing_mode=NeutralEarthingMode.ISOLATED,
    )

    result = calculate_short_circuit(
        make_study(
            fault_type=FaultType.SINGLE_PHASE_TO_EARTH,
            bus=isolated_bus,
        )
    )

    assert result.initial_symmetrical_short_circuit_current_ka == Decimal("0E-9")
    assert result.earth_fault_current_ka == Decimal("0E-9")

    warning_codes = {warning.code for warning in result.warnings}

    assert FaultWarningCode.ZERO_SEQUENCE_PATH_BLOCKED in warning_codes
    assert FaultWarningCode.NO_FAULT_CURRENT_PATH in warning_codes

    assert all(not contribution.included for contribution in result.source_contributions)


@pytest.mark.unit
def test_current_injection_source_contributes_to_three_phase_fault() -> None:
    result = calculate_short_circuit(
        make_study(
            sources=(
                make_current_source(
                    current_ka=Decimal("1.25"),
                ),
            ),
        )
    )

    assert result.initial_symmetrical_short_circuit_current_ka == Decimal("1.250000000")
    assert result.peak_short_circuit_current_ka is None
    assert result.kappa_factor is None
    assert result.x_r_ratio is None

    assert len(result.source_contributions) == 1
    assert result.source_contributions[0].included is True
    assert result.source_contributions[0].initial_symmetrical_current_ka == Decimal("1.250000000")

    warning_codes = {warning.code for warning in result.warnings}

    assert FaultWarningCode.CURRENT_INJECTION_APPROXIMATION in warning_codes
    assert FaultWarningCode.PEAK_CURRENT_NOT_EVALUATED in warning_codes


@pytest.mark.unit
def test_current_injection_is_excluded_from_unbalanced_fault() -> None:
    voltage_source = make_voltage_source()
    current_source = make_current_source()

    result = calculate_short_circuit(
        make_study(
            fault_type=FaultType.TWO_PHASE,
            sources=(
                voltage_source,
                current_source,
            ),
        )
    )

    pv_contribution = next(
        contribution
        for contribution in result.source_contributions
        if contribution.source_code == "PV-01"
    )

    assert pv_contribution.included is False
    assert pv_contribution.initial_symmetrical_current_ka == Decimal("0")

    assert any(
        warning.code is FaultWarningCode.CURRENT_INJECTION_APPROXIMATION
        and warning.reference_code == "PV-01"
        for warning in result.warnings
    )


@pytest.mark.unit
def test_parallel_voltage_sources_double_fault_strength() -> None:
    result = calculate_short_circuit(
        make_study(
            sources=(
                make_voltage_source("GRID-01"),
                make_voltage_source("GRID-02"),
            ),
        )
    )

    assert result.initial_symmetrical_short_circuit_current_ka == Decimal("62.484131319")

    included = tuple(
        contribution for contribution in result.source_contributions if contribution.included
    )

    assert len(included) == 2

    assert {contribution.initial_symmetrical_current_ka for contribution in included} == {
        Decimal("31.242065659"),
        Decimal("31.242065660"),
    }

    assert any(
        warning.code is FaultWarningCode.ENGINEERING_REVIEW_REQUIRED for warning in result.warnings
    )


@pytest.mark.unit
def test_out_of_service_source_is_explicitly_excluded() -> None:
    active_source = make_voltage_source("GRID-01")
    inactive_source = make_voltage_source(
        "GRID-02",
        in_service=False,
    )

    result = calculate_short_circuit(
        make_study(
            sources=(
                active_source,
                inactive_source,
            ),
        )
    )

    excluded = next(
        contribution
        for contribution in result.source_contributions
        if contribution.source_code == "GRID-02"
    )

    assert excluded.included is False
    assert excluded.initial_symmetrical_current_ka == Decimal("0")
    assert excluded.exclusion_reason == "Source is out of service."


@pytest.mark.unit
def test_unavailable_engineering_duties_are_never_fabricated() -> None:
    result = calculate_short_circuit(make_study())

    assert result.symmetrical_breaking_current_ka is None
    assert result.steady_state_short_circuit_current_ka is None
    assert result.thermal_equivalent_short_circuit_current_ka is None

    warning_codes = {warning.code for warning in result.warnings}

    assert {
        FaultWarningCode.BREAKING_CURRENT_NOT_EVALUATED,
        FaultWarningCode.STEADY_STATE_CURRENT_NOT_EVALUATED,
        FaultWarningCode.THERMAL_CURRENT_NOT_EVALUATED,
    }.issubset(warning_codes)


@pytest.mark.unit
def test_engine_is_deterministic_for_identical_input() -> None:
    study = make_study(
        fault_type=FaultType.SINGLE_PHASE_TO_EARTH,
    )

    first = calculate_short_circuit(study)
    second = calculate_short_circuit(study)

    assert first == second
