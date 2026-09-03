"""
Controlled analytical golden-reference cases for KESE-S2-M15.

Expected values are fixed from independent symmetrical-component
hand calculations. These are engineering regression references and
are not claimed to reproduce official IEC publication worked examples.
"""

from decimal import Decimal

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
    FaultSequence,
    FaultWarningCode,
)

pytestmark = pytest.mark.golden


def impedance(
    resistance_ohm: str,
    reactance_ohm: str,
) -> SequenceImpedanceInput:
    return SequenceImpedanceInput(
        resistance_ohm=Decimal(resistance_ohm),
        reactance_ohm=Decimal(reactance_ohm),
    )


def reference_bus(
    *,
    earthing_mode: NeutralEarthingMode = NeutralEarthingMode.SOLIDLY_EARTHED,
    neutral_resistance_ohm: Decimal = Decimal("0"),
    neutral_reactance_ohm: Decimal = Decimal("0"),
) -> FaultBusInput:
    return FaultBusInput(
        code="BUS-11KV",
        name="11 kV Reference Bus",
        nominal_voltage_v=Decimal("11000"),
        voltage_factor_max=Decimal("1.10"),
        voltage_factor_min=Decimal("0.95"),
        neutral_earthing_mode=earthing_mode,
        neutral_resistance_ohm=neutral_resistance_ohm,
        neutral_reactance_ohm=neutral_reactance_ohm,
    )


def reference_source() -> FaultSourceInput:
    return FaultSourceInput(
        code="GRID-REF",
        name="Reference Thevenin Source",
        bus_code="BUS-11KV",
        source_type=FaultSourceType.UTILITY_GRID,
        representation=SourceRepresentation.VOLTAGE_BEHIND_IMPEDANCE,
        positive_sequence_impedance=impedance("0.10", "0.20"),
        negative_sequence_impedance=impedance("0.10", "0.20"),
        zero_sequence_impedance=impedance("0.20", "0.40"),
        current_contribution_ka=None,
    )


def reference_study(
    fault_type: FaultType,
    *,
    calculation_case: ShortCircuitCase = ShortCircuitCase.MAXIMUM,
    bus: FaultBusInput | None = None,
) -> ShortCircuitStudyInput:
    return ShortCircuitStudyInput(
        code=f"GOLDEN-{fault_type.value}",
        name=f"Golden {fault_type.value} Reference",
        calculation_case=calculation_case,
        fault=FaultLocationInput(
            bus_code="BUS-11KV",
            fault_type=fault_type,
        ),
        buses=(bus or reference_bus(),),
        sources=(reference_source(),),
    )


def test_golden_three_phase_maximum_fault() -> None:
    """
    Un = 11 kV
    cmax = 1.10
    Z1 = 0.10 + j0.20 ohm

    Ik'' reference = 31.242065659 kA.
    """

    result = calculate_short_circuit(reference_study(FaultType.THREE_PHASE))

    assert result.initial_symmetrical_short_circuit_current_ka == Decimal("31.242065659")

    positive = result.sequence_results[0]

    assert positive.sequence is FaultSequence.POSITIVE
    assert positive.resistance_ohm == Decimal("0.100000000")
    assert positive.reactance_ohm == Decimal("0.200000000")


def test_golden_three_phase_minimum_fault() -> None:
    """
    cmin = 0.95 with the same Z1.

    Ik'' reference = 26.981783979 kA.
    """

    result = calculate_short_circuit(
        reference_study(
            FaultType.THREE_PHASE,
            calculation_case=ShortCircuitCase.MINIMUM,
        )
    )

    assert result.initial_symmetrical_short_circuit_current_ka == Decimal("26.981783979")


def test_golden_three_phase_peak_current() -> None:
    """
    R/X = 0.5
    X/R = 2

    kappa reference = 1.238668
    ip reference = 54.727990417 kA.
    """

    result = calculate_short_circuit(reference_study(FaultType.THREE_PHASE))

    assert result.x_r_ratio == Decimal("2.000000")
    assert result.kappa_factor == Decimal("1.238668")

    assert result.peak_short_circuit_current_ka == Decimal("54.727990417")


