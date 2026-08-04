"""
Unit tests for cable sizing and ampacity result models.
KESE-S2-M13
"""

from dataclasses import FrozenInstanceError
from decimal import Decimal

import pytest

from app.domain.electrical.cable.cable_results import (
    CableAmpacityResult,
    CableCheckStatus,
    CableConductorSizingResult,
    CableEngineeringWarning,
    CableShortCircuitResult,
    CableSizingResult,
    CableSizingStatus,
    CableVoltageDropResult,
    CableWarningCode,
)


def make_ampacity(**overrides: object) -> CableAmpacityResult:
    values: dict[str, object] = {
        "tabulated_ampacity_a_per_run": Decimal("300"),
        "combined_derating_factor": Decimal("0.75"),
        "derated_ampacity_a_per_run": Decimal("225"),
        "parallel_runs": 2,
        "total_installed_ampacity_a": Decimal("450"),
        "design_current_a": Decimal("400"),
        "required_tabulated_ampacity_a_per_run": Decimal("266.6667"),
        "utilization_ratio": Decimal("0.8889"),
        "status": CableCheckStatus.PASS,
    }
    values.update(overrides)
    return CableAmpacityResult(**values)


def make_voltage_drop(**overrides: object) -> CableVoltageDropResult:
    values: dict[str, object] = {
        "resistance_ohm_per_km": Decimal("0.124"),
        "reactance_ohm_per_km": Decimal("0.075"),
        "voltage_drop_v": Decimal("8.20"),
        "voltage_drop_percent": Decimal("1.976"),
        "allowable_voltage_drop_percent": Decimal("3"),
        "status": CableCheckStatus.PASS,
    }
    values.update(overrides)
    return CableVoltageDropResult(**values)


def make_short_circuit(**overrides: object) -> CableShortCircuitResult:
    values: dict[str, object] = {
        "fault_current_ka": Decimal("25"),
        "fault_duration_s": Decimal("1"),
        "material_constant_k": Decimal("143"),
        "required_area_mm2": Decimal("174.825"),
        "selected_area_mm2": Decimal("185"),
        "withstand_current_ka": Decimal("26.455"),
        "status": CableCheckStatus.PASS,
    }
    values.update(overrides)
    return CableShortCircuitResult(**values)


def make_conductor(**overrides: object) -> CableConductorSizingResult:
    values: dict[str, object] = {
        "phase_area_mm2": Decimal("185"),
        "neutral_area_mm2": Decimal("185"),
        "protective_area_mm2": Decimal("95"),
        "parallel_runs": 2,
        "phase_conductors_per_run": 3,
        "neutral_status": CableCheckStatus.PASS,
        "protective_status": CableCheckStatus.PASS,
    }
    values.update(overrides)
    return CableConductorSizingResult(**values)


def make_sizing_result(**overrides: object) -> CableSizingResult:
    values: dict[str, object] = {
        "study_code": "CBL-FDR-01",
        "status": CableSizingStatus.COMPLIANT,
        "conductor": make_conductor(),
        "ampacity": make_ampacity(),
        "voltage_drop": make_voltage_drop(),
        "short_circuit": make_short_circuit(),
        "warnings": (),
        "governing_criterion": "SHORT_CIRCUIT_WITHSTAND",
        "standard_reference": "IEC 60364-5-52",
        "ampacity_reference": "IEC 60287",
    }
    values.update(overrides)
    return CableSizingResult(**values)


@pytest.mark.unit
def test_create_compliant_cable_sizing_result() -> None:
    result = make_sizing_result()

    assert result.status is CableSizingStatus.COMPLIANT
    assert result.conductor is not None
    assert result.conductor.phase_area_mm2 == Decimal("185")
    assert result.ampacity is not None
    assert result.ampacity.total_installed_ampacity_a == Decimal("450")


@pytest.mark.unit
def test_result_models_are_immutable() -> None:
    result = make_ampacity()

    with pytest.raises(FrozenInstanceError):
        result.design_current_a = Decimal("500")


@pytest.mark.unit
def test_engineering_warning_is_normalized() -> None:
    warning = CableEngineeringWarning(
        code=CableWarningCode.HIGH_TOTAL_DERATING,
        message="  Combined derating factor is low  ",
        field_name="  combined_derating_factor  ",
    )

    assert warning.message == "Combined derating factor is low"
    assert warning.field_name == "combined_derating_factor"


@pytest.mark.unit
def test_invalid_warning_code_type_is_rejected() -> None:
    with pytest.raises(TypeError, match="code must be a CableWarningCode"):
        CableEngineeringWarning(
            code="HIGH_TOTAL_DERATING",
            message="Combined derating factor is low",
        )


@pytest.mark.unit
def test_ampacity_result_rejects_invalid_parallel_runs() -> None:
    with pytest.raises(ValueError, match="parallel_runs must be at least 1"):
        make_ampacity(parallel_runs=0)

    with pytest.raises(TypeError, match="parallel_runs must be an integer"):
        make_ampacity(parallel_runs=True)


@pytest.mark.unit
def test_ampacity_result_rejects_not_applicable_status() -> None:
    with pytest.raises(ValueError, match="must be PASS or FAIL"):
        make_ampacity(status=CableCheckStatus.NOT_APPLICABLE)


