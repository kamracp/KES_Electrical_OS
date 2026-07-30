"""
Unit tests for the pure generator source-sizing engine.
KESE-S2-M6
"""

from decimal import Decimal

import pytest

from app.domain.electrical.sources.generator_engine import (
    calculate_generator_sizing,
)
from app.domain.electrical.sources.generator_models import (
    GeneratorDutyClass,
    GeneratorRedundancyMode,
    GeneratorSizingInput,
)
from app.domain.electrical.sources.generator_results import (
    GeneratorSizingStatus,
    GeneratorSizingWarningCode,
)


def make_generator_input(
    **overrides: object,
) -> GeneratorSizingInput:
    """Create a valid generator-sizing input for engine tests."""

    payload: dict[str, object] = {
        "code": "DG-001",
        "name": "Emergency Generator",
        "steady_state_demand_kw": Decimal("800"),
        "steady_state_power_factor": Decimal("0.80"),
        "transient_step_load_kva": Decimal("0"),
        "transient_allowance_factor": Decimal("1"),
        "future_growth_factor": Decimal("1"),
        "design_margin_factor": Decimal("1.10"),
        "ambient_derating_factor": Decimal("1"),
        "altitude_derating_factor": Decimal("1"),
        "available_unit_ratings_kva": (
            Decimal("1000"),
            Decimal("1250"),
            Decimal("1600"),
            Decimal("2000"),
        ),
        "duty_units": 1,
        "standby_units": 0,
        "duty_class": GeneratorDutyClass.STANDBY,
        "redundancy_mode": GeneratorRedundancyMode.NONE,
    }

    payload.update(overrides)

    return GeneratorSizingInput(
        **payload,  # type: ignore[arg-type]
    )


def warning_codes(
    result: object,
) -> set[GeneratorSizingWarningCode]:
    """Return warning codes from a generator result."""

    return {
        warning.code
        for warning in result.warnings  # type: ignore[attr-defined]
    }


@pytest.mark.unit
def test_calculate_normal_generator_sizing() -> None:
    """Engine should select the smallest adequate unit rating."""

    result = calculate_generator_sizing(
        make_generator_input()
    )

    assert result.steady_state_demand_kva == Decimal("1000.0000")
    assert result.future_steady_state_kva == Decimal("1000.0000")
    assert result.steady_state_required_kva == Decimal("1100.0000")
    assert result.transient_additional_kva == Decimal("0.0000")
    assert result.transient_required_kva == Decimal("1000.0000")
    assert result.governing_required_kva == Decimal("1100.0000")
    assert result.required_unit_rating_kva == Decimal("1100.0000")
    assert result.selected_unit_rating_kva == Decimal("1250")
    assert result.installed_nameplate_capacity_kva == Decimal(
        "1250.0000"
    )
    assert result.derated_duty_capacity_kva == Decimal("1250.0000")
    assert result.spare_derated_capacity_kva == Decimal("150.0000")
    assert result.steady_state_loading_percent == Decimal("88.0000")
    assert result.status is GeneratorSizingStatus.VALID
    assert result.warnings == ()


@pytest.mark.unit
def test_transient_and_derating_requirements() -> None:
    """Transient and site derating should affect selection."""

    result = calculate_generator_sizing(
        make_generator_input(
            transient_step_load_kva=Decimal("350"),
            transient_allowance_factor=Decimal("1.10"),
            future_growth_factor=Decimal("1.10"),
            ambient_derating_factor=Decimal("0.95"),
            altitude_derating_factor=Decimal("0.98"),
            available_unit_ratings_kva=(
                Decimal("1250"),
                Decimal("1600"),
                Decimal("2000"),
            ),
        )
    )

    assert result.future_steady_state_kva == Decimal("1100.0000")
    assert result.steady_state_required_kva == Decimal("1210.0000")
    assert result.transient_additional_kva == Decimal("385.0000")
    assert result.transient_required_kva == Decimal("1485.0000")
    assert result.governing_required_kva == Decimal("1485.0000")
    assert result.combined_derating_factor == Decimal("0.9310")
    assert result.required_nameplate_capacity_kva == Decimal(
        "1595.0591"
    )
    assert result.selected_unit_rating_kva == Decimal("1600")
    assert result.derated_duty_capacity_kva == Decimal("1489.6000")
    assert result.spare_derated_capacity_kva == Decimal("4.6000")
    assert result.steady_state_loading_percent == Decimal("81.2299")
    assert result.status is GeneratorSizingStatus.WARNING

    assert warning_codes(result) == {
        GeneratorSizingWarningCode.DERATING_APPLIED,
        GeneratorSizingWarningCode.TRANSIENT_REQUIREMENT_GOVERNS,
    }


