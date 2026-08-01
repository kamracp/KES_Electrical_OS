"""
Solar PV source-sizing calculation engine.
KESE-S2-M8
"""

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP, localcontext

from app.domain.electrical.sources.pv_models import (
    PVSizingInput,
)
from app.domain.electrical.sources.pv_results import (
    PVSizingResult,
    PVSizingStatus,
    PVSizingWarning,
    PVSizingWarningCode,
)


CAPACITY_QUANTUM = Decimal("0.0001")
VOLTAGE_QUANTUM = Decimal("0.0001")
RATIO_QUANTUM = Decimal("0.0001")

HIGH_DC_AC_RATIO = Decimal("1.40")
LOW_DC_AC_RATIO = Decimal("0.90")
STC_TEMPERATURE_C = Decimal("25")


@dataclass(frozen=True, slots=True)
class _RawPVSizingValues:
    """Unrounded internal Solar PV sizing values."""

    future_required_ac_output_kw: Decimal
    design_required_ac_output_kw: Decimal
    required_dc_array_capacity_kwp: Decimal

    cold_corrected_module_voc_v: Decimal
    hot_corrected_module_vmp_v: Decimal

    maximum_modules_per_string: int
    minimum_modules_per_string: int
    modules_per_string: int

    total_modules: int
    total_strings: int
    strings_per_mppt: int

    cold_string_voc_v: Decimal
    hot_string_vmp_v: Decimal

    required_inverter_capacity_kw: Decimal
    required_unit_rating_kw: Decimal


def _round_decimal(
    value: Decimal,
    quantum: Decimal = CAPACITY_QUANTUM,
) -> Decimal:
    """Round an engineering value."""

    return value.quantize(
        quantum,
        rounding=ROUND_HALF_UP,
    )


def _ceiling_decimal_to_int(
    value: Decimal,
) -> int:
    """Round a positive Decimal upward to an integer."""

    integral = int(value)

    if Decimal(integral) < value:
        return integral + 1

    return integral


def _calculate_temperature_corrected_voltage(
    base_voltage_v: Decimal,
    temperature_coefficient_percent_per_c: Decimal,
    design_temperature_c: Decimal,
) -> Decimal:
    """Apply the module voltage temperature coefficient."""

    temperature_difference_c = (
        design_temperature_c
        - STC_TEMPERATURE_C
    )

    correction_factor = (
        Decimal("1")
        + (
            temperature_coefficient_percent_per_c
            / Decimal("100")
            * temperature_difference_c
        )
    )

    return base_voltage_v * correction_factor