@pytest.mark.unit
def test_voltage_drop_result_allows_zero_drop() -> None:
    result = make_voltage_drop(
        voltage_drop_v=Decimal("0"),
        voltage_drop_percent=Decimal("0"),
    )

    assert result.voltage_drop_v == Decimal("0")
    assert result.status is CableCheckStatus.PASS


@pytest.mark.unit
def test_voltage_drop_limit_cannot_exceed_100_percent() -> None:
    with pytest.raises(ValueError, match="must not exceed 100"):
        make_voltage_drop(allowable_voltage_drop_percent=Decimal("101"))


@pytest.mark.unit
def test_short_circuit_values_must_be_provided_together() -> None:
    with pytest.raises(ValueError, match="must be provided together"):
        make_short_circuit(withstand_current_ka=None)


@pytest.mark.unit
def test_short_circuit_not_applicable_result_is_valid() -> None:
    result = make_short_circuit(
        fault_current_ka=None,
        fault_duration_s=None,
        material_constant_k=None,
        required_area_mm2=None,
        withstand_current_ka=None,
        status=CableCheckStatus.NOT_APPLICABLE,
    )

    assert result.status is CableCheckStatus.NOT_APPLICABLE
    assert result.required_area_mm2 is None


@pytest.mark.unit
def test_missing_short_circuit_values_require_not_applicable_status() -> None:
    with pytest.raises(ValueError, match="require NOT_APPLICABLE"):
        make_short_circuit(
            fault_current_ka=None,
            fault_duration_s=None,
            material_constant_k=None,
            required_area_mm2=None,
            withstand_current_ka=None,
            status=CableCheckStatus.PASS,
        )


@pytest.mark.unit
def test_missing_neutral_area_requires_not_applicable_status() -> None:
    with pytest.raises(ValueError, match="missing neutral area requires"):
        make_conductor(neutral_area_mm2=None)

    result = make_conductor(
        neutral_area_mm2=None,
        neutral_status=CableCheckStatus.NOT_APPLICABLE,
    )
    assert result.neutral_status is CableCheckStatus.NOT_APPLICABLE


@pytest.mark.unit
def test_selected_protective_area_requires_applicable_status() -> None:
    with pytest.raises(ValueError, match="selected protective area requires"):
        make_conductor(protective_status=CableCheckStatus.NOT_APPLICABLE)


@pytest.mark.unit
def test_duplicate_warning_codes_are_rejected() -> None:
    warning = CableEngineeringWarning(
        code=CableWarningCode.HIGH_TOTAL_DERATING,
        message="Combined derating factor is low",
    )

    with pytest.raises(ValueError, match="warning codes must be unique"):
        make_sizing_result(warnings=(warning, warning))


@pytest.mark.unit
def test_no_standard_size_result_requires_warning() -> None:
    with pytest.raises(ValueError, match="requires its warning code"):
        make_sizing_result(
            status=CableSizingStatus.NO_STANDARD_SIZE_AVAILABLE,
            conductor=None,
            ampacity=None,
            voltage_drop=None,
            short_circuit=None,
        )


@pytest.mark.unit
def test_create_no_standard_size_result() -> None:
    warning = CableEngineeringWarning(
        code=CableWarningCode.NO_STANDARD_SIZE_AVAILABLE,
        message="No approved standard size satisfies the design duty",
    )
    result = make_sizing_result(
        status=CableSizingStatus.NO_STANDARD_SIZE_AVAILABLE,
        conductor=None,
        ampacity=None,
        voltage_drop=None,
        short_circuit=None,
        warnings=(warning,),
        governing_criterion=None,
    )

    assert result.status is CableSizingStatus.NO_STANDARD_SIZE_AVAILABLE
    assert result.conductor is None
    assert result.warnings == (warning,)


@pytest.mark.unit
def test_detailed_results_required_for_compliant_status() -> None:
    with pytest.raises(ValueError, match="require all detailed results"):
        make_sizing_result(voltage_drop=None)


@pytest.mark.unit
def test_compliant_result_rejects_failed_check() -> None:
    with pytest.raises(ValueError, match="cannot contain a failed"):
        make_sizing_result(
            voltage_drop=make_voltage_drop(status=CableCheckStatus.FAIL),
        )


@pytest.mark.unit
def test_non_compliant_result_accepts_failed_check_and_warning() -> None:
    warning = CableEngineeringWarning(
        code=CableWarningCode.VOLTAGE_DROP_EXCEEDED,
        message="Calculated voltage drop exceeds the allowable limit",
        field_name="voltage_drop_percent",
    )
    result = make_sizing_result(
        status=CableSizingStatus.NON_COMPLIANT,
        voltage_drop=make_voltage_drop(status=CableCheckStatus.FAIL),
        warnings=(warning,),
        governing_criterion="VOLTAGE_DROP",
    )

    assert result.status is CableSizingStatus.NON_COMPLIANT
    assert result.voltage_drop is not None
    assert result.voltage_drop.status is CableCheckStatus.FAIL
    assert result.warnings == (warning,)
