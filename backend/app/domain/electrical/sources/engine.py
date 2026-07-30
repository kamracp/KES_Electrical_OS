"""
Pure domain engine for transformer source sizing.
KESE-S2-M4
"""

from dataclasses import dataclass
from decimal import (
    ROUND_HALF_UP,
    Decimal,
    localcontext,
)

from app.domain.electrical.sources.models import (
    TransformerSizingInput,
)
from app.domain.electrical.sources.results import (
    TransformerSizingResult,
    TransformerSizingStatus,
    TransformerSizingWarning,
    TransformerSizingWarningCode,
)


CAPACITY_QUANTUM = Decimal("0.0001")
PERCENT_QUANTUM = Decimal("0.0001")

HIGH_LOADING_LIMIT_PERCENT = Decimal("90")
LOW_LOADING_LIMIT_PERCENT = Decimal("40")


@dataclass(frozen=True, slots=True)
class _RawTransformerSizingValues:
    """Unrounded internal transformer-sizing values."""

    base_demand_kva: Decimal
    future_demand_kva: Decimal
    design_required_kva: Decimal
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
    sizing_input: TransformerSizingInput,
) -> _RawTransformerSizingValues:
    """Calculate unrounded transformer-sizing requirements."""

    with localcontext() as context:
        context.prec = 50

        base_demand_kva = (
            sizing_input.demand_power_kw
            / sizing_input.demand_power_factor
        )

        future_demand_kva = (
            base_demand_kva
            * sizing_input.future_growth_factor
        )

        design_required_kva = (
            future_demand_kva
            * sizing_input.design_margin_factor
        )

        combined_derating_factor = (
            sizing_input.ambient_derating_factor
            * sizing_input.altitude_derating_factor
            * sizing_input.harmonic_derating_factor
        )

        required_nameplate_capacity_kva = (
            design_required_kva
            / combined_derating_factor
        )

        required_unit_rating_kva = (
            required_nameplate_capacity_kva
            / Decimal(sizing_input.duty_units)
        )

    return _RawTransformerSizingValues(
        base_demand_kva=base_demand_kva,
        future_demand_kva=future_demand_kva,
        design_required_kva=design_required_kva,
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
    sizing_input: TransformerSizingInput,
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


def _build_no_solution_result(
    sizing_input: TransformerSizingInput,
    raw_values: _RawTransformerSizingValues,
) -> TransformerSizingResult:
    """Build a controlled result when no rating is adequate."""

    warnings: list[TransformerSizingWarning] = []

    if (
        raw_values.combined_derating_factor
        < Decimal("1")
    ):
        warnings.append(
            TransformerSizingWarning(
                code=(
                    TransformerSizingWarningCode
                    .DERATING_APPLIED
                ),
                message=(
                    "Ambient, altitude or harmonic "
                    "derating has increased the required "
                    "transformer nameplate capacity."
                ),
            )
        )

    warnings.append(
        TransformerSizingWarning(
            code=(
                TransformerSizingWarningCode
                .NO_STANDARD_RATING_AVAILABLE
            ),
            message=(
                "No available transformer unit rating "
                "satisfies the calculated capacity "
                "requirement."
            ),
        )
    )

    return TransformerSizingResult(
        code=sizing_input.code,
        name=sizing_input.name,
        scenario=sizing_input.scenario,
        redundancy_mode=(
            sizing_input.redundancy_mode
        ),
        demand_power_kw=sizing_input.demand_power_kw,
        demand_power_factor=(
            sizing_input.demand_power_factor
        ),
        base_demand_kva=_round_capacity(
            raw_values.base_demand_kva
        ),
        future_growth_factor=(
            sizing_input.future_growth_factor
        ),
        future_demand_kva=_round_capacity(
            raw_values.future_demand_kva
        ),
        design_margin_factor=(
            sizing_input.design_margin_factor
        ),
        design_required_kva=_round_capacity(
            raw_values.design_required_kva
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
        loading_percent=None,
        status=TransformerSizingStatus.NO_SOLUTION,
        warnings=tuple(warnings),
    )


def _build_selected_rating_result(
    sizing_input: TransformerSizingInput,
    raw_values: _RawTransformerSizingValues,
    selected_unit_rating_kva: Decimal,
) -> TransformerSizingResult:
    """Build the result for a successfully selected rating."""

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
            - raw_values.design_required_kva
        )

        loading_percent = (
            raw_values.design_required_kva
            / derated_duty_capacity_kva
            * Decimal("100")
        )

    warnings: list[TransformerSizingWarning] = []

    if (
        raw_values.combined_derating_factor
        < Decimal("1")
    ):
        warnings.append(
            TransformerSizingWarning(
                code=(
                    TransformerSizingWarningCode
                    .DERATING_APPLIED
                ),
                message=(
                    "Ambient, altitude or harmonic "
                    "derating factors were applied."
                ),
            )
        )

    if loading_percent >= HIGH_LOADING_LIMIT_PERCENT:
        warnings.append(
            TransformerSizingWarning(
                code=(
                    TransformerSizingWarningCode
                    .HIGH_LOADING
                ),
                message=(
                    "Calculated transformer duty loading "
                    "is at or above 90 percent."
                ),
            )
        )

    if loading_percent < LOW_LOADING_LIMIT_PERCENT:
        warnings.append(
            TransformerSizingWarning(
                code=(
                    TransformerSizingWarningCode
                    .LOW_LOADING
                ),
                message=(
                    "Calculated transformer duty loading "
                    "is below 40 percent; review possible "
                    "oversizing and operating efficiency."
                ),
            )
        )

    status = (
        TransformerSizingStatus.WARNING
        if warnings
        else TransformerSizingStatus.VALID
    )

    return TransformerSizingResult(
        code=sizing_input.code,
        name=sizing_input.name,
        scenario=sizing_input.scenario,
        redundancy_mode=(
            sizing_input.redundancy_mode
        ),
        demand_power_kw=sizing_input.demand_power_kw,
        demand_power_factor=(
            sizing_input.demand_power_factor
        ),
        base_demand_kva=_round_capacity(
            raw_values.base_demand_kva
        ),
        future_growth_factor=(
            sizing_input.future_growth_factor
        ),
        future_demand_kva=_round_capacity(
            raw_values.future_demand_kva
        ),
        design_margin_factor=(
            sizing_input.design_margin_factor
        ),
        design_required_kva=_round_capacity(
            raw_values.design_required_kva
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
        loading_percent=_round_percent(
            loading_percent
        ),
        status=status,
        warnings=tuple(warnings),
    )


def calculate_transformer_sizing(
    sizing_input: TransformerSizingInput,
) -> TransformerSizingResult:
    """
    Calculate and select a transformer source arrangement.

    The function is pure and does not access a database, API,
    environment configuration or manufacturer service.
    """

    if not isinstance(
        sizing_input,
        TransformerSizingInput,
    ):
        raise TypeError(
            "sizing_input must be a "
            "TransformerSizingInput record"
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
    "calculate_transformer_sizing",
]