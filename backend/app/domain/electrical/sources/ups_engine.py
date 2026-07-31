"""
UPS source-sizing calculation engine.

Mission: KESE-S2-M7
"""

from decimal import Decimal, ROUND_HALF_UP

from app.domain.electrical.sources.ups_models import UPSSizingInput
from app.domain.electrical.sources.ups_results import (
    UPSSizingResult,
    UPSSizingStatus,
)


TWO_DECIMAL_PLACES = Decimal("0.01")


def _round_decimal(value: Decimal) -> Decimal:
    """Round engineering outputs to two decimal places."""

    return value.quantize(
        TWO_DECIMAL_PLACES,
        rounding=ROUND_HALF_UP,
    )


def _select_standard_rating(
    required_rating_kva: Decimal,
    available_ratings_kva: tuple[Decimal, ...],
) -> Decimal | None:
    """Select the smallest standard rating meeting the requirement."""

    for rating in available_ratings_kva:
        if rating >= required_rating_kva:
            return rating

    return None


def calculate_ups_sizing(
    sizing_input: UPSSizingInput,
) -> UPSSizingResult:
    """
    Calculate UPS source capacity and select a standard module rating.

    Calculation basis:

    base_load_kva
        = critical_load_kw / load_power_factor

    design_load_kva
        = base_load_kva
        × future_growth_factor
        × design_margin_factor
        × inverter_overload_factor

    derated_required_capacity_kva
        = design_load_kva
        / ambient_derating_factor
        / altitude_derating_factor

    required_capacity_per_duty_module_kva
        = derated_required_capacity_kva / duty_modules

    estimated_output_energy_kwh
        = critical_load_kw × runtime_hours

    estimated_dc_energy_kwh
        = estimated_output_energy_kwh / ups_efficiency
    """

    if not isinstance(sizing_input, UPSSizingInput):
        raise TypeError(
            "sizing_input must be a UPSSizingInput instance"
        )

    base_load_kva = (
        sizing_input.critical_load_kw
        / sizing_input.load_power_factor
    )

    design_load_kva = (
        base_load_kva
        * sizing_input.future_growth_factor
        * sizing_input.design_margin_factor
        * sizing_input.inverter_overload_factor
    )

    combined_derating_factor = (
        sizing_input.ambient_derating_factor
        * sizing_input.altitude_derating_factor
    )

    derated_required_capacity_kva = (
        design_load_kva
        / combined_derating_factor
    )

    required_capacity_per_duty_module_kva = (
        derated_required_capacity_kva
        / Decimal(sizing_input.duty_modules)
    )

    selected_unit_rating_kva = _select_standard_rating(
        required_capacity_per_duty_module_kva,
        sizing_input.available_unit_ratings_kva,
    )

    total_installed_modules = (
        sizing_input.duty_modules
        + sizing_input.redundant_modules
    )

    runtime_hours = (
        sizing_input.required_runtime_minutes
        / Decimal("60")
    )

    estimated_output_energy_kwh = (
        sizing_input.critical_load_kw
        * runtime_hours
    )

    estimated_dc_energy_kwh = (
        estimated_output_energy_kwh
        / sizing_input.ups_efficiency
    )

    if selected_unit_rating_kva is None:
        return UPSSizingResult(
            code=sizing_input.code,
            name=sizing_input.name,
            critical_load_kw=_round_decimal(
                sizing_input.critical_load_kw
            ),
            base_load_kva=_round_decimal(
                base_load_kva
            ),
            design_load_kva=_round_decimal(
                design_load_kva
            ),
            derated_required_capacity_kva=_round_decimal(
                derated_required_capacity_kva
            ),
            required_capacity_per_duty_module_kva=_round_decimal(
                required_capacity_per_duty_module_kva
            ),
            selected_unit_rating_kva=None,
            duty_modules=sizing_input.duty_modules,
            redundant_modules=sizing_input.redundant_modules,
            total_installed_modules=total_installed_modules,
            duty_capacity_kva=None,
            total_installed_capacity_kva=None,
            spare_capacity_kva=None,
            loading_percent=None,
            required_runtime_minutes=_round_decimal(
                sizing_input.required_runtime_minutes
            ),
            estimated_output_energy_kwh=_round_decimal(
                estimated_output_energy_kwh
            ),
            estimated_dc_energy_kwh=_round_decimal(
                estimated_dc_energy_kwh
            ),
            topology=sizing_input.topology,
            phase_configuration=sizing_input.phase_configuration,
            redundancy_mode=sizing_input.redundancy_mode,
            battery_technology=sizing_input.battery_technology,
            status=(
                UPSSizingStatus.NO_STANDARD_RATING_AVAILABLE
            ),
            notes=sizing_input.notes,
        )

    duty_capacity_kva = (
        selected_unit_rating_kva
        * Decimal(sizing_input.duty_modules)
    )

    total_installed_capacity_kva = (
        selected_unit_rating_kva
        * Decimal(total_installed_modules)
    )

    spare_capacity_kva = (
        duty_capacity_kva
        - derated_required_capacity_kva
    )

    loading_percent = (
        derated_required_capacity_kva
        / duty_capacity_kva
        * Decimal("100")
    )

    return UPSSizingResult(
        code=sizing_input.code,
        name=sizing_input.name,
        critical_load_kw=_round_decimal(
            sizing_input.critical_load_kw
        ),
        base_load_kva=_round_decimal(
            base_load_kva
        ),
        design_load_kva=_round_decimal(
            design_load_kva
        ),
        derated_required_capacity_kva=_round_decimal(
            derated_required_capacity_kva
        ),
        required_capacity_per_duty_module_kva=_round_decimal(
            required_capacity_per_duty_module_kva
        ),
        selected_unit_rating_kva=_round_decimal(
            selected_unit_rating_kva
        ),
        duty_modules=sizing_input.duty_modules,
        redundant_modules=sizing_input.redundant_modules,
        total_installed_modules=total_installed_modules,
        duty_capacity_kva=_round_decimal(
            duty_capacity_kva
        ),
        total_installed_capacity_kva=_round_decimal(
            total_installed_capacity_kva
        ),
        spare_capacity_kva=_round_decimal(
            spare_capacity_kva
        ),
        loading_percent=_round_decimal(
            loading_percent
        ),
        required_runtime_minutes=_round_decimal(
            sizing_input.required_runtime_minutes
        ),
        estimated_output_energy_kwh=_round_decimal(
            estimated_output_energy_kwh
        ),
        estimated_dc_energy_kwh=_round_decimal(
            estimated_dc_energy_kwh
        ),
        topology=sizing_input.topology,
        phase_configuration=sizing_input.phase_configuration,
        redundancy_mode=sizing_input.redundancy_mode,
        battery_technology=sizing_input.battery_technology,
        status=UPSSizingStatus.SELECTED,
        notes=sizing_input.notes,
    )


__all__ = [
    "calculate_ups_sizing",
]
