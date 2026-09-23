"""
Unit tests for transformer source-sizing domain engine.
KESE-S2-M4
"""

from decimal import Decimal

import pytest

from app.domain.electrical.loads.models import LoadScenario
from app.domain.electrical.sources.engine import (
    calculate_transformer_sizing,
)
from app.domain.electrical.sources.models import (
    TransformerRedundancyMode,
    TransformerSizingInput,
)
from app.domain.electrical.sources.results import (
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

    return {warning.code for warning in result.warnings}


@pytest.mark.unit
def test_selects_smallest_adequate_rating() -> None:
    """Select the smallest adequate standard transformer rating."""

    result = calculate_transformer_sizing(
        make_sizing_input(),
    )

    assert result.base_demand_kva == Decimal("1000.0000")
    assert result.future_demand_kva == Decimal("1000.0000")
    assert result.design_required_kva == Decimal("1100.0000")
    assert result.required_unit_rating_kva == Decimal("1100.0000")
    assert result.selected_unit_rating_kva == Decimal("1250")
    assert result.installed_nameplate_capacity_kva == Decimal("1250.0000")
    assert result.derated_duty_capacity_kva == Decimal("1250.0000")
    assert result.spare_derated_capacity_kva == Decimal("150.0000")
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

    assert result.required_unit_rating_kva == Decimal("1100.0000")
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
    assert result.combined_derating_factor == Decimal("0.8379")
    assert result.selected_unit_rating_kva == Decimal("1600")
    assert result.status is TransformerSizingStatus.WARNING
    assert TransformerSizingWarningCode.DERATING_APPLIED in warning_codes(result)


@pytest.mark.unit
@pytest.mark.parametrize(
    ("demand_power_kw", "expected_loading"),
    [
        (Decimal("900"), Decimal("90.0000")),
        (Decimal("300"), Decimal("30.0000")),
    ],
)
def test_loading_no_longer_warns(
    demand_power_kw: Decimal,
    expected_loading: Decimal,
) -> None:
    """The unreferenced 90 / 40 percent limits are withdrawn (A16 (c), GAP-016)."""

    result = calculate_transformer_sizing(
        make_sizing_input(
            demand_power_kw=demand_power_kw,
            demand_power_factor=Decimal("1"),
            design_margin_factor=Decimal("1"),
            available_unit_ratings_kva=(Decimal("1000"),),
        ),
    )

    assert result.loading_percent == expected_loading
    assert result.status is TransformerSizingStatus.VALID
    assert result.warnings == ()


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
        TransformerSizingWarningCode.NO_STANDARD_RATING_AVAILABLE,
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
        TransformerSizingWarningCode.NO_STANDARD_RATING_AVAILABLE,
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
            redundancy_mode=(TransformerRedundancyMode.N_PLUS_1),
        ),
    )

    assert result.selected_unit_rating_kva == Decimal("1000")
    assert result.duty_units == 2
    assert result.standby_units == 1
    assert result.total_units == 3
    assert result.installed_nameplate_capacity_kva == Decimal("3000.0000")
    assert result.derated_duty_capacity_kva == Decimal("2000.0000")
    assert result.spare_derated_capacity_kva == Decimal("0.0000")


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
    assert result.installed_nameplate_capacity_kva == Decimal("2000.0000")
    assert result.derated_duty_capacity_kva == Decimal("1000.0000")


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
        match=("sizing_input must be a TransformerSizingInput record"),
    ):
        calculate_transformer_sizing(
            "invalid",  # type: ignore[arg-type]
        )


@pytest.mark.unit
def test_every_factor_established_is_valid() -> None:
    """A fully specified study carries no warning at all (A16 (a))."""

    result = calculate_transformer_sizing(make_sizing_input())

    assert result.status is TransformerSizingStatus.VALID
    assert result.warnings == ()


