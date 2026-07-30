"""
Pure domain engine for generator source sizing.
KESE-S2-M6
"""

from dataclasses import dataclass
from decimal import (
    ROUND_HALF_UP,
    Decimal,
    localcontext,
)

from app.domain.electrical.sources.generator_models import (
    GeneratorSizingInput,
)
from app.domain.electrical.sources.generator_results import (
    GeneratorSizingResult,
    GeneratorSizingStatus,
    GeneratorSizingWarning,
    GeneratorSizingWarningCode,
)


CAPACITY_QUANTUM = Decimal("0.0001")
PERCENT_QUANTUM = Decimal("0.0001")

HIGH_LOADING_LIMIT_PERCENT = Decimal("90")
LOW_LOADING_LIMIT_PERCENT = Decimal("40")


@dataclass(frozen=True, slots=True)
class _RawGeneratorSizingValues:
    """Unrounded internal generator-sizing values."""

    steady_state_demand_kva: Decimal
    future_steady_state_kva: Decimal
    steady_state_required_kva: Decimal

    transient_additional_kva: Decimal
    transient_required_kva: Decimal

    governing_required_kva: Decimal

    combined_derating_factor: Decimal
    required_nameplate_capacity_kva: Decimal
    required_unit_rating_kva: Decimal


def _round_capacity(
    value: Decimal,
) -> Decimal:
    """Round a capacity value to four decimal places."""

    return value.quantize(
        CAPACITY_QUANTUM,
        rounding=ROUND_HALF_UP,
    )


def _round_percent(
    value: Decimal,
) -> Decimal:
    """Round a percentage value to four decimal places."""

    return value.quantize(
        PERCENT_QUANTUM,
        rounding=ROUND_HALF_UP,
    )


def _calculate_raw_values(
    sizing_input: GeneratorSizingInput,
) -> _RawGeneratorSizingValues:
    """Calculate unrounded generator-sizing requirements."""

    with localcontext() as context:
        context.prec = 50

        steady_state_demand_kva = (
            sizing_input.steady_state_demand_kw
            / sizing_input.steady_state_power_factor
        )

        future_steady_state_kva = (
            steady_state_demand_kva
            * sizing_input.future_growth_factor
        )

        steady_state_required_kva = (
            future_steady_state_kva
            * sizing_input.design_margin_factor
        )

        transient_additional_kva = (
            sizing_input.transient_step_load_kva
            * sizing_input.transient_allowance_factor
        )

        transient_required_kva = (
            future_steady_state_kva
            + transient_additional_kva
        )

        governing_required_kva = max(
            steady_state_required_kva,
            transient_required_kva,
        )

        combined_derating_factor = (
            sizing_input.ambient_derating_factor
            * sizing_input.altitude_derating_factor
        )

        required_nameplate_capacity_kva = (
            governing_required_kva
            / combined_derating_factor
        )

        required_unit_rating_kva = (
            required_nameplate_capacity_kva
            / Decimal(sizing_input.duty_units)
        )

    return _RawGeneratorSizingValues(
        steady_state_demand_kva=(
            steady_state_demand_kva
        ),
        future_steady_state_kva=(
            future_steady_state_kva
        ),
        steady_state_required_kva=(
            steady_state_required_kva
        ),
        transient_additional_kva=(
            transient_additional_kva
        ),
        transient_required_kva=(
            transient_required_kva
        ),
        governing_required_kva=(
            governing_required_kva
        ),
        combined_derating_factor=(
            combined_derating_factor
        ),
        required_nameplate_capacity_kva=(
            required_nameplate_capacity_kva
        ),
        required_unit_rating_kva=(
            required_unit_rating_kva
        ),
    )


def _select_unit_rating(
    sizing_input: GeneratorSizingInput,
    required_unit_rating_kva: Decimal,
) -> Decimal | None:
    """Select the smallest available adequate unit rating."""

    return next(
        (
            rating
            for rating
            in sizing_input.available_unit_ratings_kva
            if rating >= required_unit_rating_kva
        ),
        None,
    )