@pytest.mark.unit
def test_small_transient_does_not_govern_selection() -> None:
    """A transient below steady requirement should not govern."""

    result = calculate_generator_sizing(
        make_generator_input(
            transient_step_load_kva=Decimal("50"),
        )
    )

    assert result.transient_required_kva == Decimal("1050.0000")
    assert result.steady_state_required_kva == Decimal("1100.0000")
    assert result.governing_required_kva == Decimal("1100.0000")
    assert (
        GeneratorSizingWarningCode.TRANSIENT_REQUIREMENT_GOVERNS
        not in warning_codes(result)
    )
    assert result.status is GeneratorSizingStatus.VALID


@pytest.mark.unit
def test_no_standard_generator_rating_available() -> None:
    """Inadequate rating schedules should return no solution."""

    result = calculate_generator_sizing(
        make_generator_input(
            steady_state_demand_kw=Decimal("3000"),
            available_unit_ratings_kva=(
                Decimal("1000"),
                Decimal("1250"),
                Decimal("2000"),
            ),
        )
    )

    assert result.steady_state_demand_kva == Decimal("3750.0000")
    assert result.steady_state_required_kva == Decimal("4125.0000")
    assert result.required_unit_rating_kva == Decimal("4125.0000")
    assert result.selected_unit_rating_kva is None
    assert result.installed_nameplate_capacity_kva is None
    assert result.derated_duty_capacity_kva is None
    assert result.spare_derated_capacity_kva is None
    assert result.steady_state_loading_percent is None
    assert result.status is GeneratorSizingStatus.NO_SOLUTION

    assert warning_codes(result) == {
        GeneratorSizingWarningCode.NO_STANDARD_RATING_AVAILABLE,
    }


@pytest.mark.unit
def test_no_solution_preserves_common_warnings() -> None:
    """No-solution results should retain engineering warnings."""

    result = calculate_generator_sizing(
        make_generator_input(
            steady_state_demand_kw=Decimal("1000"),
            steady_state_power_factor=Decimal("1"),
            design_margin_factor=Decimal("1"),
            transient_step_load_kva=Decimal("1000"),
            transient_allowance_factor=Decimal("1"),
            ambient_derating_factor=Decimal("0.90"),
            altitude_derating_factor=Decimal("1"),
            available_unit_ratings_kva=(
                Decimal("1000"),
                Decimal("1500"),
                Decimal("2000"),
            ),
        )
    )

    assert result.status is GeneratorSizingStatus.NO_SOLUTION
    assert result.selected_unit_rating_kva is None

    assert warning_codes(result) == {
        GeneratorSizingWarningCode.DERATING_APPLIED,
        GeneratorSizingWarningCode.TRANSIENT_REQUIREMENT_GOVERNS,
        GeneratorSizingWarningCode.NO_STANDARD_RATING_AVAILABLE,
    }


@pytest.mark.unit
def test_high_generator_loading_warning() -> None:
    """Loading at 90 percent should produce a warning."""

    result = calculate_generator_sizing(
        make_generator_input(
            steady_state_demand_kw=Decimal("900"),
            steady_state_power_factor=Decimal("1"),
            design_margin_factor=Decimal("1"),
            available_unit_ratings_kva=(
                Decimal("1000"),
            ),
        )
    )

    assert result.steady_state_loading_percent == Decimal("90.0000")
    assert result.status is GeneratorSizingStatus.WARNING
    assert warning_codes(result) == {
        GeneratorSizingWarningCode.HIGH_LOADING,
    }


@pytest.mark.unit
def test_low_generator_loading_warning() -> None:
    """Loading below 40 percent should produce a warning."""

    result = calculate_generator_sizing(
        make_generator_input(
            steady_state_demand_kw=Decimal("300"),
            steady_state_power_factor=Decimal("1"),
            design_margin_factor=Decimal("1"),
            available_unit_ratings_kva=(
                Decimal("1000"),
            ),
        )
    )

    assert result.steady_state_loading_percent == Decimal("30.0000")
    assert result.status is GeneratorSizingStatus.WARNING
    assert warning_codes(result) == {
        GeneratorSizingWarningCode.LOW_LOADING,
    }


