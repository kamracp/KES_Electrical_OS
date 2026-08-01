"""
Unit tests for Solar PV source-sizing engine.
KESE-S2-M8
"""

from decimal import Decimal

import pytest

from app.domain.electrical.sources.pv_engine import (
    calculate_pv_sizing,
)
from app.domain.electrical.sources.pv_models import (
    PVBatteryConfiguration,
    PVInverterRedundancyMode,
    PVPhaseConfiguration,
    PVSizingInput,
    PVSystemType,
)
from app.domain.electrical.sources.pv_results import (
    PVSizingStatus,
    PVSizingWarningCode,
)


def make_pv_input(
    **overrides: object,
) -> PVSizingInput:
    values: dict[str, object] = {
        "code": "PV-001",
        "name": "Main Solar PV Plant",
        "required_ac_output_kw": Decimal("500"),
        "module_rated_power_wp": Decimal("550"),
        "module_open_circuit_voltage_v": Decimal("49.9"),
        "module_maximum_power_voltage_v": Decimal("41.8"),
        "module_short_circuit_current_a": Decimal("13.9"),
        "module_maximum_power_current_a": Decimal("13.16"),
        "temperature_coefficient_voc_percent_per_c": Decimal("-0.25"),
        "temperature_coefficient_vmp_percent_per_c": Decimal("-0.30"),
        "minimum_design_temperature_c": Decimal("5"),
        "maximum_cell_temperature_c": Decimal("70"),
        "inverter_max_dc_voltage_v": Decimal("1100"),
        "inverter_mppt_min_voltage_v": Decimal("200"),
        "inverter_mppt_max_voltage_v": Decimal("1000"),
        "inverter_max_input_current_per_mppt_a": Decimal("30"),
        "available_inverter_ratings_kw": (
            Decimal("100"),
            Decimal("125"),
            Decimal("250"),
            Decimal("500"),
            Decimal("630"),
        ),
        "target_dc_ac_ratio": Decimal("1.20"),
        "design_irradiance_w_per_m2": Decimal("1000"),
        "dc_efficiency_factor": Decimal("0.97"),
        "ac_efficiency_factor": Decimal("0.98"),
        "future_growth_factor": Decimal("1"),
        "design_margin_factor": Decimal("1"),
        "mppt_count": 10,
        "maximum_strings_per_mppt": 2,
        "duty_inverters": 1,
        "redundant_inverters": 0,
        "system_type": PVSystemType.GRID_TIED,
        "phase_configuration": PVPhaseConfiguration.THREE_PHASE,
        "redundancy_mode": PVInverterRedundancyMode.NONE,
        "battery_configuration": PVBatteryConfiguration.NONE,
        "export_limit_kw": None,
        "dg_coexistence": False,
    }

    values.update(overrides)

    return PVSizingInput(**values)


@pytest.mark.unit
def test_calculate_pv_sizing_selects_inverter() -> None:
    result = calculate_pv_sizing(
        make_pv_input()
    )

    assert result.selected_unit_rating_kw == Decimal("630")
    assert result.duty_inverters == 1
    assert result.total_inverters == 1
    assert result.total_modules > 0
    assert result.modules_per_string > 0
    assert result.total_strings > 0
    assert result.status in {
        PVSizingStatus.VALID,
        PVSizingStatus.WARNING,
    }


@pytest.mark.unit
def test_pv_temperature_voltage_calculation() -> None:
    result = calculate_pv_sizing(
        make_pv_input()
    )

    assert (
        result.cold_corrected_module_voc_v
        > Decimal("49.9")
    )
    assert (
        result.hot_corrected_module_vmp_v
        < Decimal("41.8")
    )
    assert (
        result.cold_string_voc_v
        <= Decimal("1100")
    )
    assert (
        result.hot_string_vmp_v
        >= Decimal("200")
    )


@pytest.mark.unit
def test_no_standard_inverter_rating_returns_no_solution() -> None:
    result = calculate_pv_sizing(
        make_pv_input(
            available_inverter_ratings_kw=(
                Decimal("100"),
                Decimal("250"),
                Decimal("500"),
            ),
        )
    )

    assert result.status is PVSizingStatus.NO_SOLUTION
    assert result.selected_unit_rating_kw is None
    assert any(
        warning.code
        is PVSizingWarningCode.NO_STANDARD_INVERTER_RATING
        for warning in result.warnings
    )


@pytest.mark.unit
def test_export_limit_warning() -> None:
    result = calculate_pv_sizing(
        make_pv_input(
            export_limit_kw=Decimal("450"),
        )
    )

    assert any(
        warning.code
        is PVSizingWarningCode.EXPORT_LIMIT_APPLIED
        for warning in result.warnings
    )


@pytest.mark.unit
def test_dg_coordination_warning() -> None:
    result = calculate_pv_sizing(
        make_pv_input(
            dg_coexistence=True,
        )
    )

    assert any(
        warning.code
        is PVSizingWarningCode.DG_COORDINATION_REQUIRED
        for warning in result.warnings
    )


@pytest.mark.unit
def test_string_current_limit_warning() -> None:
    result = calculate_pv_sizing(
        make_pv_input(
            inverter_max_input_current_per_mppt_a=Decimal("20"),
        )
    )

    assert any(
        warning.code
        is PVSizingWarningCode.STRING_CURRENT_LIMIT
        for warning in result.warnings
    )


@pytest.mark.unit
def test_n_plus_one_inverter_arrangement() -> None:
    result = calculate_pv_sizing(
        make_pv_input(
            required_ac_output_kw=Decimal("200"),
            available_inverter_ratings_kw=(
                Decimal("100"),
                Decimal("125"),
                Decimal("250"),
            ),
            duty_inverters=2,
            redundant_inverters=1,
            redundancy_mode=(
                PVInverterRedundancyMode.N_PLUS_1
            ),
        )
    )

    assert result.duty_inverters == 2
    assert result.redundant_inverters == 1
    assert result.total_inverters == 3
    assert result.selected_unit_rating_kw is not None


@pytest.mark.unit
def test_invalid_input_type_is_rejected() -> None:
    with pytest.raises(
        TypeError,
        match="PVSizingInput record",
    ):
        calculate_pv_sizing(
            "invalid"  # type: ignore[arg-type]
        )
