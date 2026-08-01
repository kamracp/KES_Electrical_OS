"""
Unit tests for Solar PV source-sizing result models.
KESE-S2-M8
"""

from decimal import Decimal

import pytest

from app.domain.electrical.loads.models import LoadScenario
from app.domain.electrical.sources.pv_models import (
    PVBatteryConfiguration,
    PVInverterRedundancyMode,
    PVPhaseConfiguration,
    PVSystemType,
)
from app.domain.electrical.sources.pv_results import (
    PVSizingResult,
    PVSizingStatus,
    PVSizingWarning,
    PVSizingWarningCode,
)


def make_result(
    **overrides: object,
) -> PVSizingResult:
    values: dict[str, object] = {
        "code": "PV-001",
        "name": "Main Solar PV Plant",
        "scenario": LoadScenario.PV,
        "system_type": PVSystemType.GRID_TIED,
        "phase_configuration": PVPhaseConfiguration.THREE_PHASE,
        "redundancy_mode": PVInverterRedundancyMode.NONE,
        "battery_configuration": PVBatteryConfiguration.NONE,
        "required_ac_output_kw": Decimal("500"),
        "future_required_ac_output_kw": Decimal("500"),
        "design_required_ac_output_kw": Decimal("500"),
        "target_dc_ac_ratio": Decimal("1.20"),
        "required_dc_array_capacity_kwp": Decimal("600"),
        "module_rated_power_wp": Decimal("550"),
        "total_modules": 1092,
        "modules_per_string": 20,
        "total_strings": 55,
        "strings_per_mppt": 2,
        "cold_corrected_module_voc_v": Decimal("52.39"),
        "hot_corrected_module_vmp_v": Decimal("36.16"),
        "cold_string_voc_v": Decimal("1047.80"),
        "hot_string_vmp_v": Decimal("723.20"),
        "string_short_circuit_current_a": Decimal("13.90"),
        "required_inverter_capacity_kw": Decimal("500"),
        "required_unit_rating_kw": Decimal("500"),
        "selected_unit_rating_kw": Decimal("500"),
        "duty_inverters": 1,
        "redundant_inverters": 0,
        "total_inverters": 1,
        "installed_duty_capacity_kw": Decimal("500"),
        "total_installed_capacity_kw": Decimal("500"),
        "actual_dc_ac_ratio": Decimal("1.2012"),
        "spare_ac_capacity_kw": Decimal("0"),
        "export_limit_kw": Decimal("450"),
        "dg_coexistence": True,
        "status": PVSizingStatus.WARNING,
        "warnings": (
            PVSizingWarning(
                code=PVSizingWarningCode.EXPORT_LIMIT_APPLIED,
                message="Export limitation is active.",
            ),
        ),
    }

    values.update(overrides)

    return PVSizingResult(**values)


@pytest.mark.unit
def test_create_valid_pv_result() -> None:
    result = make_result()

    assert result.code == "PV-001"
    assert result.status is PVSizingStatus.WARNING
    assert result.total_modules == 1092
    assert result.selected_unit_rating_kw == Decimal("500")


@pytest.mark.unit
def test_result_text_is_trimmed() -> None:
    result = make_result(
        code="  PV-001  ",
        name="  Main Solar PV Plant  ",
    )

    assert result.code == "PV-001"
    assert result.name == "Main Solar PV Plant"


@pytest.mark.unit
def test_warning_message_is_trimmed() -> None:
    warning = PVSizingWarning(
        code=PVSizingWarningCode.DG_COORDINATION_REQUIRED,
        message="  DG coordination study required.  ",
    )

    assert warning.message == "DG coordination study required."


@pytest.mark.unit
def test_duplicate_warning_codes_are_rejected() -> None:
    warning = PVSizingWarning(
        code=PVSizingWarningCode.EXPORT_LIMIT_APPLIED,
        message="Export limitation is active.",
    )

    with pytest.raises(
        ValueError,
        match="warning codes must be unique",
    ):
        make_result(
            warnings=(warning, warning),
        )


@pytest.mark.unit
def test_total_inverters_must_match() -> None:
    with pytest.raises(
        ValueError,
        match="total_inverters must equal",
    ):
        make_result(
            total_inverters=2,
        )


@pytest.mark.unit
def test_no_solution_rejects_selected_values() -> None:
    with pytest.raises(
        ValueError,
        match="must not contain selected capacity values",
    ):
        make_result(
            status=PVSizingStatus.NO_SOLUTION,
        )


@pytest.mark.unit
def test_valid_result_requires_selected_values() -> None:
    with pytest.raises(
        ValueError,
        match="requires complete capacity values",
    ):
        make_result(
            selected_unit_rating_kw=None,
        )


@pytest.mark.unit
def test_warning_code_type_is_validated() -> None:
    with pytest.raises(
        TypeError,
        match="PVSizingWarningCode",
    ):
        PVSizingWarning(
            code="INVALID",  # type: ignore[arg-type]
            message="Invalid warning.",
        )
