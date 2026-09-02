"""
Unit tests for short-circuit and earth-fault engineering domain models.
KESE-S2-M15
"""

from dataclasses import FrozenInstanceError
from decimal import Decimal

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


def make_impedance(
    *,
    resistance_ohm: Decimal = Decimal("0.05"),
    reactance_ohm: Decimal = Decimal("0.25"),
) -> SequenceImpedanceInput:
    return SequenceImpedanceInput(
        resistance_ohm=resistance_ohm,
        reactance_ohm=reactance_ohm,
    )


def make_bus(
    *,
    code: str = "BUS-01",
    neutral_earthing_mode: NeutralEarthingMode = NeutralEarthingMode.SOLIDLY_EARTHED,
    **overrides: object,
) -> FaultBusInput:
    values: dict[str, object] = {
        "code": code,
        "name": code.replace("-", " ").title(),
        "nominal_voltage_v": Decimal("11000"),
        "voltage_factor_max": Decimal("1.10"),
        "voltage_factor_min": Decimal("0.95"),
        "neutral_earthing_mode": neutral_earthing_mode,
        "sld_node_code": f"SLD-{code}",
    }
    values.update(overrides)
    return FaultBusInput(**values)


def make_source(
    *,
    code: str = "GRID-01",
    bus_code: str = "BUS-01",
    representation: SourceRepresentation = SourceRepresentation.VOLTAGE_BEHIND_IMPEDANCE,
    **overrides: object,
) -> FaultSourceInput:
    values: dict[str, object] = {
        "code": code,
        "name": code.replace("-", " ").title(),
        "bus_code": bus_code,
        "source_type": FaultSourceType.UTILITY_GRID,
        "representation": representation,
        "positive_sequence_impedance": make_impedance(),
        "negative_sequence_impedance": make_impedance(
            resistance_ohm=Decimal("0.06"),
            reactance_ohm=Decimal("0.26"),
        ),
        "zero_sequence_impedance": make_impedance(
            resistance_ohm=Decimal("0.15"),
            reactance_ohm=Decimal("0.45"),
        ),
        "current_contribution_ka": None,
        "equipment_reference": f"EQ-{code}",
    }
    if representation is SourceRepresentation.CURRENT_INJECTION:
        values.update(
            {
                "positive_sequence_impedance": None,
                "negative_sequence_impedance": None,
                "zero_sequence_impedance": None,
                "current_contribution_ka": Decimal("1.25"),
            }
        )
    values.update(overrides)
    return FaultSourceInput(**values)


def make_branch(
    *,
    code: str = "BR-01-02",
    from_bus_code: str = "BUS-01",
    to_bus_code: str = "BUS-02",
    **overrides: object,
) -> FaultBranchInput:
    values: dict[str, object] = {
        "code": code,
        "name": code.replace("-", " ").title(),
        "from_bus_code": from_bus_code,
        "to_bus_code": to_bus_code,
        "branch_type": FaultBranchType.CABLE,
        "positive_sequence_impedance": make_impedance(),
        "negative_sequence_impedance": make_impedance(
            resistance_ohm=Decimal("0.05"),
            reactance_ohm=Decimal("0.25"),
        ),
        "zero_sequence_impedance": make_impedance(
            resistance_ohm=Decimal("0.20"),
            reactance_ohm=Decimal("0.60"),
        ),
        "equipment_reference": f"EQ-{code}",
    }
    values.update(overrides)
    return FaultBranchInput(**values)


def make_fault(
    *,
    bus_code: str = "BUS-02",
    fault_type: FaultType = FaultType.THREE_PHASE,
    **overrides: object,
) -> FaultLocationInput:
    values: dict[str, object] = {
        "bus_code": bus_code,
        "fault_type": fault_type,
        "clearing_time_s": Decimal("0.20"),
    }
    values.update(overrides)
    return FaultLocationInput(**values)