@pytest.mark.unit
def test_derating_warning_without_transient_warning() -> None:
    """Site derating alone should generate one warning."""

    result = calculate_generator_sizing(
        make_generator_input(
            steady_state_demand_kw=Decimal("600"),
            steady_state_power_factor=Decimal("0.80"),
            ambient_derating_factor=Decimal("0.95"),
            altitude_derating_factor=Decimal("0.98"),
            available_unit_ratings_kva=(
                Decimal("1000"),
                Decimal("1250"),
            ),
        )
    )

    assert result.combined_derating_factor == Decimal("0.9310")
    assert result.required_nameplate_capacity_kva == Decimal(
        "886.1439"
    )
    assert result.selected_unit_rating_kva == Decimal("1000")
    assert result.steady_state_loading_percent == Decimal("88.6144")
    assert result.status is GeneratorSizingStatus.WARNING
    assert warning_codes(result) == {
        GeneratorSizingWarningCode.DERATING_APPLIED,
    }


@pytest.mark.unit
def test_n_plus_one_generator_arrangement() -> None:
    """N+1 should include one standby generator."""

    result = calculate_generator_sizing(
        make_generator_input(
            steady_state_demand_kw=Decimal("1600"),
            steady_state_power_factor=Decimal("0.80"),
            design_margin_factor=Decimal("1"),
            available_unit_ratings_kva=(
                Decimal("1000"),
                Decimal("1250"),
            ),
            duty_units=2,
            standby_units=1,
            redundancy_mode=GeneratorRedundancyMode.N_PLUS_1,
        )
    )

    assert result.selected_unit_rating_kva == Decimal("1000")
    assert result.duty_units == 2
    assert result.standby_units == 1
    assert result.total_units == 3
    assert result.installed_nameplate_capacity_kva == Decimal(
        "3000.0000"
    )
    assert result.derated_duty_capacity_kva == Decimal("2000.0000")
    assert result.spare_derated_capacity_kva == Decimal("0.0000")


@pytest.mark.unit
def test_two_n_generator_arrangement() -> None:
    """Two-N should install standby capacity equal to duty."""

    result = calculate_generator_sizing(
        make_generator_input(
            design_margin_factor=Decimal("1"),
            available_unit_ratings_kva=(
                Decimal("1000"),
                Decimal("1250"),
            ),
            duty_units=1,
            standby_units=1,
            redundancy_mode=GeneratorRedundancyMode.TWO_N,
        )
    )

    assert result.selected_unit_rating_kva == Decimal("1000")
    assert result.duty_units == 1
    assert result.standby_units == 1
    assert result.total_units == 2
    assert result.installed_nameplate_capacity_kva == Decimal(
        "2000.0000"
    )
    assert result.derated_duty_capacity_kva == Decimal("1000.0000")


@pytest.mark.unit
def test_generator_engine_is_deterministic() -> None:
    """Identical inputs should return identical immutable results."""

    sizing_input = make_generator_input(
        transient_step_load_kva=Decimal("150"),
    )

    first_result = calculate_generator_sizing(sizing_input)
    second_result = calculate_generator_sizing(sizing_input)

    assert first_result == second_result
    assert first_result is not second_result


@pytest.mark.unit
def test_generator_engine_does_not_modify_input() -> None:
    """Pure calculation must not modify its input record."""

    sizing_input = make_generator_input()
    original_ratings = sizing_input.available_unit_ratings_kva
    original_code = sizing_input.code

    calculate_generator_sizing(sizing_input)

    assert sizing_input.code == original_code
    assert sizing_input.available_unit_ratings_kva == original_ratings


@pytest.mark.unit
def test_generator_engine_rejects_invalid_input_type() -> None:
    """Engine accepts only GeneratorSizingInput records."""

    with pytest.raises(
        TypeError,
        match=(
            "sizing_input must be a "
            "GeneratorSizingInput record"
        ),
    ):
        calculate_generator_sizing(
            "invalid",  # type: ignore[arg-type]
        )
