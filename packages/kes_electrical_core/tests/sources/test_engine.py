"""
Unit tests for transformer source-sizing domain engine.
KESE-S2-M4
"""

from decimal import Decimal

import pytest

from kes_electrical_core.loads.models import LoadScenario
from kes_electrical_core.sources.engine import (
    calculate_transformer_sizing,
)
from kes_electrical_core.sources.models import (
    TransformerRedundancyMode,
    TransformerSizingInput,
)
from kes_electrical_core.sources.results import (
    TransformerSizingResult,
    TransformerSizingStatus,
    TransformerSizingWarningCode,
)


def make_sizing_input(
    **overrides: object,
) -> TransformerSizingInput:
    """Create a valid transformer-sizing input."""

    payload: dict[str, object] = {
        "code": "TR-001",
        "name": "Main Transformer",
        "demand_power_kw": Decimal("800"),
        "demand_power_factor": Decimal("0.80"),
        "available_unit_ratings_kva": (
            Decimal("1000"),
            Decimal("1250"),
            Decimal("1600"),
        ),
        "future_growth_factor": Decimal("1"),
        "design_margin_factor": Decimal("1.10"),
        "ambient_derating_factor": Decimal("1"),
        "altitude_derating_factor": Decimal("1"),
        "harmonic_derating_factor": Decimal("1"),
        "duty_units": 1,
        "standby_units": 0,
        "redundancy_mode": TransformerRedundancyMode.NONE,
        "scenario": LoadScenario.NORMAL,
    }

    payload.update(overrides)

    return TransformerSizingInput(
        **payload,  # type: ignore[arg-type]
    )


def warning_codes(
    result: TransformerSizingResult,
) -> set[TransformerSizingWarningCode]:
    """Return controlled warning codes from a result."""

    return {
        warning.code
        for warning in result.warnings
    }


@pytest.mark.unit
def test_selects_smallest_adequate_rating() -> None:
    """Select the smallest adequate standard transformer rating."""

    result = calculate_transformer_sizing(
        make_sizing_input(),
    )

    assert result.base_demand_kva == Decimal("1000.0000")
    assert result.future_demand_kva == Decimal("1000.0000")
    assert result.design_required_kva == Decimal("1100.0000")
    assert (
        result.required_unit_rating_kva
        == Decimal("1100.0000")
    )
    assert result.selected_unit_rating_kva == Decimal("1250")
    assert (
        result.installed_nameplate_capacity_kva
        == Decimal("1250.0000")
    )
    assert (
        result.derated_duty_capacity_kva
        == Decimal("1250.0000")
    )
    assert (
        result.spare_derated_capacity_kva
        == Decimal("150.0000")
    )
    assert result.loading_percent == Decimal("88.0000")
    assert result.status is TransformerSizingStatus.VALID
    assert result.warnings == ()


@pytest.mark.unit
def test_exact_matching_rating_is_selected() -> None:
    """A rating equal to the requirement should be selected."""

    result = calculate_transformer_sizing(
        make_sizing_input(
            available_unit_ratings_kva=(
                Decimal("1000"),
                Decimal("1100"),
                Decimal("1250"),
            ),
        ),
    )

    assert result.selected_unit_rating_kva == Decimal("1100")
    assert result.loading_percent == Decimal("100.0000")


@pytest.mark.unit
def test_rating_selection_uses_unrounded_requirement() -> None:
    """Selection must use the unrounded engineering requirement."""

    result = calculate_transformer_sizing(
        make_sizing_input(
            demand_power_kw=Decimal("880.000008"),
            demand_power_factor=Decimal("0.80"),
            design_margin_factor=Decimal("1"),
            available_unit_ratings_kva=(
                Decimal("1100"),
                Decimal("1250"),
            ),
        ),
    )

    assert (
        result.required_unit_rating_kva
        == Decimal("1100.0000")
    )
    assert result.selected_unit_rating_kva == Decimal("1250")


@pytest.mark.unit
def test_growth_margin_and_derating_are_applied() -> None:
    """Apply growth, margin and all derating factors."""

    result = calculate_transformer_sizing(
        make_sizing_input(
            future_growth_factor=Decimal("1.20"),
            design_margin_factor=Decimal("1.10"),
            ambient_derating_factor=Decimal("0.95"),
            altitude_derating_factor=Decimal("0.98"),
            harmonic_derating_factor=Decimal("0.90"),
            available_unit_ratings_kva=(
                Decimal("1250"),
                Decimal("1600"),
                Decimal("2000"),
            ),
        ),
    )

    assert result.base_demand_kva == Decimal("1000.0000")
    assert result.future_demand_kva == Decimal("1200.0000")
    assert result.design_required_kva == Decimal("1320.0000")
    assert (
        result.combined_derating_factor
        == Decimal("0.8379")
    )
    assert result.selected_unit_rating_kva == Decimal("1600")
    assert result.status is TransformerSizingStatus.WARNING
    assert (
        TransformerSizingWarningCode.DERATING_APPLIED
        in warning_codes(result)
    )


@pytest.mark.unit
def test_high_loading_warning_at_ninety_percent() -> None:
    """Loading at 90 percent should produce a warning."""

    result = calculate_transformer_sizing(
        make_sizing_input(
            demand_power_kw=Decimal("900"),
            demand_power_factor=Decimal("1"),
            design_margin_factor=Decimal("1"),
            available_unit_ratings_kva=(Decimal("1000"),),
        ),
    )

    assert result.loading_percent == Decimal("90.0000")
    assert result.status is TransformerSizingStatus.WARNING
    assert warning_codes(result) == {
        TransformerSizingWarningCode.HIGH_LOADING,
    }