def make_study(**overrides: object) -> ShortCircuitStudyInput:
    values: dict[str, object] = {
        "code": "SC-STUDY-01",
        "name": "Main Substation Fault Study",
        "calculation_case": ShortCircuitCase.MAXIMUM,
        "fault": make_fault(),
        "buses": (make_bus(), make_bus(code="BUS-02")),
        "sources": (make_source(),),
        "branches": (make_branch(),),
        "operating_state_code": "STATE-NORMAL",
    }
    values.update(overrides)
    return ShortCircuitStudyInput(**values)


@pytest.mark.unit
def test_create_valid_short_circuit_study() -> None:
    study = make_study()

    assert study.code == "SC-STUDY-01"
    assert study.calculation_case is ShortCircuitCase.MAXIMUM
    assert study.fault.fault_type is FaultType.THREE_PHASE
    assert study.frequency_hz == Decimal("50")
    assert study.standard_reference == "IEC 60909-0:2026"
    assert study.earth_current_reference == "IEC 60909-3:2009"


@pytest.mark.unit
def test_fault_records_are_immutable() -> None:
    bus = make_bus()

    with pytest.raises(FrozenInstanceError):
        bus.name = "Changed"


@pytest.mark.unit
def test_text_fields_are_normalized() -> None:
    bus = make_bus(
        code="  BUS-01  ",
        name="  Main Bus  ",
        sld_node_code="  SLD-BUS-01  ",
        notes="   ",
    )
    source = make_source(
        code="  GRID-01  ",
        name="  Utility Grid  ",
        bus_code="  BUS-01  ",
        equipment_reference="  EQ-GRID-01  ",
        notes="  Maximum utility case  ",
    )

    assert bus.code == "BUS-01"
    assert bus.name == "Main Bus"
    assert bus.sld_node_code == "SLD-BUS-01"
    assert bus.notes is None
    assert source.code == "GRID-01"
    assert source.name == "Utility Grid"
    assert source.bus_code == "BUS-01"
    assert source.equipment_reference == "EQ-GRID-01"
    assert source.notes == "Maximum utility case"


@pytest.mark.unit
def test_sequence_impedance_requires_exact_non_zero_decimal_values() -> None:
    with pytest.raises(TypeError, match="resistance_ohm must be a Decimal"):
        make_impedance(resistance_ohm=0.05)

    with pytest.raises(ValueError, match="reactance_ohm must not be negative"):
        make_impedance(reactance_ohm=Decimal("-0.01"))

    with pytest.raises(ValueError, match="sequence impedance must not be zero"):
        make_impedance(
            resistance_ohm=Decimal("0"),
            reactance_ohm=Decimal("0"),
        )


@pytest.mark.unit
def test_bus_requires_valid_voltage_factors() -> None:
    with pytest.raises(ValueError, match="nominal_voltage_v must be greater than zero"):
        make_bus(nominal_voltage_v=Decimal("0"))

    with pytest.raises(ValueError, match="voltage_factor_min must not exceed"):
        make_bus(
            voltage_factor_max=Decimal("0.95"),
            voltage_factor_min=Decimal("1.00"),
        )


@pytest.mark.unit
def test_solidly_earthed_bus_requires_zero_neutral_impedance() -> None:
    with pytest.raises(ValueError, match="requires zero neutral impedance"):
        make_bus(neutral_resistance_ohm=Decimal("0.10"))


@pytest.mark.unit
def test_resistance_earthed_bus_requires_neutral_resistance() -> None:
    bus = make_bus(
        neutral_earthing_mode=NeutralEarthingMode.RESISTANCE_EARTHED,
        neutral_resistance_ohm=Decimal("10"),
    )

    assert bus.neutral_resistance_ohm == Decimal("10")

    with pytest.raises(ValueError, match="requires neutral resistance"):
        make_bus(neutral_earthing_mode=NeutralEarthingMode.RESISTANCE_EARTHED)