def _calculate_raw_values(
    sizing_input: PVSizingInput,
) -> _RawPVSizingValues:
    """Calculate unrounded Solar PV sizing values."""

    with localcontext() as context:
        context.prec = 50

        future_required_ac_output_kw = (
            sizing_input.required_ac_output_kw
            * sizing_input.future_growth_factor
        )

        design_required_ac_output_kw = (
            future_required_ac_output_kw
            * sizing_input.design_margin_factor
        )

        required_inverter_capacity_kw = (
            design_required_ac_output_kw
            / sizing_input.ac_efficiency_factor
        )

        required_dc_array_capacity_kwp = (
            required_inverter_capacity_kw
            * sizing_input.target_dc_ac_ratio
            / sizing_input.dc_efficiency_factor
        )

        cold_corrected_module_voc_v = (
            _calculate_temperature_corrected_voltage(
                sizing_input.module_open_circuit_voltage_v,
                sizing_input
                .temperature_coefficient_voc_percent_per_c,
                sizing_input.minimum_design_temperature_c,
            )
        )

        hot_corrected_module_vmp_v = (
            _calculate_temperature_corrected_voltage(
                sizing_input.module_maximum_power_voltage_v,
                sizing_input
                .temperature_coefficient_vmp_percent_per_c,
                sizing_input.maximum_cell_temperature_c,
            )
        )

        maximum_modules_per_string = int(
            sizing_input.inverter_max_dc_voltage_v
            / cold_corrected_module_voc_v
        )

        minimum_modules_per_string = (
            _ceiling_decimal_to_int(
                sizing_input.inverter_mppt_min_voltage_v
                / hot_corrected_module_vmp_v
            )
        )

        modules_per_string = min(
            maximum_modules_per_string,
            int(
                sizing_input.inverter_mppt_max_voltage_v
                / sizing_input.module_maximum_power_voltage_v
            ),
        )

        total_modules = _ceiling_decimal_to_int(
            required_dc_array_capacity_kwp
            * Decimal("1000")
            / sizing_input.module_rated_power_wp
        )

        total_strings = _ceiling_decimal_to_int(
            Decimal(total_modules)
            / Decimal(modules_per_string)
        )

        strings_per_mppt = _ceiling_decimal_to_int(
            Decimal(total_strings)
            / (
                Decimal(sizing_input.mppt_count)
                * Decimal(sizing_input.duty_inverters)
            )
        )

        cold_string_voc_v = (
            cold_corrected_module_voc_v
            * Decimal(modules_per_string)
        )

        hot_string_vmp_v = (
            hot_corrected_module_vmp_v
            * Decimal(modules_per_string)
        )

        required_unit_rating_kw = (
            required_inverter_capacity_kw
            / Decimal(sizing_input.duty_inverters)
        )

    return _RawPVSizingValues(
        future_required_ac_output_kw=(
            future_required_ac_output_kw
        ),
        design_required_ac_output_kw=(
            design_required_ac_output_kw
        ),
        required_dc_array_capacity_kwp=(
            required_dc_array_capacity_kwp
        ),
        cold_corrected_module_voc_v=(
            cold_corrected_module_voc_v
        ),
        hot_corrected_module_vmp_v=(
            hot_corrected_module_vmp_v
        ),
        maximum_modules_per_string=(
            maximum_modules_per_string
        ),
        minimum_modules_per_string=(
            minimum_modules_per_string
        ),
        modules_per_string=modules_per_string,
        total_modules=total_modules,
        total_strings=total_strings,
        strings_per_mppt=strings_per_mppt,
        cold_string_voc_v=cold_string_voc_v,
        hot_string_vmp_v=hot_string_vmp_v,
        required_inverter_capacity_kw=(
            required_inverter_capacity_kw
        ),
        required_unit_rating_kw=(
            required_unit_rating_kw
        ),
    )


def _select_inverter_rating(
    sizing_input: PVSizingInput,
    required_unit_rating_kw: Decimal,
) -> Decimal | None:
    """Select the smallest adequate inverter rating."""

    return next(
        (
            rating
            for rating
            in sizing_input.available_inverter_ratings_kw
            if rating >= required_unit_rating_kw
        ),
        None,
    )


def _build_common_warnings(
    sizing_input: PVSizingInput,
    raw_values: _RawPVSizingValues,
) -> list[PVSizingWarning]:
    """Build common Solar PV engineering warnings."""

    warnings: list[PVSizingWarning] = []

    if (
        raw_values.cold_string_voc_v
        > sizing_input.inverter_max_dc_voltage_v
    ):
        warnings.append(
            PVSizingWarning(
                code=PVSizingWarningCode.COLD_VOC_LIMIT,
                message=(
                    "Cold-condition string open-circuit voltage "
                    "exceeds the inverter maximum DC voltage."
                ),
            )
        )

    if (
        raw_values.hot_string_vmp_v
        < sizing_input.inverter_mppt_min_voltage_v
    ):
        warnings.append(
            PVSizingWarning(
                code=(
                    PVSizingWarningCode
                    .HOT_VMP_BELOW_MPPT
                ),
                message=(
                    "Hot-condition string operating voltage "
                    "is below the inverter MPPT minimum."
                ),
            )
        )

    string_input_current_a = (
        sizing_input.module_short_circuit_current_a
        * Decimal(raw_values.strings_per_mppt)
    )

    if (
        string_input_current_a
        > sizing_input
        .inverter_max_input_current_per_mppt_a
    ):
        warnings.append(
            PVSizingWarning(
                code=(
                    PVSizingWarningCode
                    .STRING_CURRENT_LIMIT
                ),
                message=(
                    "Calculated PV string current per MPPT "
                    "exceeds the inverter input-current limit."
                ),
            )
        )

    if sizing_input.export_limit_kw is not None:
        warnings.append(
            PVSizingWarning(
                code=(
                    PVSizingWarningCode
                    .EXPORT_LIMIT_APPLIED
                ),
                message=(
                    "An active-power export limit is applied "
                    "to the Solar PV system."
                ),
            )
        )

    if sizing_input.dg_coexistence:
        warnings.append(
            PVSizingWarning(
                code=(
                    PVSizingWarningCode
                    .DG_COORDINATION_REQUIRED
                ),
                message=(
                    "PV and generator coexistence requires "
                    "a dedicated control and protection study."
                ),
            )
        )

    return warnings