def _build_common_warnings(
    raw_values: _RawGeneratorSizingValues,
) -> list[GeneratorSizingWarning]:
    """Build warnings common to selected and no-solution results."""

    warnings: list[GeneratorSizingWarning] = []

    if (
        raw_values.combined_derating_factor
        < Decimal("1")
    ):
        warnings.append(
            GeneratorSizingWarning(
                code=(
                    GeneratorSizingWarningCode
                    .DERATING_APPLIED
                ),
                message=(
                    "Ambient or altitude derating has "
                    "increased the required generator "
                    "nameplate capacity."
                ),
            )
        )

    if (
        raw_values.transient_required_kva
        > raw_values.steady_state_required_kva
    ):
        warnings.append(
            GeneratorSizingWarning(
                code=(
                    GeneratorSizingWarningCode
                    .TRANSIENT_REQUIREMENT_GOVERNS
                ),
                message=(
                    "The transient or starting-load "
                    "requirement governs generator selection."
                ),
            )
        )

    return warnings


def _build_no_solution_result(
    sizing_input: GeneratorSizingInput,
    raw_values: _RawGeneratorSizingValues,
) -> GeneratorSizingResult:
    """Build a controlled result when no rating is adequate."""

    warnings = _build_common_warnings(
        raw_values
    )

    warnings.append(
        GeneratorSizingWarning(
            code=(
                GeneratorSizingWarningCode
                .NO_STANDARD_RATING_AVAILABLE
            ),
            message=(
                "No available generator unit rating "
                "satisfies the calculated capacity "
                "requirement."
            ),
        )
    )

    return GeneratorSizingResult(
        code=sizing_input.code,
        name=sizing_input.name,
        scenario=sizing_input.scenario,
        duty_class=sizing_input.duty_class,
        redundancy_mode=(
            sizing_input.redundancy_mode
        ),
        steady_state_demand_kw=(
            sizing_input.steady_state_demand_kw
        ),
        steady_state_power_factor=(
            sizing_input.steady_state_power_factor
        ),
        steady_state_demand_kva=_round_capacity(
            raw_values.steady_state_demand_kva
        ),
        future_growth_factor=(
            sizing_input.future_growth_factor
        ),
        future_steady_state_kva=_round_capacity(
            raw_values.future_steady_state_kva
        ),
        design_margin_factor=(
            sizing_input.design_margin_factor
        ),
        steady_state_required_kva=_round_capacity(
            raw_values.steady_state_required_kva
        ),
        transient_step_load_kva=(
            sizing_input.transient_step_load_kva
        ),
        transient_allowance_factor=(
            sizing_input.transient_allowance_factor
        ),
        transient_additional_kva=_round_capacity(
            raw_values.transient_additional_kva
        ),
        transient_required_kva=_round_capacity(
            raw_values.transient_required_kva
        ),
        governing_required_kva=_round_capacity(
            raw_values.governing_required_kva
        ),
        combined_derating_factor=_round_capacity(
            raw_values.combined_derating_factor
        ),
        required_nameplate_capacity_kva=(
            _round_capacity(
                raw_values
                .required_nameplate_capacity_kva
            )
        ),
        duty_units=sizing_input.duty_units,
        standby_units=sizing_input.standby_units,
        total_units=(
            sizing_input.duty_units
            + sizing_input.standby_units
        ),
        required_unit_rating_kva=_round_capacity(
            raw_values.required_unit_rating_kva
        ),
        selected_unit_rating_kva=None,
        installed_nameplate_capacity_kva=None,
        derated_duty_capacity_kva=None,
        spare_derated_capacity_kva=None,
        steady_state_loading_percent=None,
        status=GeneratorSizingStatus.NO_SOLUTION,
        warnings=tuple(warnings),
    )