@pytest.mark.unit
@pytest.mark.parametrize(
    "earthing_mode",
    [
        NeutralEarthingMode.REACTANCE_EARTHED,
        NeutralEarthingMode.RESONANT_EARTHED,
    ],
)
def test_reactive_earthing_modes_require_neutral_reactance(
    earthing_mode: NeutralEarthingMode,
) -> None:
    bus = make_bus(
        neutral_earthing_mode=earthing_mode,
        neutral_reactance_ohm=Decimal("5"),
    )

    assert bus.neutral_reactance_ohm == Decimal("5")

    with pytest.raises(ValueError, match="requires neutral reactance"):
        make_bus(neutral_earthing_mode=earthing_mode)


@pytest.mark.unit
def test_isolated_bus_rejects_neutral_impedance() -> None:
    bus = make_bus(neutral_earthing_mode=NeutralEarthingMode.ISOLATED)

    assert bus.neutral_resistance_ohm == Decimal("0")
    assert bus.neutral_reactance_ohm == Decimal("0")

    with pytest.raises(ValueError, match="cannot define a neutral earthing impedance"):
        make_bus(
            neutral_earthing_mode=NeutralEarthingMode.ISOLATED,
            neutral_reactance_ohm=Decimal("1"),
        )


@pytest.mark.unit
def test_bus_rejects_non_enum_earthing_mode() -> None:
    with pytest.raises(TypeError, match="must be a NeutralEarthingMode"):
        make_bus(neutral_earthing_mode="SOLIDLY_EARTHED")


@pytest.mark.unit
def test_voltage_behind_impedance_source_requires_positive_sequence_data() -> None:
    with pytest.raises(ValueError, match="requires positive-sequence impedance"):
        make_source(positive_sequence_impedance=None)


@pytest.mark.unit
def test_voltage_behind_impedance_source_rejects_current_contribution() -> None:
    with pytest.raises(ValueError, match="cannot define current_contribution_ka"):
        make_source(current_contribution_ka=Decimal("1"))


@pytest.mark.unit
def test_current_injection_source_requires_current_and_rejects_impedances() -> None:
    with pytest.raises(ValueError, match="requires current_contribution_ka"):
        make_source(
            representation=SourceRepresentation.CURRENT_INJECTION,
            current_contribution_ka=None,
        )

    with pytest.raises(ValueError, match="cannot define sequence impedances"):
        make_source(
            representation=SourceRepresentation.CURRENT_INJECTION,
            positive_sequence_impedance=make_impedance(),
        )


@pytest.mark.unit
def test_current_injection_source_requires_positive_decimal_current() -> None:
    with pytest.raises(TypeError, match="current_contribution_ka must be a Decimal"):
        make_source(
            representation=SourceRepresentation.CURRENT_INJECTION,
            current_contribution_ka=1.25,
        )

    with pytest.raises(ValueError, match="current_contribution_ka must be greater than zero"):
        make_source(
            representation=SourceRepresentation.CURRENT_INJECTION,
            current_contribution_ka=Decimal("0"),
        )


@pytest.mark.unit
def test_source_contribution_factor_and_service_flag_are_strict() -> None:
    with pytest.raises(ValueError, match="contribution_factor must be greater than 0"):
        make_source(contribution_factor=Decimal("0"))

    with pytest.raises(TypeError, match="in_service must be a boolean"):
        make_source(in_service=1)


@pytest.mark.unit
def test_source_rejects_invalid_sequence_record_type() -> None:
    with pytest.raises(TypeError, match="negative_sequence_impedance must be"):
        make_source(negative_sequence_impedance=Decimal("0.25"))


@pytest.mark.unit
@pytest.mark.parametrize(
    ("field_name", "invalid_value", "message"),
    [
        ("source_type", "UTILITY_GRID", "source_type must be a FaultSourceType"),
        (
            "representation",
            "VOLTAGE_BEHIND_IMPEDANCE",
            "representation must be a SourceRepresentation",
        ),
    ],
)
def test_source_rejects_non_enum_classification(
    field_name: str,
    invalid_value: str,
    message: str,
) -> None:
    with pytest.raises(TypeError, match=message):
        make_source(**{field_name: invalid_value})


