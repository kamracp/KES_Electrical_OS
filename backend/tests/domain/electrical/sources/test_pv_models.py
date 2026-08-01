"""
Unit tests for Solar PV source-sizing input models.
KESE-S2-M8
"""

from decimal import Decimal

import pytest

from app.domain.electrical.loads.models import LoadScenario
from app.domain.electrical.sources.pv_models import (
    PVBatteryConfiguration,
    PVInverterRedundancyMode,
    PVPhaseConfiguration,
    PVSizingInput,
    PVSystemType,
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
        "export_limit_kw": Decimal("450"),
        "dg_coexistence": True,
        "scenario": LoadScenario.PV,
        "notes": "Main rooftop and ground-mounted PV plant.",
    }

    values.update(overrides)

    return PVSizingInput(**values)


@pytest.mark.unit
def test_create_valid_pv_input() -> None:
    sizing_input = make_pv_input()

    assert sizing_input.code == "PV-001"
    assert sizing_input.required_ac_output_kw == Decimal("500")
    assert sizing_input.system_type is PVSystemType.GRID_TIED
    assert sizing_input.scenario is LoadScenario.PV
    assert sizing_input.dg_coexistence is True


@pytest.mark.unit
def test_pv_text_fields_are_trimmed() -> None:
    sizing_input = make_pv_input(
        code="  PV-001  ",
        name="  Main Solar PV Plant  ",
        notes="  Approved basis  ",
    )

    assert sizing_input.code == "PV-001"
    assert sizing_input.name == "Main Solar PV Plant"
    assert sizing_input.notes == "Approved basis"


@pytest.mark.unit
def test_float_engineering_input_is_rejected() -> None:
    with pytest.raises(
        TypeError,
        match="required_ac_output_kw must be a Decimal",
    ):
        make_pv_input(
            required_ac_output_kw=500.0,
        )


@pytest.mark.unit
def test_invalid_temperature_order_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="minimum_design_temperature_c must be below",
    ):
        make_pv_input(
            minimum_design_temperature_c=Decimal("70"),
            maximum_cell_temperature_c=Decimal("70"),
        )


@pytest.mark.unit
def test_positive_temperature_coefficient_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="must not be positive",
    ):
        make_pv_input(
            temperature_coefficient_voc_percent_per_c=Decimal("0.25"),
        )


@pytest.mark.unit
def test_empty_inverter_rating_schedule_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="at least one available inverter rating",
    ):
        make_pv_input(
            available_inverter_ratings_kw=(),
        )


@pytest.mark.unit
def test_duplicate_inverter_ratings_are_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="must be unique",
    ):
        make_pv_input(
            available_inverter_ratings_kw=(
                Decimal("100"),
                Decimal("100"),
            ),
        )


@pytest.mark.unit
def test_unsorted_inverter_ratings_are_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="ascending order",
    ):
        make_pv_input(
            available_inverter_ratings_kw=(
                Decimal("250"),
                Decimal("100"),
            ),
        )


@pytest.mark.unit
def test_invalid_mppt_voltage_window_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="MPPT maximum voltage must not exceed",
    ):
        make_pv_input(
            inverter_mppt_max_voltage_v=Decimal("1200"),
        )


@pytest.mark.unit
def test_n_plus_one_requires_one_redundant_inverter() -> None:
    with pytest.raises(
        ValueError,
        match="exactly one redundant inverter",
    ):
        make_pv_input(
            redundancy_mode=PVInverterRedundancyMode.N_PLUS_1,
            redundant_inverters=0,
        )


@pytest.mark.unit
def test_two_n_requires_equal_redundant_inverters() -> None:
    with pytest.raises(
        ValueError,
        match="to equal duty_inverters",
    ):
        make_pv_input(
            redundancy_mode=PVInverterRedundancyMode.TWO_N,
            duty_inverters=2,
            redundant_inverters=1,
        )


@pytest.mark.unit
def test_negative_export_limit_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="export_limit_kw must not be negative",
    ):
        make_pv_input(
            export_limit_kw=Decimal("-1"),
        )
