"""
Unit tests for short-circuit and earth-fault engineering results.
KESE-S2-M15
"""

from dataclasses import FrozenInstanceError
from decimal import Decimal

import pytest

from app.domain.electrical.fault.fault_models import (
    FaultSourceType,
    FaultType,
    ShortCircuitCase,
    SourceRepresentation,
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


def make_warning(**overrides: object) -> FaultEngineeringWarning:
    values: dict[str, object] = {
        "code": FaultWarningCode.PEAK_CURRENT_NOT_EVALUATED,
        "severity": FaultWarningSeverity.WARNING,
        "message": "Peak current was not evaluated",
        "reference_code": "BUS-02",
    }
    values.update(overrides)
    return FaultEngineeringWarning(**values)


def make_sequence(
    *,
    sequence: FaultSequence = FaultSequence.POSITIVE,
    **overrides: object,
) -> EquivalentSequenceImpedanceResult:
    values: dict[str, object] = {
        "sequence": sequence,
        "available": True,
        "resistance_ohm": Decimal("0.05"),
        "reactance_ohm": Decimal("0.25"),
        "path_reference_codes": ("GRID-01", "BR-01-02"),
        "blocking_reference_codes": (),
    }
    values.update(overrides)
    return EquivalentSequenceImpedanceResult(**values)


def make_blocked_sequence(
    *,
    sequence: FaultSequence = FaultSequence.ZERO,
    **overrides: object,
) -> EquivalentSequenceImpedanceResult:
    values: dict[str, object] = {
        "sequence": sequence,
        "available": False,
        "resistance_ohm": None,
        "reactance_ohm": None,
        "path_reference_codes": (),
        "blocking_reference_codes": ("TX-01",),
    }
    values.update(overrides)
    return EquivalentSequenceImpedanceResult(**values)


def make_contribution(**overrides: object) -> FaultSourceContributionResult:
    values: dict[str, object] = {
        "source_code": "GRID-01",
        "source_type": FaultSourceType.UTILITY_GRID,
        "representation": SourceRepresentation.VOLTAGE_BEHIND_IMPEDANCE,
        "included": True,
        "initial_symmetrical_current_ka": Decimal("22.50"),
        "peak_current_ka": Decimal("55.10"),
        "exclusion_reason": None,
    }
    values.update(overrides)
    return FaultSourceContributionResult(**values)


def make_excluded_contribution(
    **overrides: object,
) -> FaultSourceContributionResult:
    values: dict[str, object] = {
        "source_code": "GRID-01",
        "source_type": FaultSourceType.UTILITY_GRID,
        "representation": SourceRepresentation.VOLTAGE_BEHIND_IMPEDANCE,
        "included": False,
        "initial_symmetrical_current_ka": Decimal("0"),
        "peak_current_ka": None,
        "exclusion_reason": "Source is disconnected from the fault",
    }
    values.update(overrides)
    return FaultSourceContributionResult(**values)


def make_result(**overrides: object) -> ShortCircuitStudyResult:
    values: dict[str, object] = {
        "study_code": "SC-STUDY-01",
        "study_name": "Main Substation Maximum Fault",
        "calculation_case": ShortCircuitCase.MAXIMUM,
        "fault_bus_code": "BUS-02",
        "fault_type": FaultType.THREE_PHASE,
        "nominal_voltage_v": Decimal("11000"),
        "frequency_hz": Decimal("50"),
        "status": FaultResultStatus.CALCULATED,
        "initial_symmetrical_short_circuit_current_ka": Decimal("22.50"),
        "peak_short_circuit_current_ka": Decimal("55.10"),
        "symmetrical_breaking_current_ka": Decimal("21.80"),
        "steady_state_short_circuit_current_ka": Decimal("20.40"),
        "thermal_equivalent_short_circuit_current_ka": Decimal("23.10"),
        "earth_fault_current_ka": None,
        "kappa_factor": Decimal("1.73"),
        "x_r_ratio": Decimal("5"),
        "clearing_time_s": Decimal("0.20"),
        "sequence_results": (make_sequence(),),
        "source_contributions": (make_contribution(),),
        "warnings": (),
        "operating_state_code": "STATE-NORMAL",
    }
    values.update(overrides)
    return ShortCircuitStudyResult(**values)


def make_zero_earth_fault_result(**overrides: object) -> ShortCircuitStudyResult:
    warning = make_warning(
        code=FaultWarningCode.NO_FAULT_CURRENT_PATH,
        message="No closed zero-sequence path reaches the fault",
    )
    values: dict[str, object] = {
        "calculation_case": ShortCircuitCase.MINIMUM,
        "fault_type": FaultType.SINGLE_PHASE_TO_EARTH,
        "status": FaultResultStatus.WARNING,
        "initial_symmetrical_short_circuit_current_ka": Decimal("0"),
        "peak_short_circuit_current_ka": None,
        "symmetrical_breaking_current_ka": None,
        "steady_state_short_circuit_current_ka": None,
        "thermal_equivalent_short_circuit_current_ka": None,
        "earth_fault_current_ka": Decimal("0"),
        "kappa_factor": None,
        "x_r_ratio": None,
        "clearing_time_s": None,
        "sequence_results": (
            make_sequence(),
            make_sequence(sequence=FaultSequence.NEGATIVE),
            make_blocked_sequence(),
        ),
        "source_contributions": (make_excluded_contribution(),),
        "warnings": (warning,),
    }
    values.update(overrides)
    return make_result(**values)


def make_indeterminate_result(**overrides: object) -> ShortCircuitStudyResult:
    error = make_warning(
        code=FaultWarningCode.CALCULATION_FAILED,
        severity=FaultWarningSeverity.ERROR,
        message="Network reduction failed",
        reference_code=None,
    )
    values: dict[str, object] = {
        "status": FaultResultStatus.INDETERMINATE,
        "initial_symmetrical_short_circuit_current_ka": None,
        "peak_short_circuit_current_ka": None,
        "symmetrical_breaking_current_ka": None,
        "steady_state_short_circuit_current_ka": None,
        "thermal_equivalent_short_circuit_current_ka": None,
        "earth_fault_current_ka": None,
        "kappa_factor": None,
        "x_r_ratio": None,
        "clearing_time_s": None,
        "source_contributions": (make_excluded_contribution(),),
        "warnings": (error,),
    }
    values.update(overrides)
    return make_result(**values)


@pytest.mark.unit
def test_create_valid_calculated_result() -> None:
    result = make_result()

    assert result.status is FaultResultStatus.CALCULATED
    assert result.initial_symmetrical_short_circuit_current_ka == Decimal("22.50")
    assert result.standard_reference == "IEC 60909-0:2026"
    assert result.earth_current_reference == "IEC 60909-3:2009"


@pytest.mark.unit
def test_result_records_are_immutable() -> None:
    result = make_result()

    with pytest.raises(FrozenInstanceError):
        result.status = FaultResultStatus.WARNING


@pytest.mark.unit
def test_warning_normalizes_text() -> None:
    warning = make_warning(
        message="  Peak current was not evaluated  ",
        reference_code="  BUS-02  ",
    )

    assert warning.message == "Peak current was not evaluated"
    assert warning.reference_code == "BUS-02"


@pytest.mark.unit
def test_warning_rejects_non_enum_values() -> None:
    with pytest.raises(TypeError, match="code must be a FaultWarningCode"):
        make_warning(code="PEAK_CURRENT_NOT_EVALUATED")

    with pytest.raises(TypeError, match="severity must be a FaultWarningSeverity"):
        make_warning(severity="WARNING")


@pytest.mark.unit
def test_create_available_sequence_result() -> None:
    sequence = make_sequence(
        path_reference_codes=("  GRID-01  ", "  BR-01-02  "),
    )

    assert sequence.available is True
    assert sequence.path_reference_codes == ("GRID-01", "BR-01-02")
    assert sequence.blocking_reference_codes == ()


@pytest.mark.unit
def test_sequence_rejects_invalid_enum_and_boolean() -> None:
    with pytest.raises(TypeError, match="sequence must be a FaultSequence"):
        make_sequence(sequence="POSITIVE")

    with pytest.raises(TypeError, match="available must be a boolean"):
        make_sequence(available=1)


@pytest.mark.unit
def test_sequence_reference_codes_must_be_unique_tuples() -> None:
    with pytest.raises(TypeError, match="path_reference_codes must be a tuple"):
        make_sequence(path_reference_codes=["GRID-01"])

    with pytest.raises(ValueError, match="path_reference_codes values must be unique"):
        make_sequence(path_reference_codes=("GRID-01", "GRID-01"))


@pytest.mark.unit
def test_sequence_path_and_blocking_references_cannot_overlap() -> None:
    with pytest.raises(ValueError, match="must not overlap"):
        make_sequence(blocking_reference_codes=("GRID-01",))


@pytest.mark.unit
def test_available_sequence_requires_complete_non_zero_impedance() -> None:
    with pytest.raises(ValueError, match="requires resistance and reactance"):
        make_sequence(resistance_ohm=None)

    with pytest.raises(TypeError, match="resistance_ohm must be a Decimal"):
        make_sequence(resistance_ohm=0.05)

    with pytest.raises(ValueError, match="impedance must not be zero"):
        make_sequence(
            resistance_ohm=Decimal("0"),
            reactance_ohm=Decimal("0"),
        )


@pytest.mark.unit
def test_available_sequence_rejects_blocking_references() -> None:
    with pytest.raises(ValueError, match="cannot define blocking references"):
        make_sequence(blocking_reference_codes=("TX-01",))


@pytest.mark.unit
def test_unavailable_sequence_requires_explicit_blocking_representation() -> None:
    sequence = make_blocked_sequence()

    assert sequence.available is False
    assert sequence.blocking_reference_codes == ("TX-01",)

    with pytest.raises(ValueError, match="cannot define impedance values"):
        make_blocked_sequence(resistance_ohm=Decimal("0.50"))

    with pytest.raises(ValueError, match="requires blocking references"):
        make_blocked_sequence(blocking_reference_codes=())


@pytest.mark.unit
def test_create_included_source_contribution() -> None:
    contribution = make_contribution(source_code="  GRID-01  ")

    assert contribution.source_code == "GRID-01"
    assert contribution.included is True
    assert contribution.peak_current_ka == Decimal("55.10")


@pytest.mark.unit
def test_source_contribution_rejects_invalid_classification() -> None:
    with pytest.raises(TypeError, match="source_type must be a FaultSourceType"):
        make_contribution(source_type="UTILITY_GRID")

    with pytest.raises(TypeError, match="representation must be a SourceRepresentation"):
        make_contribution(representation="VOLTAGE_BEHIND_IMPEDANCE")

    with pytest.raises(TypeError, match="included must be a boolean"):
        make_contribution(included=1)


@pytest.mark.unit
def test_source_contribution_requires_exact_non_negative_currents() -> None:
    with pytest.raises(TypeError, match="initial_symmetrical_current_ka must be a Decimal"):
        make_contribution(initial_symmetrical_current_ka=22.5)

    with pytest.raises(ValueError, match="peak_current_ka must not be negative"):
        make_contribution(peak_current_ka=Decimal("-1"))

    with pytest.raises(ValueError, match="must not be below initial symmetrical"):
        make_contribution(peak_current_ka=Decimal("20"))


@pytest.mark.unit
def test_included_source_requires_positive_current_and_no_exclusion_reason() -> None:
    with pytest.raises(ValueError, match="requires a positive current contribution"):
        make_contribution(initial_symmetrical_current_ka=Decimal("0"))

    with pytest.raises(ValueError, match="cannot define an exclusion reason"):
        make_contribution(exclusion_reason="Disconnected")


@pytest.mark.unit
def test_excluded_source_requires_zero_current_and_reason() -> None:
    contribution = make_excluded_contribution(exclusion_reason="  Breaker open  ")

    assert contribution.exclusion_reason == "Breaker open"

    with pytest.raises(ValueError, match="must have zero current contribution"):
        make_excluded_contribution(initial_symmetrical_current_ka=Decimal("1"))

    with pytest.raises(ValueError, match="cannot define peak_current_ka"):
        make_excluded_contribution(peak_current_ka=Decimal("1"))

    with pytest.raises(ValueError, match="requires an exclusion reason"):
        make_excluded_contribution(exclusion_reason="  ")


@pytest.mark.unit
def test_study_text_fields_are_normalized() -> None:
    result = make_result(
        study_code="  SC-STUDY-01  ",
        study_name="  Main Fault Study  ",
        fault_bus_code="  BUS-02  ",
        standard_reference="  IEC 60909-0:2026  ",
        earth_current_reference="  IEC 60909-3:2009  ",
        operating_state_code="  STATE-NORMAL  ",
        notes="   ",
    )

    assert result.study_code == "SC-STUDY-01"
    assert result.study_name == "Main Fault Study"
    assert result.fault_bus_code == "BUS-02"
    assert result.standard_reference == "IEC 60909-0:2026"
    assert result.earth_current_reference == "IEC 60909-3:2009"
    assert result.operating_state_code == "STATE-NORMAL"
    assert result.notes is None


@pytest.mark.unit
@pytest.mark.parametrize(
    ("field_name", "invalid_value", "message"),
    [
        ("calculation_case", "MAXIMUM", "calculation_case must be a ShortCircuitCase"),
        ("fault_type", "THREE_PHASE", "fault_type must be a FaultType"),
        ("status", "CALCULATED", "status must be a FaultResultStatus"),
    ],
)
def test_study_rejects_non_enum_values(
    field_name: str,
    invalid_value: str,
    message: str,
) -> None:
    with pytest.raises(TypeError, match=message):
        make_result(**{field_name: invalid_value})


@pytest.mark.unit
def test_study_requires_positive_exact_voltage_and_iec_frequency() -> None:
    with pytest.raises(TypeError, match="nominal_voltage_v must be a Decimal"):
        make_result(nominal_voltage_v=11000)

    with pytest.raises(ValueError, match="nominal_voltage_v must be greater than zero"):
        make_result(nominal_voltage_v=Decimal("0"))

    assert make_result(frequency_hz=Decimal("60")).frequency_hz == Decimal("60")

    with pytest.raises(ValueError, match="frequency_hz must be 50 or 60"):
        make_result(frequency_hz=Decimal("55"))


@pytest.mark.unit
def test_study_current_duties_require_exact_non_negative_decimals() -> None:
    with pytest.raises(TypeError, match="symmetrical_breaking_current_ka must be a Decimal"):
        make_result(symmetrical_breaking_current_ka=21.8)

    with pytest.raises(ValueError, match=r"steady_state.*must not be negative"):
        make_result(steady_state_short_circuit_current_ka=Decimal("-1"))

    with pytest.raises(ValueError, match="x_r_ratio must not be negative"):
        make_result(x_r_ratio=Decimal("-1"))


@pytest.mark.unit
def test_kappa_factor_and_clearing_time_are_bounded() -> None:
    with pytest.raises(TypeError, match="kappa_factor must be a Decimal"):
        make_result(kappa_factor=1.73)

    with pytest.raises(ValueError, match="kappa_factor must be between 1 and 2"):
        make_result(kappa_factor=Decimal("2.01"))

    with pytest.raises(ValueError, match="clearing_time_s must be greater than zero"):
        make_result(clearing_time_s=Decimal("0"))


@pytest.mark.unit
@pytest.mark.parametrize(
    "field_name",
    ["sequence_results", "source_contributions", "warnings"],
)
def test_study_collections_must_be_tuples(field_name: str) -> None:
    result = make_result()

    with pytest.raises(TypeError, match=rf"{field_name} must be a tuple"):
        make_result(**{field_name: list(getattr(result, field_name))})


@pytest.mark.unit
def test_study_collections_reject_wrong_record_types() -> None:
    with pytest.raises(TypeError, match="sequence_results must contain only"):
        make_result(sequence_results=(make_contribution(),))

    with pytest.raises(TypeError, match="source_contributions must contain only"):
        make_result(source_contributions=(make_sequence(),))

    with pytest.raises(TypeError, match="warnings must contain only"):
        make_result(warnings=(make_sequence(),))


@pytest.mark.unit
def test_study_requires_sequence_results() -> None:
    with pytest.raises(ValueError, match="requires sequence results"):
        make_result(sequence_results=())


@pytest.mark.unit
def test_study_rejects_duplicate_sequence_source_and_warning_keys() -> None:
    sequence = make_sequence()
    with pytest.raises(ValueError, match="sequence result types must be unique"):
        make_result(sequence_results=(sequence, sequence))

    contribution = make_contribution()
    with pytest.raises(ValueError, match="source contribution codes must be unique"):
        make_result(source_contributions=(contribution, contribution))

    warning = make_warning()
    with pytest.raises(ValueError, match="warning code and reference combinations"):
        make_result(
            status=FaultResultStatus.WARNING,
            warnings=(warning, warning),
        )


@pytest.mark.unit
@pytest.mark.parametrize(
    ("fault_type", "sequence_results"),
    [
        (FaultType.THREE_PHASE, (make_sequence(sequence=FaultSequence.NEGATIVE),)),
        (FaultType.TWO_PHASE, (make_sequence(),)),
        (
            FaultType.TWO_PHASE_TO_EARTH,
            (
                make_sequence(),
                make_sequence(sequence=FaultSequence.NEGATIVE),
            ),
        ),
        (
            FaultType.SINGLE_PHASE_TO_EARTH,
            (
                make_sequence(),
                make_sequence(sequence=FaultSequence.NEGATIVE),
            ),
        ),
    ],
)
def test_study_requires_sequences_for_fault_type(
    fault_type: FaultType,
    sequence_results: tuple[EquivalentSequenceImpedanceResult, ...],
) -> None:
    with pytest.raises(ValueError, match="missing a required sequence result"):
        make_result(fault_type=fault_type, sequence_results=sequence_results)


@pytest.mark.unit
def test_warning_and_error_severity_derive_result_status() -> None:
    warning = make_warning()
    result = make_result(
        status=FaultResultStatus.WARNING,
        peak_short_circuit_current_ka=None,
        kappa_factor=None,
        x_r_ratio=None,
        warnings=(warning,),
    )

    assert result.status is FaultResultStatus.WARNING

    with pytest.raises(ValueError, match="status does not match"):
        make_result(status=FaultResultStatus.WARNING)

    with pytest.raises(ValueError, match="status does not match"):
        make_result(warnings=(warning,))


@pytest.mark.unit
def test_create_valid_indeterminate_result() -> None:
    result = make_indeterminate_result()

    assert result.status is FaultResultStatus.INDETERMINATE
    assert result.initial_symmetrical_short_circuit_current_ka is None


@pytest.mark.unit
def test_indeterminate_result_rejects_duties_and_included_sources() -> None:
    with pytest.raises(ValueError, match="must not contain calculated current duties"):
        make_indeterminate_result(
            initial_symmetrical_short_circuit_current_ka=Decimal("1"),
        )

    with pytest.raises(ValueError, match="cannot contain included source contributions"):
        make_indeterminate_result(source_contributions=(make_contribution(),))


@pytest.mark.unit
def test_calculated_result_requires_initial_current() -> None:
    with pytest.raises(ValueError, match="requires initial symmetrical current"):
        make_result(initial_symmetrical_short_circuit_current_ka=None)


@pytest.mark.unit
def test_earth_fault_requires_explicit_earth_current() -> None:
    sequences = (
        make_sequence(),
        make_sequence(sequence=FaultSequence.NEGATIVE),
        make_sequence(sequence=FaultSequence.ZERO),
    )

    with pytest.raises(ValueError, match="requires earth_fault_current_ka"):
        make_result(
            fault_type=FaultType.SINGLE_PHASE_TO_EARTH,
            sequence_results=sequences,
        )


@pytest.mark.unit
def test_non_earth_fault_rejects_earth_current() -> None:
    with pytest.raises(ValueError, match="cannot define earth_fault_current_ka"):
        make_result(earth_fault_current_ka=Decimal("1"))


@pytest.mark.unit
def test_peak_current_kappa_and_x_r_ratio_are_atomic() -> None:
    with pytest.raises(ValueError, match="must be provided together"):
        make_result(kappa_factor=None)

    with pytest.raises(ValueError, match="must not be below initial current"):
        make_result(peak_short_circuit_current_ka=Decimal("20"))


@pytest.mark.unit
def test_thermal_current_and_clearing_time_are_atomic() -> None:
    with pytest.raises(ValueError, match="must be provided together"):
        make_result(clearing_time_s=None)

    with pytest.raises(ValueError, match="must be provided together"):
        make_result(thermal_equivalent_short_circuit_current_ka=None)


@pytest.mark.unit
def test_positive_fault_current_requires_included_source() -> None:
    with pytest.raises(ValueError, match="requires an included source contribution"):
        make_result(source_contributions=(make_excluded_contribution(),))


@pytest.mark.unit
def test_zero_fault_current_rejects_included_source() -> None:
    warning = make_warning(code=FaultWarningCode.NO_FAULT_CURRENT_PATH)

    with pytest.raises(ValueError, match="cannot contain included source contributions"):
        make_result(
            status=FaultResultStatus.WARNING,
            initial_symmetrical_short_circuit_current_ka=Decimal("0"),
            peak_short_circuit_current_ka=None,
            kappa_factor=None,
            x_r_ratio=None,
            source_contributions=(make_contribution(),),
            warnings=(warning,),
        )


@pytest.mark.unit
def test_zero_fault_current_requires_no_path_warning() -> None:
    warning = make_warning(code=FaultWarningCode.ENGINEERING_REVIEW_REQUIRED)

    with pytest.raises(ValueError, match="requires NO_FAULT_CURRENT_PATH warning"):
        make_result(
            status=FaultResultStatus.WARNING,
            initial_symmetrical_short_circuit_current_ka=Decimal("0"),
            peak_short_circuit_current_ka=None,
            kappa_factor=None,
            x_r_ratio=None,
            source_contributions=(make_excluded_contribution(),),
            warnings=(warning,),
        )


@pytest.mark.unit
def test_blocked_zero_sequence_path_supports_zero_earth_fault_result() -> None:
    result = make_zero_earth_fault_result()

    zero_sequence = next(
        sequence for sequence in result.sequence_results if sequence.sequence is FaultSequence.ZERO
    )
    assert result.initial_symmetrical_short_circuit_current_ka == Decimal("0")
    assert result.earth_fault_current_ka == Decimal("0")
    assert zero_sequence.available is False
    assert zero_sequence.blocking_reference_codes == ("TX-01",)