@pytest.mark.unit
def test_branch_rejects_self_loop() -> None:
    with pytest.raises(ValueError, match="cannot connect a bus to itself"):
        make_branch(to_bus_code="BUS-01")


@pytest.mark.unit
def test_branch_requires_positive_sequence_record() -> None:
    with pytest.raises(TypeError, match="positive_sequence_impedance must be"):
        make_branch(positive_sequence_impedance=None)


@pytest.mark.unit
def test_branch_rejects_non_enum_type_and_invalid_optional_sequence() -> None:
    with pytest.raises(TypeError, match="branch_type must be a FaultBranchType"):
        make_branch(branch_type="CABLE")

    with pytest.raises(TypeError, match="zero_sequence_impedance must be"):
        make_branch(zero_sequence_impedance=Decimal("0.60"))


@pytest.mark.unit
def test_branch_requires_positive_integer_parallel_circuits() -> None:
    with pytest.raises(ValueError, match="parallel_circuits must be at least 1"):
        make_branch(parallel_circuits=0)

    with pytest.raises(TypeError, match="parallel_circuits must be an integer"):
        make_branch(parallel_circuits=True)


@pytest.mark.unit
def test_branch_service_flag_is_strict_boolean() -> None:
    with pytest.raises(TypeError, match="in_service must be a boolean"):
        make_branch(in_service="yes")


@pytest.mark.unit
def test_fault_location_validates_impedance_and_clearing_time() -> None:
    fault = make_fault(clearing_time_s=None)

    assert fault.clearing_time_s is None

    with pytest.raises(ValueError, match="fault_resistance_ohm must not be negative"):
        make_fault(fault_resistance_ohm=Decimal("-0.01"))

    with pytest.raises(ValueError, match="clearing_time_s must be greater than zero"):
        make_fault(clearing_time_s=Decimal("0"))


@pytest.mark.unit
def test_fault_location_rejects_non_enum_fault_type() -> None:
    with pytest.raises(TypeError, match="fault_type must be a FaultType"):
        make_fault(fault_type="THREE_PHASE")


@pytest.mark.unit
@pytest.mark.parametrize("field_name", ["buses", "sources", "branches"])
def test_study_collections_must_be_tuples(field_name: str) -> None:
    study = make_study()

    with pytest.raises(TypeError, match=rf"{field_name} must be a tuple"):
        make_study(**{field_name: list(getattr(study, field_name))})


@pytest.mark.unit
def test_study_collections_reject_wrong_record_types() -> None:
    with pytest.raises(TypeError, match="buses must contain only FaultBusInput"):
        make_study(buses=(make_source(),))


@pytest.mark.unit
def test_study_rejects_invalid_case_and_fault_record_types() -> None:
    with pytest.raises(TypeError, match="calculation_case must be a ShortCircuitCase"):
        make_study(calculation_case="MAXIMUM")

    with pytest.raises(TypeError, match="fault must be a FaultLocationInput"):
        make_study(fault="BUS-02")


@pytest.mark.unit
def test_study_requires_bus_and_source() -> None:
    with pytest.raises(ValueError, match="requires at least one bus"):
        make_study(buses=())

    with pytest.raises(ValueError, match="requires at least one source"):
        make_study(sources=())


@pytest.mark.unit
def test_study_accepts_only_iec_frequency_values() -> None:
    assert make_study(frequency_hz=Decimal("60")).frequency_hz == Decimal("60")

    with pytest.raises(ValueError, match="frequency_hz must be 50 or 60"):
        make_study(frequency_hz=Decimal("55"))

    with pytest.raises(TypeError, match="frequency_hz must be a Decimal"):
        make_study(frequency_hz=50)