def test_golden_two_phase_fault() -> None:
    """
    Z1 = Z2 = 0.10 + j0.20 ohm.

    ILL reference = 27.056422528 kA.
    """

    result = calculate_short_circuit(reference_study(FaultType.TWO_PHASE))

    assert result.initial_symmetrical_short_circuit_current_ka == Decimal("27.056422528")

    assert {item.sequence for item in result.sequence_results} == {
        FaultSequence.POSITIVE,
        FaultSequence.NEGATIVE,
    }


def test_golden_single_phase_to_earth_fault() -> None:
    """
    Z1 = 0.10 + j0.20 ohm
    Z2 = 0.10 + j0.20 ohm
    Z0 = 0.20 + j0.40 ohm

    ILG reference = 23.431549245 kA.
    """

    result = calculate_short_circuit(reference_study(FaultType.SINGLE_PHASE_TO_EARTH))

    assert result.initial_symmetrical_short_circuit_current_ka == Decimal("23.431549245")
    assert result.earth_fault_current_ka == Decimal("23.431549245")

    assert {item.sequence for item in result.sequence_results} == {
        FaultSequence.POSITIVE,
        FaultSequence.NEGATIVE,
        FaultSequence.ZERO,
    }


def test_golden_two_phase_to_earth_fault() -> None:
    """
    Symmetrical-component reference:

    Maximum phase current = 28.633826150 kA
    Residual earth current = 18.745239396 kA.
    """

    result = calculate_short_circuit(reference_study(FaultType.TWO_PHASE_TO_EARTH))

    assert result.initial_symmetrical_short_circuit_current_ka == Decimal("28.633826150")
    assert result.earth_fault_current_ka == Decimal("18.745239396")


def test_golden_resistance_earthed_single_phase_fault() -> None:
    """
    Neutral resistance Rn = 1.0 ohm.

    Zero-sequence source path:
        Z0,total = (0.20 + 3*1.0) + j0.40
                 = 3.20 + j0.40 ohm

    Complete SLG loop:
        Z1 + Z2 + Z0,total
        = 3.40 + j0.80 ohm

    ILG reference = 6.000204915 kA.
    """

    bus = reference_bus(
        earthing_mode=NeutralEarthingMode.RESISTANCE_EARTHED,
        neutral_resistance_ohm=Decimal("1"),
    )

    result = calculate_short_circuit(
        reference_study(
            FaultType.SINGLE_PHASE_TO_EARTH,
            bus=bus,
        )
    )

    assert result.initial_symmetrical_short_circuit_current_ka == Decimal("6.000204915")
    assert result.earth_fault_current_ka == Decimal("6.000204915")

    zero_result = next(
        item for item in result.sequence_results if item.sequence is FaultSequence.ZERO
    )

    assert zero_result.available is True
    assert zero_result.resistance_ohm == Decimal("3.200000000")
    assert zero_result.reactance_ohm == Decimal("0.400000000")


def test_golden_isolated_neutral_blocks_zero_sequence() -> None:
    """
    Isolated neutral provides no complete zero-sequence return path.

    Expected earth-fault current = 0 kA.
    """

    bus = reference_bus(
        earthing_mode=NeutralEarthingMode.ISOLATED,
    )

    result = calculate_short_circuit(
        reference_study(
            FaultType.SINGLE_PHASE_TO_EARTH,
            bus=bus,
        )
    )

    assert result.initial_symmetrical_short_circuit_current_ka == Decimal("0E-9")
    assert result.earth_fault_current_ka == Decimal("0E-9")

    zero_result = next(
        item for item in result.sequence_results if item.sequence is FaultSequence.ZERO
    )

    assert zero_result.available is False

    warning_codes = {warning.code for warning in result.warnings}

    assert FaultWarningCode.ZERO_SEQUENCE_PATH_BLOCKED in warning_codes
    assert FaultWarningCode.NO_FAULT_CURRENT_PATH in warning_codes
