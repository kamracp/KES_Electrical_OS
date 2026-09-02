"""
Unit tests for symmetrical-sequence fault-network reduction.
KESE-S2-M15
"""

from dataclasses import FrozenInstanceError
from decimal import Decimal
from typing import Any, cast

import pytest

from app.domain.electrical.fault.fault_models import (
    FaultBranchInput,
    FaultBranchType,
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
from app.domain.electrical.fault.fault_network import (
    SequenceNetworkReduction,
    reduce_sequence_network,
)
from app.domain.electrical.fault.fault_results import FaultSequence

TOLERANCE = Decimal("0.000000000001")


def assert_decimal_close(
    actual: Decimal | None,
    expected: Decimal,
) -> None:
    assert actual is not None
    assert abs(actual - expected) <= TOLERANCE


def make_impedance(
    resistance_ohm: str = "0.10",
    reactance_ohm: str = "0.20",
) -> SequenceImpedanceInput:
    return SequenceImpedanceInput(
        resistance_ohm=Decimal(resistance_ohm),
        reactance_ohm=Decimal(reactance_ohm),
    )


def make_bus(
    code: str,
    *,
    earthing_mode: NeutralEarthingMode = NeutralEarthingMode.SOLIDLY_EARTHED,
    neutral_resistance_ohm: Decimal = Decimal("0"),
    neutral_reactance_ohm: Decimal = Decimal("0"),
) -> FaultBusInput:
    return FaultBusInput(
        code=code,
        name=code,
        nominal_voltage_v=Decimal("11000"),
        voltage_factor_max=Decimal("1.10"),
        voltage_factor_min=Decimal("0.95"),
        neutral_earthing_mode=earthing_mode,
        neutral_resistance_ohm=neutral_resistance_ohm,
        neutral_reactance_ohm=neutral_reactance_ohm,
    )


def make_voltage_source(
    code: str,
    bus_code: str,
    *,
    positive: SequenceImpedanceInput | None = None,
    negative: SequenceImpedanceInput | None = None,
    zero: SequenceImpedanceInput | None = None,
    contribution_factor: Decimal = Decimal("1"),
) -> FaultSourceInput:
    return FaultSourceInput(
        code=code,
        name=code,
        bus_code=bus_code,
        source_type=FaultSourceType.UTILITY_GRID,
        representation=SourceRepresentation.VOLTAGE_BEHIND_IMPEDANCE,
        positive_sequence_impedance=positive or make_impedance(),
        negative_sequence_impedance=negative or make_impedance("0.12", "0.22"),
        zero_sequence_impedance=zero or make_impedance("0.20", "0.40"),
        current_contribution_ka=None,
        contribution_factor=contribution_factor,
    )


def make_current_source(
    code: str,
    bus_code: str,
) -> FaultSourceInput:
    return FaultSourceInput(
        code=code,
        name=code,
        bus_code=bus_code,
        source_type=FaultSourceType.INVERTER_BASED_RESOURCE,
        representation=SourceRepresentation.CURRENT_INJECTION,
        positive_sequence_impedance=None,
        negative_sequence_impedance=None,
        zero_sequence_impedance=None,
        current_contribution_ka=Decimal("1.25"),
    )


def make_branch(
    code: str,
    from_bus_code: str,
    to_bus_code: str,
    *,
    positive: SequenceImpedanceInput | None = None,
    negative: SequenceImpedanceInput | None = None,
    zero: SequenceImpedanceInput | None = None,
    parallel_circuits: int = 1,
) -> FaultBranchInput:
    return FaultBranchInput(
        code=code,
        name=code,
        from_bus_code=from_bus_code,
        to_bus_code=to_bus_code,
        branch_type=FaultBranchType.CABLE,
        positive_sequence_impedance=positive or make_impedance("0.05", "0.10"),
        negative_sequence_impedance=negative or make_impedance("0.06", "0.11"),
        zero_sequence_impedance=zero or make_impedance("0.15", "0.30"),
        parallel_circuits=parallel_circuits,
    )


def make_study(
    *,
    fault_bus_code: str = "BUS-02",
    fault_type: FaultType = FaultType.THREE_PHASE,
    buses: tuple[FaultBusInput, ...] | None = None,
    sources: tuple[FaultSourceInput, ...] | None = None,
    branches: tuple[FaultBranchInput, ...] | None = None,
) -> ShortCircuitStudyInput:
    selected_buses = buses or (
        make_bus("BUS-01"),
        make_bus("BUS-02"),
    )
    selected_sources = sources or (make_voltage_source("GRID-01", "BUS-01"),)
    selected_branches = (
        branches if branches is not None else (make_branch("BR-01-02", "BUS-01", "BUS-02"),)
    )

    return ShortCircuitStudyInput(
        code="SC-NET-01",
        name="Fault Network Reduction",
        calculation_case=ShortCircuitCase.MAXIMUM,
        fault=FaultLocationInput(
            bus_code=fault_bus_code,
            fault_type=fault_type,
        ),
        buses=selected_buses,
        sources=selected_sources,
        branches=selected_branches,
    )


@pytest.mark.unit
def test_reduction_record_is_immutable() -> None:
    result = reduce_sequence_network(
        make_study(),
        FaultSequence.POSITIVE,
    )

    with pytest.raises(FrozenInstanceError):
        cast(Any, result).available = False


@pytest.mark.unit
def test_reducer_rejects_invalid_input_types() -> None:
    with pytest.raises(
        TypeError,
        match="study must be a ShortCircuitStudyInput",
    ):
        reduce_sequence_network(
            cast(Any, "invalid"),
            FaultSequence.POSITIVE,
        )

    with pytest.raises(
        TypeError,
        match="sequence must be a FaultSequence",
    ):
        reduce_sequence_network(
            make_study(),
            cast(Any, "POSITIVE"),
        )


@pytest.mark.unit
def test_source_at_fault_bus_returns_source_impedance() -> None:
    bus = make_bus("BUS-01")
    source = make_voltage_source(
        "GRID-01",
        "BUS-01",
        positive=make_impedance("0.10", "0.20"),
    )
    study = make_study(
        fault_bus_code="BUS-01",
        buses=(bus,),
        sources=(source,),
        branches=(),
    )

    result = reduce_sequence_network(
        study,
        FaultSequence.POSITIVE,
    )

    assert result.available is True
    assert_decimal_close(
        result.resistance_ohm,
        Decimal("0.10"),
    )
    assert_decimal_close(
        result.reactance_ohm,
        Decimal("0.20"),
    )
    assert result.connected_bus_codes == ("BUS-01",)
    assert result.path_reference_codes == ("GRID-01",)
    assert result.blocking_reference_codes == ()


@pytest.mark.unit
def test_radial_network_adds_source_and_branch_impedance() -> None:
    result = reduce_sequence_network(
        make_study(),
        FaultSequence.POSITIVE,
    )

    assert result.available is True
    assert_decimal_close(
        result.resistance_ohm,
        Decimal("0.15"),
    )
    assert_decimal_close(
        result.reactance_ohm,
        Decimal("0.30"),
    )
    assert result.connected_bus_codes == (
        "BUS-01",
        "BUS-02",
    )
    assert result.path_reference_codes == (
        "BR-01-02",
        "GRID-01",
    )


@pytest.mark.unit
def test_parallel_sources_reduce_equivalent_impedance() -> None:
    bus = make_bus("BUS-01")
    sources = (
        make_voltage_source(
            "GRID-01",
            "BUS-01",
            positive=make_impedance("0.10", "0.20"),
        ),
        make_voltage_source(
            "GEN-01",
            "BUS-01",
            positive=make_impedance("0.10", "0.20"),
        ),
    )
    study = make_study(
        fault_bus_code="BUS-01",
        buses=(bus,),
        sources=sources,
        branches=(),
    )

    result = reduce_sequence_network(
        study,
        FaultSequence.POSITIVE,
    )

    assert_decimal_close(
        result.resistance_ohm,
        Decimal("0.05"),
    )
    assert_decimal_close(
        result.reactance_ohm,
        Decimal("0.10"),
    )
    assert result.path_reference_codes == (
        "GEN-01",
        "GRID-01",
    )


@pytest.mark.unit
def test_parallel_branch_circuits_reduce_branch_impedance() -> None:
    branch = make_branch(
        "BR-01-02",
        "BUS-01",
        "BUS-02",
        positive=make_impedance("0.10", "0.20"),
        parallel_circuits=2,
    )
    study = make_study(
        branches=(branch,),
    )

    result = reduce_sequence_network(
        study,
        FaultSequence.POSITIVE,
    )

    assert_decimal_close(
        result.resistance_ohm,
        Decimal("0.15"),
    )
    assert_decimal_close(
        result.reactance_ohm,
        Decimal("0.30"),
    )


@pytest.mark.unit
def test_disconnected_source_returns_unavailable_network() -> None:
    study = make_study(
        branches=(),
    )

    result = reduce_sequence_network(
        study,
        FaultSequence.POSITIVE,
    )

    assert result.available is False
    assert result.resistance_ohm is None
    assert result.reactance_ohm is None
    assert result.connected_bus_codes == ("BUS-02",)
    assert result.path_reference_codes == ()
    assert result.blocking_reference_codes == ("BUS-02",)


@pytest.mark.unit
def test_negative_sequence_uses_negative_sequence_data() -> None:
    source = make_voltage_source(
        "GRID-01",
        "BUS-01",
        negative=make_impedance("0.12", "0.22"),
    )
    branch = make_branch(
        "BR-01-02",
        "BUS-01",
        "BUS-02",
        negative=make_impedance("0.06", "0.11"),
    )
    study = make_study(
        fault_type=FaultType.TWO_PHASE,
        sources=(source,),
        branches=(branch,),
    )

    result = reduce_sequence_network(
        study,
        FaultSequence.NEGATIVE,
    )

    assert result.available is True
    assert_decimal_close(
        result.resistance_ohm,
        Decimal("0.18"),
    )
    assert_decimal_close(
        result.reactance_ohm,
        Decimal("0.33"),
    )


@pytest.mark.unit
def test_isolated_neutral_blocks_zero_sequence_source_path() -> None:
    bus = make_bus(
        "BUS-01",
        earthing_mode=NeutralEarthingMode.ISOLATED,
    )
    source = make_voltage_source(
        "GRID-01",
        "BUS-01",
    )
    study = make_study(
        fault_bus_code="BUS-01",
        fault_type=FaultType.SINGLE_PHASE_TO_EARTH,
        buses=(bus,),
        sources=(source,),
        branches=(),
    )

    result = reduce_sequence_network(
        study,
        FaultSequence.ZERO,
    )

    assert result.available is False
    assert result.resistance_ohm is None
    assert result.reactance_ohm is None
    assert result.blocking_reference_codes == ("GRID-01",)


@pytest.mark.unit
def test_resistance_earthed_neutral_adds_three_times_neutral_impedance() -> None:
    bus = make_bus(
        "BUS-01",
        earthing_mode=NeutralEarthingMode.RESISTANCE_EARTHED,
        neutral_resistance_ohm=Decimal("1"),
    )
    source = make_voltage_source(
        "GRID-01",
        "BUS-01",
        zero=make_impedance("0.20", "0.40"),
    )
    study = make_study(
        fault_bus_code="BUS-01",
        fault_type=FaultType.SINGLE_PHASE_TO_EARTH,
        buses=(bus,),
        sources=(source,),
        branches=(),
    )

    result = reduce_sequence_network(
        study,
        FaultSequence.ZERO,
    )

    assert result.available is True
    assert_decimal_close(
        result.resistance_ohm,
        Decimal("3.20"),
    )
    assert_decimal_close(
        result.reactance_ohm,
        Decimal("0.40"),
    )


@pytest.mark.unit
def test_current_injection_source_is_excluded_from_passive_network() -> None:
    bus = make_bus("BUS-01")
    source = make_current_source(
        "PV-01",
        "BUS-01",
    )
    study = make_study(
        fault_bus_code="BUS-01",
        buses=(bus,),
        sources=(source,),
        branches=(),
    )

    result = reduce_sequence_network(
        study,
        FaultSequence.POSITIVE,
    )

    assert result.available is False
    assert result.path_reference_codes == ()
    assert result.blocking_reference_codes == ("BUS-01",)


@pytest.mark.unit
def test_contribution_factor_scales_source_admittance() -> None:
    bus = make_bus("BUS-01")
    source = make_voltage_source(
        "GRID-01",
        "BUS-01",
        positive=make_impedance("0.10", "0.20"),
        contribution_factor=Decimal("0.50"),
    )
    study = make_study(
        fault_bus_code="BUS-01",
        buses=(bus,),
        sources=(source,),
        branches=(),
    )

    result = reduce_sequence_network(
        study,
        FaultSequence.POSITIVE,
    )

    assert_decimal_close(
        result.resistance_ohm,
        Decimal("0.20"),
    )
    assert_decimal_close(
        result.reactance_ohm,
        Decimal("0.40"),
    )


@pytest.mark.unit
def test_sequence_network_reduction_type_is_explicit() -> None:
    result = reduce_sequence_network(
        make_study(),
        FaultSequence.POSITIVE,
    )

    assert isinstance(
        result,
        SequenceNetworkReduction,
    )
    assert result.sequence is FaultSequence.POSITIVE