@pytest.mark.unit
@pytest.mark.parametrize(
    ("field_name", "duplicate_value", "message"),
    [
        ("buses", make_bus(), "fault bus codes must be unique"),
        ("sources", make_source(), "fault source codes must be unique"),
        ("branches", make_branch(), "fault branch codes must be unique"),
    ],
)
def test_study_rejects_duplicate_record_codes(
    field_name: str,
    duplicate_value: object,
    message: str,
) -> None:
    study = make_study()

    with pytest.raises(ValueError, match=message):
        make_study(**{field_name: (*getattr(study, field_name), duplicate_value)})


@pytest.mark.unit
def test_study_rejects_unknown_fault_bus() -> None:
    with pytest.raises(ValueError, match="fault location references an unknown bus"):
        make_study(fault=make_fault(bus_code="UNKNOWN"))


@pytest.mark.unit
def test_study_rejects_unknown_source_bus() -> None:
    with pytest.raises(ValueError, match="source GRID-01 references an unknown bus"):
        make_study(sources=(make_source(bus_code="UNKNOWN"),))


@pytest.mark.unit
def test_study_requires_an_in_service_source() -> None:
    with pytest.raises(ValueError, match="requires an in-service source"):
        make_study(sources=(make_source(in_service=False),))


@pytest.mark.unit
@pytest.mark.parametrize(
    ("endpoint", "message"),
    [
        ("from_bus_code", "unknown from_bus_code"),
        ("to_bus_code", "unknown to_bus_code"),
    ],
)
def test_study_rejects_unknown_branch_endpoint(endpoint: str, message: str) -> None:
    branch = make_branch(**{endpoint: "UNKNOWN"})

    with pytest.raises(ValueError, match=message):
        make_study(branches=(branch,))


@pytest.mark.unit
@pytest.mark.parametrize(
    "fault_type",
    [
        FaultType.TWO_PHASE,
        FaultType.TWO_PHASE_TO_EARTH,
        FaultType.SINGLE_PHASE_TO_EARTH,
    ],
)
def test_unbalanced_fault_requires_source_negative_sequence(
    fault_type: FaultType,
) -> None:
    source = make_source(negative_sequence_impedance=None)

    with pytest.raises(ValueError, match="requires explicit source negative-sequence data"):
        make_study(fault=make_fault(fault_type=fault_type), sources=(source,))


@pytest.mark.unit
def test_unbalanced_fault_requires_branch_negative_sequence() -> None:
    branch = make_branch(negative_sequence_impedance=None)

    with pytest.raises(ValueError, match="requires explicit branch negative-sequence data"):
        make_study(
            fault=make_fault(fault_type=FaultType.SINGLE_PHASE_TO_EARTH),
            branches=(branch,),
        )


@pytest.mark.unit
def test_out_of_service_records_do_not_require_negative_sequence_data() -> None:
    source = make_source(
        code="GRID-STANDBY",
        negative_sequence_impedance=None,
        in_service=False,
    )
    branch = make_branch(
        code="BR-STANDBY",
        negative_sequence_impedance=None,
        in_service=False,
    )
    study = make_study(
        fault=make_fault(fault_type=FaultType.SINGLE_PHASE_TO_EARTH),
        sources=(make_source(), source),
        branches=(make_branch(), branch),
    )

    assert len(study.sources) == 2
    assert len(study.branches) == 2


@pytest.mark.unit
def test_blocked_zero_sequence_paths_are_explicitly_supported() -> None:
    source = make_source(zero_sequence_impedance=None)
    branch = make_branch(zero_sequence_impedance=None)
    study = make_study(
        fault=make_fault(fault_type=FaultType.SINGLE_PHASE_TO_EARTH),
        sources=(source,),
        branches=(branch,),
    )

    assert study.sources[0].zero_sequence_impedance is None
    assert study.branches[0].zero_sequence_impedance is None


@pytest.mark.unit
def test_balanced_fault_allows_missing_negative_sequence_data() -> None:
    study = make_study(
        sources=(make_source(negative_sequence_impedance=None),),
        branches=(make_branch(negative_sequence_impedance=None),),
    )

    assert study.fault.fault_type is FaultType.THREE_PHASE