def calculate_pv_sizing(
    sizing_input: PVSizingInput,
) -> PVSizingResult:
    """Calculate and select a Solar PV source arrangement."""

    if not isinstance(sizing_input, PVSizingInput):
        raise TypeError(
            "sizing_input must be a PVSizingInput record"
        )

    raw_values = _calculate_raw_values(sizing_input)

    selected_unit_rating_kw = _select_inverter_rating(
        sizing_input,
        raw_values.required_unit_rating_kw,
    )

    warnings = _build_common_warnings(
        sizing_input,
        raw_values,
    )

    total_inverters = (
        sizing_input.duty_inverters
        + sizing_input.redundant_inverters
    )

    if selected_unit_rating_kw is None:
        warnings.append(
            PVSizingWarning(
                code=(
                    PVSizingWarningCode
                    .NO_STANDARD_INVERTER_RATING
                ),
                message=(
                    "No available inverter rating satisfies "
                    "the calculated unit capacity requirement."
                ),
            )
        )

        return PVSizingResult(
            code=sizing_input.code,
            name=sizing_input.name,
            scenario=sizing_input.scenario,
            system_type=sizing_input.system_type,
            phase_configuration=(
                sizing_input.phase_configuration
            ),
            redundancy_mode=sizing_input.redundancy_mode,
            battery_configuration=(
                sizing_input.battery_configuration
            ),
            required_ac_output_kw=(
                sizing_input.required_ac_output_kw
            ),
            future_required_ac_output_kw=_round_decimal(
                raw_values.future_required_ac_output_kw
            ),
            design_required_ac_output_kw=_round_decimal(
                raw_values.design_required_ac_output_kw
            ),
            target_dc_ac_ratio=sizing_input.target_dc_ac_ratio,
            required_dc_array_capacity_kwp=_round_decimal(
                raw_values.required_dc_array_capacity_kwp
            ),
            module_rated_power_wp=(
                sizing_input.module_rated_power_wp
            ),
            total_modules=raw_values.total_modules,
            modules_per_string=raw_values.modules_per_string,
            total_strings=raw_values.total_strings,
            strings_per_mppt=raw_values.strings_per_mppt,
            cold_corrected_module_voc_v=_round_decimal(
                raw_values.cold_corrected_module_voc_v,
                VOLTAGE_QUANTUM,
            ),
            hot_corrected_module_vmp_v=_round_decimal(
                raw_values.hot_corrected_module_vmp_v,
                VOLTAGE_QUANTUM,
            ),
            cold_string_voc_v=_round_decimal(
                raw_values.cold_string_voc_v,
                VOLTAGE_QUANTUM,
            ),
            hot_string_vmp_v=_round_decimal(
                raw_values.hot_string_vmp_v,
                VOLTAGE_QUANTUM,
            ),
            string_short_circuit_current_a=(
                sizing_input.module_short_circuit_current_a
            ),
            required_inverter_capacity_kw=_round_decimal(
                raw_values.required_inverter_capacity_kw
            ),
            required_unit_rating_kw=_round_decimal(
                raw_values.required_unit_rating_kw
            ),
            selected_unit_rating_kw=None,
            duty_inverters=sizing_input.duty_inverters,
            redundant_inverters=(
                sizing_input.redundant_inverters
            ),
            total_inverters=total_inverters,
            installed_duty_capacity_kw=None,
            total_installed_capacity_kw=None,
            actual_dc_ac_ratio=None,
            spare_ac_capacity_kw=None,
            export_limit_kw=sizing_input.export_limit_kw,
            dg_coexistence=sizing_input.dg_coexistence,
            status=PVSizingStatus.NO_SOLUTION,
            warnings=tuple(warnings),
        )

    installed_duty_capacity_kw = (
        selected_unit_rating_kw
        * Decimal(sizing_input.duty_inverters)
    )

    total_installed_capacity_kw = (
        selected_unit_rating_kw
        * Decimal(total_inverters)
    )

    actual_dc_ac_ratio = (
        raw_values.required_dc_array_capacity_kwp
        / installed_duty_capacity_kw
    )

    spare_ac_capacity_kw = (
        installed_duty_capacity_kw
        - raw_values.required_inverter_capacity_kw
    )

    if actual_dc_ac_ratio > HIGH_DC_AC_RATIO:
        warnings.append(
            PVSizingWarning(
                code=PVSizingWarningCode.HIGH_DC_AC_RATIO,
                message=(
                    "Calculated DC-to-AC ratio is above 1.40."
                ),
            )
        )

    if actual_dc_ac_ratio < LOW_DC_AC_RATIO:
        warnings.append(
            PVSizingWarning(
                code=PVSizingWarningCode.LOW_DC_AC_RATIO,
                message=(
                    "Calculated DC-to-AC ratio is below 0.90."
                ),
            )
        )

    status = (
        PVSizingStatus.WARNING
        if warnings
        else PVSizingStatus.VALID
    )

    return PVSizingResult(
        code=sizing_input.code,
        name=sizing_input.name,
        scenario=sizing_input.scenario,
        system_type=sizing_input.system_type,
        phase_configuration=sizing_input.phase_configuration,
        redundancy_mode=sizing_input.redundancy_mode,
        battery_configuration=sizing_input.battery_configuration,
        required_ac_output_kw=sizing_input.required_ac_output_kw,
        future_required_ac_output_kw=_round_decimal(
            raw_values.future_required_ac_output_kw
        ),
        design_required_ac_output_kw=_round_decimal(
            raw_values.design_required_ac_output_kw
        ),
        target_dc_ac_ratio=sizing_input.target_dc_ac_ratio,
        required_dc_array_capacity_kwp=_round_decimal(
            raw_values.required_dc_array_capacity_kwp
        ),
        module_rated_power_wp=sizing_input.module_rated_power_wp,
        total_modules=raw_values.total_modules,
        modules_per_string=raw_values.modules_per_string,
        total_strings=raw_values.total_strings,
        strings_per_mppt=raw_values.strings_per_mppt,
        cold_corrected_module_voc_v=_round_decimal(
            raw_values.cold_corrected_module_voc_v,
            VOLTAGE_QUANTUM,
        ),
        hot_corrected_module_vmp_v=_round_decimal(
            raw_values.hot_corrected_module_vmp_v,
            VOLTAGE_QUANTUM,
        ),
        cold_string_voc_v=_round_decimal(
            raw_values.cold_string_voc_v,
            VOLTAGE_QUANTUM,
        ),
        hot_string_vmp_v=_round_decimal(
            raw_values.hot_string_vmp_v,
            VOLTAGE_QUANTUM,
        ),
        string_short_circuit_current_a=(
            sizing_input.module_short_circuit_current_a
        ),
        required_inverter_capacity_kw=_round_decimal(
            raw_values.required_inverter_capacity_kw
        ),
        required_unit_rating_kw=_round_decimal(
            raw_values.required_unit_rating_kw
        ),
        selected_unit_rating_kw=selected_unit_rating_kw,
        duty_inverters=sizing_input.duty_inverters,
        redundant_inverters=sizing_input.redundant_inverters,
        total_inverters=total_inverters,
        installed_duty_capacity_kw=_round_decimal(
            installed_duty_capacity_kw
        ),
        total_installed_capacity_kw=_round_decimal(
            total_installed_capacity_kw
        ),
        actual_dc_ac_ratio=_round_decimal(
            actual_dc_ac_ratio,
            RATIO_QUANTUM,
        ),
        spare_ac_capacity_kw=_round_decimal(
            spare_ac_capacity_kw
        ),
        export_limit_kw=sizing_input.export_limit_kw,
        dg_coexistence=sizing_input.dg_coexistence,
        status=status,
        warnings=tuple(warnings),
    )


__all__ = [
    "calculate_pv_sizing",
]