def _build_selected_rating_result(
    sizing_input: GeneratorSizingInput,
    raw_values: _RawGeneratorSizingValues,
    selected_unit_rating_kva: Decimal,
) -> GeneratorSizingResult:
    """Build a result for a successfully selected rating."""

    with localcontext() as context:
        context.prec = 50

        total_units = (
            sizing_input.duty_units
            + sizing_input.standby_units
        )

        installed_nameplate_capacity_kva = (
            selected_unit_rating_kva
            * Decimal(total_units)
        )

        derated_duty_capacity_kva = (
            selected_unit_rating_kva
            * Decimal(sizing_input.duty_units)
            * raw_values.combined_derating_factor
        )

        spare_derated_capacity_kva = (
            derated_duty_capacity_kva
            - raw_values.governing_required_kva
        )

        steady_state_loading_percent = (
            raw_values.steady_state_required_kva
            / derated_duty_capacity_kva
            * Decimal("100")
        )

    warnings = _build_common_warnings(
        raw_values
    )

    if (
        steady_state_loading_percent
        >= HIGH_LOADING_LIMIT_PERCENT
    ):
        warnings.append(
            GeneratorSizingWarning(
                code=(
                    GeneratorSizingWarningCode
                    .HIGH_LOADING
                ),
                message=(
                    "Calculated steady-state generator "
                    "loading is at or above 90 percent."
                ),
            )
        )

    if (
        steady_state_loading_percent
        < LOW_LOADING_LIMIT_PERCENT
    ):
        warnings.append(
            GeneratorSizingWarning(
                code=(
                    GeneratorSizingWarningCode
                    .LOW_LOADING
                ),
                message=(
                    "Calculated steady-state generator "
                    "loading is below 40 percent; review "
                    "possible oversizing and operating "
                    "efficiency."
                ),
            )
        )

    status = (
        GeneratorSizingStatus.WARNING
        if warnings
        else GeneratorSizingStatus.VALID
    )

    return GeneratorSizingResult(
        code=sizing_input.code,
        name=sizing_input.name,
        scenario=sizing_input.scenario,
        duty_class=sizing_input.duty_class,
        redundancy_mode=(
            sizing_input.redundancy_mode
        ),
        steady_state_demand_kw=(
            sizing_input.steady_state_demand_kw
        ),
        steady_state_power_factor=(
            sizing_input.steady_state_power_factor
        ),
        steady_state_demand_kva=_round_capacity(
            raw_values.steady_state_demand_kva
        ),
        future_growth_factor=(
            sizing_input.future_growth_factor
        ),
        future_steady_state_kva=_round_capacity(
            raw_values.future_steady_state_kva
        ),
        design_margin_factor=(
            sizing_input.design_margin_factor
        ),
        steady_state_required_kva=_round_capacity(
            raw_values.steady_state_required_kva
        ),
        transient_step_load_kva=(
            sizing_input.transient_step_load_kva
        ),
        transient_allowance_factor=(
            sizing_input.transient_allowance_factor
        ),
        transient_additional_kva=_round_capacity(
            raw_values.transient_additional_kva
        ),
        transient_required_kva=_round_capacity(
            raw_values.transient_required_kva
        ),
        governing_required_kva=_round_capacity(
            raw_values.governing_required_kva
        ),
        combined_derating_factor=_round_capacity(
            raw_values.combined_derating_factor
        ),
        required_nameplate_capacity_kva=(
            _round_capacity(
                raw_values
                .required_nameplate_capacity_kva
            )
        ),
        duty_units=sizing_input.duty_units,
        standby_units=sizing_input.standby_units,
        total_units=total_units,
        required_unit_rating_kva=_round_capacity(
            raw_values.required_unit_rating_kva
        ),
        selected_unit_rating_kva=(
            selected_unit_rating_kva
        ),
        installed_nameplate_capacity_kva=(
            _round_capacity(
                installed_nameplate_capacity_kva
            )
        ),
        derated_duty_capacity_kva=_round_capacity(
            derated_duty_capacity_kva
        ),
        spare_derated_capacity_kva=_round_capacity(
            spare_derated_capacity_kva
        ),
        steady_state_loading_percent=_round_percent(
            steady_state_loading_percent
        ),
        status=status,
        warnings=tuple(warnings),
    )


def calculate_generator_sizing(
    sizing_input: GeneratorSizingInput,
) -> GeneratorSizingResult:
    """
    Calculate and select a generator source arrangement.

    The function is pure and does not access a database, API,
    environment configuration or manufacturer service.
    """

    if not isinstance(
        sizing_input,
        GeneratorSizingInput,
    ):
        raise TypeError(
            "sizing_input must be a "
            "GeneratorSizingInput record"
        )

    raw_values = _calculate_raw_values(
        sizing_input
    )

    selected_unit_rating_kva = (
        _select_unit_rating(
            sizing_input,
            raw_values.required_unit_rating_kva,
        )
    )

    if selected_unit_rating_kva is None:
        return _build_no_solution_result(
            sizing_input,
            raw_values,
        )

    return _build_selected_rating_result(
        sizing_input,
        raw_values,
        selected_unit_rating_kva,
    )


__all__ = [
    "calculate_generator_sizing",
]