@pytest.mark.unit
def test_low_loading_warning_below_forty_percent() -> None:
    """Loading below 40 percent should produce a warning."""

    result = calculate_transformer_sizing(
        make_sizing_input(
            demand_power_kw=Decimal("300"),
            demand_power_factor=Decimal("1"),
            design_margin_factor=Decimal("1"),
            available_unit_ratings_kva=(Decimal("1000"),),
        ),
    )

    assert result.loading_percent == Decimal("30.0000")
    assert result.status is TransformerSizingStatus.WARNING
    assert warning_codes(result) == {
        TransformerSizingWarningCode.LOW_LOADING,
    }


@pytest.mark.unit
def test_loading_at_forty_percent_is_valid() -> None:
    """Loading at exactly 40 percent should remain valid."""

    result = calculate_transformer_sizing(
        make_sizing_input(
            demand_power_kw=Decimal("400"),
            demand_power_factor=Decimal("1"),
            design_margin_factor=Decimal("1"),
            available_unit_ratings_kva=(Decimal("1000"),),
        ),
    )

    assert result.loading_percent == Decimal("40.0000")
    assert result.status is TransformerSizingStatus.VALID
    assert result.warnings == ()


@pytest.mark.unit
def test_no_solution_for_inadequate_rating_schedule() -> None:
    """Return a controlled result when no rating is adequate."""

    result = calculate_transformer_sizing(
        make_sizing_input(
            demand_power_kw=Decimal("3000"),
        ),
    )

    assert result.status is TransformerSizingStatus.NO_SOLUTION
    assert result.selected_unit_rating_kva is None
    assert result.installed_nameplate_capacity_kva is None
    assert result.derated_duty_capacity_kva is None
    assert result.spare_derated_capacity_kva is None
    assert result.loading_percent is None
    assert warning_codes(result) == {
        TransformerSizingWarningCode
        .NO_STANDARD_RATING_AVAILABLE,
    }


@pytest.mark.unit
def test_no_solution_preserves_derating_warning() -> None:
    """No-solution result should retain derating traceability."""

    result = calculate_transformer_sizing(
        make_sizing_input(
            demand_power_kw=Decimal("3000"),
            ambient_derating_factor=Decimal("0.90"),
        ),
    )

    assert result.status is TransformerSizingStatus.NO_SOLUTION
    assert warning_codes(result) == {
        TransformerSizingWarningCode.DERATING_APPLIED,
        TransformerSizingWarningCode
        .NO_STANDARD_RATING_AVAILABLE,
    }


@pytest.mark.unit
def test_n_plus_one_arrangement_capacity() -> None:
    """N+1 includes one standby unit in installed capacity."""

    result = calculate_transformer_sizing(
        make_sizing_input(
            demand_power_kw=Decimal("1600"),
            demand_power_factor=Decimal("0.80"),
            design_margin_factor=Decimal("1"),
            available_unit_ratings_kva=(
                Decimal("1000"),
                Decimal("1250"),
            ),
            duty_units=2,
            standby_units=1,
            redundancy_mode=(
                TransformerRedundancyMode.N_PLUS_1
            ),
        ),
    )

    assert result.selected_unit_rating_kva == Decimal("1000")
    assert result.duty_units == 2
    assert result.standby_units == 1
    assert result.total_units == 3
    assert (
        result.installed_nameplate_capacity_kva
        == Decimal("3000.0000")
    )
    assert (
        result.derated_duty_capacity_kva
        == Decimal("2000.0000")
    )
    assert (
        result.spare_derated_capacity_kva
        == Decimal("0.0000")
    )


@pytest.mark.unit
def test_two_n_arrangement_capacity() -> None:
    """2N installs equal duty and standby transformer capacity."""

    result = calculate_transformer_sizing(
        make_sizing_input(
            demand_power_kw=Decimal("800"),
            demand_power_factor=Decimal("0.80"),
            design_margin_factor=Decimal("1"),
            available_unit_ratings_kva=(
                Decimal("500"),
                Decimal("630"),
                Decimal("800"),
            ),
            duty_units=2,
            standby_units=2,
            redundancy_mode=TransformerRedundancyMode.TWO_N,
        ),
    )

    assert result.selected_unit_rating_kva == Decimal("500")
    assert result.total_units == 4
    assert (
        result.installed_nameplate_capacity_kva
        == Decimal("2000.0000")
    )
    assert (
        result.derated_duty_capacity_kva
        == Decimal("1000.0000")
    )


@pytest.mark.unit
def test_capacity_values_use_half_up_rounding() -> None:
    """Published capacity values should use ROUND_HALF_UP."""

    result = calculate_transformer_sizing(
        make_sizing_input(
            demand_power_kw=Decimal("800.00005"),
            demand_power_factor=Decimal("1"),
            design_margin_factor=Decimal("1"),
            available_unit_ratings_kva=(Decimal("1000"),),
        ),
    )

    assert result.base_demand_kva == Decimal("800.0001")
    assert result.future_demand_kva == Decimal("800.0001")
    assert result.design_required_kva == Decimal("800.0001")


@pytest.mark.unit
def test_calculation_is_deterministic() -> None:
    """Repeated calculations should produce identical results."""

    sizing_input = make_sizing_input()

    first_result = calculate_transformer_sizing(sizing_input)
    second_result = calculate_transformer_sizing(sizing_input)

    assert first_result == second_result


@pytest.mark.unit
def test_invalid_engine_input_is_rejected() -> None:
    """Engine accepts only TransformerSizingInput records."""

    with pytest.raises(
        TypeError,
        match=(
            "sizing_input must be a "
            "TransformerSizingInput record"
        ),
    ):
        calculate_transformer_sizing(
            "invalid",  # type: ignore[arg-type]
        )