@pytest.mark.unit
@pytest.mark.parametrize(
    ("field_name", "expected_code"),
    [
        (
            "future_growth_factor",
            TransformerSizingWarningCode.GROWTH_FACTOR_NOT_ESTABLISHED,
        ),
        (
            "design_margin_factor",
            TransformerSizingWarningCode.DESIGN_MARGIN_NOT_ESTABLISHED,
        ),
        (
            "ambient_derating_factor",
            TransformerSizingWarningCode.AMBIENT_DERATING_NOT_ESTABLISHED,
        ),
        (
            "altitude_derating_factor",
            TransformerSizingWarningCode.ALTITUDE_DERATING_NOT_ESTABLISHED,
        ),
        (
            "harmonic_derating_factor",
            TransformerSizingWarningCode.HARMONIC_DERATING_NOT_ESTABLISHED,
        ),
    ],
)
def test_a_blank_factor_is_reported_as_not_established(
    field_name: str,
    expected_code: TransformerSizingWarningCode,
) -> None:
    """A blank factor sizes with 1, names itself and needs review (A16 (a))."""

    established = calculate_transformer_sizing(make_sizing_input(**{field_name: Decimal("1")}))

    result = calculate_transformer_sizing(make_sizing_input(**{field_name: None}))

    assert result.status is TransformerSizingStatus.REVIEW_REQUIRED
    assert expected_code in warning_codes(result)
    # The figures are exactly those of a factor of 1; only the status differs.
    assert result.required_nameplate_capacity_kva == established.required_nameplate_capacity_kva
    assert result.selected_unit_rating_kva == established.selected_unit_rating_kva
    assert result.loading_percent == established.loading_percent


@pytest.mark.unit
def test_a_blank_design_margin_no_longer_applies_ten_percent() -> None:
    """The invented 1.10 margin is gone: a blank margin sizes with 1 (A16 (a))."""

    result = calculate_transformer_sizing(
        make_sizing_input(
            demand_power_kw=Decimal("800"),
            demand_power_factor=Decimal("1"),
            design_margin_factor=None,
        ),
    )

    assert result.design_required_kva == Decimal("800.0000")
    # The result records the factor the sizing used, so a reader sees the 1.
    assert result.design_margin_factor == Decimal("1")
    assert result.status is TransformerSizingStatus.REVIEW_REQUIRED
    assert warning_codes(result) == {
        TransformerSizingWarningCode.DESIGN_MARGIN_NOT_ESTABLISHED,
    }


@pytest.mark.unit
def test_several_blank_factors_are_all_named() -> None:
    """Every unestablished factor gets its own warning."""

    result = calculate_transformer_sizing(
        make_sizing_input(
            future_growth_factor=None,
            design_margin_factor=None,
            harmonic_derating_factor=None,
        ),
    )

    assert result.status is TransformerSizingStatus.REVIEW_REQUIRED
    assert warning_codes(result) == {
        TransformerSizingWarningCode.GROWTH_FACTOR_NOT_ESTABLISHED,
        TransformerSizingWarningCode.DESIGN_MARGIN_NOT_ESTABLISHED,
        TransformerSizingWarningCode.HARMONIC_DERATING_NOT_ESTABLISHED,
    }


@pytest.mark.unit
def test_no_adequate_rating_outranks_an_unestablished_factor() -> None:
    """NO_SOLUTION wins: there is no sized result to review (A16 (d))."""

    result = calculate_transformer_sizing(
        make_sizing_input(
            design_margin_factor=None,
            available_unit_ratings_kva=(Decimal("100"),),
        ),
    )

    assert result.status is TransformerSizingStatus.NO_SOLUTION
    assert result.selected_unit_rating_kva is None
    # The unestablished factor is still named, so the reason is not lost.
    assert warning_codes(result) == {
        TransformerSizingWarningCode.NO_STANDARD_RATING_AVAILABLE,
        TransformerSizingWarningCode.DESIGN_MARGIN_NOT_ESTABLISHED,
    }


@pytest.mark.unit
def test_a_derating_warning_alone_is_only_a_warning() -> None:
    """A given derating factor below 1 warns, but needs no review."""

    result = calculate_transformer_sizing(
        make_sizing_input(ambient_derating_factor=Decimal("0.90")),
    )

    assert result.status is TransformerSizingStatus.WARNING
    assert warning_codes(result) == {TransformerSizingWarningCode.DERATING_APPLIED}
