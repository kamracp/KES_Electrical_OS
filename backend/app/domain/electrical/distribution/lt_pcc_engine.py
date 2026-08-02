"""
Pure domain engine for LT PCC / Main Panel engineering.
KESE-S2-M10
"""

from decimal import Decimal, ROUND_HALF_UP, localcontext

from app.domain.electrical.distribution.lt_pcc_models import (
    LTFeederInput,
    LTFeederType,
    LTPCCSizingInput,
    LTSwitchingDevice,
    LTTripUnitType,
)
from app.domain.electrical.distribution.lt_pcc_results import (
    LTFeederResult,
    LTPCCSizingResult,
    LTPCCSizingStatus,
    LTPCCWarning,
    LTPCCWarningCode,
)


DECIMAL_QUANTUM = Decimal("0.0001")
HIGH_LOADING_PERCENT = Decimal("90")
LOW_LOADING_PERCENT = Decimal("25")
LOW_MARGIN_FACTOR = Decimal("1.25")
LOW_SPARE_CAPACITY_PERCENT = Decimal("10")


def _round_value(value: Decimal) -> Decimal:
    """Round engineering values to four decimal places."""

    return value.quantize(
        DECIMAL_QUANTUM,
        rounding=ROUND_HALF_UP,
    )


def _calculate_feeder_result(
    feeder: LTFeederInput,
) -> LTFeederResult:
    """Calculate one LT feeder engineering result."""

    with localcontext() as context:
        context.prec = 50

        loading_percent = (
            feeder.design_current_a
            / feeder.rated_current_a
            * Decimal("100")
        )

        spare_current_capacity_a = (
            feeder.rated_current_a
            - feeder.design_current_a
        )

        icu_margin_ka = (
            feeder.rated_ultimate_breaking_capacity_ka
            - feeder.prospective_short_circuit_current_ka
        )

        ics_margin_ka = (
            feeder.rated_service_breaking_capacity_ka
            - feeder.prospective_short_circuit_current_ka
        )

        icw_margin_ka = (
            feeder.rated_short_time_withstand_current_ka
            - feeder.prospective_short_circuit_current_ka
        )

    warnings: list[LTPCCWarning] = []

    if (
        feeder.rated_ultimate_breaking_capacity_ka
        < feeder.prospective_short_circuit_current_ka
        * LOW_MARGIN_FACTOR
    ):
        warnings.append(
            LTPCCWarning(
                code=LTPCCWarningCode.ICU_MARGIN_LOW,
                message=(
                    "Feeder Icu margin is below 25 percent."
                ),
            )
        )

    if (
        feeder.rated_service_breaking_capacity_ka
        < feeder.prospective_short_circuit_current_ka
        * LOW_MARGIN_FACTOR
    ):
        warnings.append(
            LTPCCWarning(
                code=LTPCCWarningCode.ICS_MARGIN_LOW,
                message=(
                    "Feeder Ics margin is below 25 percent."
                ),
            )
        )

    if (
        feeder.rated_short_time_withstand_current_ka
        < feeder.prospective_short_circuit_current_ka
        * LOW_MARGIN_FACTOR
    ):
        warnings.append(
            LTPCCWarning(
                code=LTPCCWarningCode.ICW_MARGIN_LOW,
                message=(
                    "Feeder Icw margin is below 25 percent."
                ),
            )
        )

    spare_capacity_percent = (
        spare_current_capacity_a
        / feeder.rated_current_a
        * Decimal("100")
    )

    if (
        spare_capacity_percent
        < LOW_SPARE_CAPACITY_PERCENT
    ):
        warnings.append(
            LTPCCWarning(
                code=(
                    LTPCCWarningCode
                    .LOW_FEEDER_SPARE_CAPACITY
                ),
                message=(
                    "Feeder spare current capacity is below "
                    "10 percent."
                ),
            )
        )

    return LTFeederResult(
        code=feeder.code,
        name=feeder.name,
        feeder_type=feeder.feeder_type,
        switching_device=feeder.switching_device,
        trip_unit_type=feeder.trip_unit_type,
        design_current_a=feeder.design_current_a,
        rated_current_a=feeder.rated_current_a,
        loading_percent=_round_value(
            loading_percent
        ),
        spare_current_capacity_a=_round_value(
            spare_current_capacity_a
        ),
        prospective_short_circuit_current_ka=(
            feeder.prospective_short_circuit_current_ka
        ),
        rated_ultimate_breaking_capacity_ka=(
            feeder.rated_ultimate_breaking_capacity_ka
        ),
        icu_margin_ka=_round_value(
            icu_margin_ka
        ),
        rated_service_breaking_capacity_ka=(
            feeder.rated_service_breaking_capacity_ka
        ),
        ics_margin_ka=_round_value(
            ics_margin_ka
        ),
        rated_short_time_withstand_current_ka=(
            feeder.rated_short_time_withstand_current_ka
        ),
        icw_margin_ka=_round_value(
            icw_margin_ka
        ),
        number_of_poles=feeder.number_of_poles,
        cable_count=feeder.cable_count,
        spare_feeder=feeder.spare_feeder,
        warnings=tuple(warnings),
    )


def _build_spare_feeder_result(
    panel: LTPCCSizingInput,
    sequence: int,
) -> LTFeederResult:
    """Build one reserved spare feeder result."""

    return LTFeederResult(
        code=f"{panel.code}-SPARE-{sequence:02d}",
        name=f"Reserved Spare LT Feeder {sequence}",
        feeder_type=LTFeederType.SPARE_FEEDER,
        switching_device=LTSwitchingDevice.MCCB,
        trip_unit_type=LTTripUnitType.ELECTRONIC_LSI,
        design_current_a=Decimal("0"),
        rated_current_a=panel.busbar_rated_current_a,
        loading_percent=Decimal("0"),
        spare_current_capacity_a=panel.busbar_rated_current_a,
        prospective_short_circuit_current_ka=Decimal("0"),
        rated_ultimate_breaking_capacity_ka=(
            panel.busbar_short_time_withstand_current_ka
        ),
        icu_margin_ka=(
            panel.busbar_short_time_withstand_current_ka
        ),
        rated_service_breaking_capacity_ka=(
            panel.busbar_short_time_withstand_current_ka
        ),
        ics_margin_ka=(
            panel.busbar_short_time_withstand_current_ka
        ),
        rated_short_time_withstand_current_ka=(
            panel.busbar_short_time_withstand_current_ka
        ),
        icw_margin_ka=(
            panel.busbar_short_time_withstand_current_ka
        ),
        number_of_poles=4,
        cable_count=1,
        spare_feeder=True,
        warnings=(),
    )


def calculate_lt_pcc_sizing(
    sizing_input: LTPCCSizingInput,
) -> LTPCCSizingResult:
    """Calculate LT PCC, busbar and feeder engineering KPIs."""

    if not isinstance(
        sizing_input,
        LTPCCSizingInput,
    ):
        raise TypeError(
            "sizing_input must be an LTPCCSizingInput record"
        )

    active_feeder_results = tuple(
        _calculate_feeder_result(feeder)
        for feeder in sizing_input.feeders
    )

    spare_feeder_results = tuple(
        _build_spare_feeder_result(
            sizing_input,
            sequence,
        )
        for sequence in range(
            1,
            sizing_input.spare_feeders + 1,
        )
    )

    feeder_results = (
        active_feeder_results
        + spare_feeder_results
    )

    with localcontext() as context:
        context.prec = 50

        aggregate_design_current_a = sum(
            (
                feeder.design_current_a
                for feeder in sizing_input.feeders
            ),
            Decimal("0"),
        )

        maximum_feeder_rated_current_a = max(
            feeder.rated_current_a
            for feeder in sizing_input.feeders
        )

        maximum_fault_current_ka = max(
            feeder.prospective_short_circuit_current_ka
            for feeder in sizing_input.feeders
        )

        busbar_loading_percent = (
            aggregate_design_current_a
            / sizing_input.busbar_rated_current_a
            * Decimal("100")
        )

        busbar_spare_capacity_a = (
            sizing_input.busbar_rated_current_a
            - aggregate_design_current_a
        )

        busbar_fault_margin_ka = (
            sizing_input
            .busbar_short_time_withstand_current_ka
            - maximum_fault_current_ka
        )

    warnings: list[LTPCCWarning] = []

    if busbar_loading_percent >= HIGH_LOADING_PERCENT:
        warnings.append(
            LTPCCWarning(
                code=LTPCCWarningCode.HIGH_BUSBAR_LOADING,
                message=(
                    "Calculated LT busbar loading is at or "
                    "above 90 percent."
                ),
            )
        )

    if busbar_loading_percent < LOW_LOADING_PERCENT:
        warnings.append(
            LTPCCWarning(
                code=LTPCCWarningCode.LOW_BUSBAR_LOADING,
                message=(
                    "Calculated LT busbar loading is below "
                    "25 percent; review possible oversizing."
                ),
            )
        )

    if sizing_input.apfc_required:
        warnings.append(
            LTPCCWarning(
                code=LTPCCWarningCode.APFC_REVIEW_REQUIRED,
                message=(
                    "APFC duty, harmonic environment and "
                    "detuning requirements require review."
                ),
            )
        )

    if (
        sizing_input.installation.value == "OUTDOOR"
        and not sizing_input.remote_operation_required
    ):
        warnings.append(
            LTPCCWarning(
                code=(
                    LTPCCWarningCode
                    .REMOTE_OPERATION_RECOMMENDED
                ),
                message=(
                    "Remote breaker operation should be reviewed "
                    "for outdoor LT switchgear."
                ),
            )
        )

    status = (
        LTPCCSizingStatus.WARNING
        if warnings
        or any(
            result.warnings
            for result in active_feeder_results
        )
        else LTPCCSizingStatus.VALID
    )

    return LTPCCSizingResult(
        code=sizing_input.code,
        name=sizing_input.name,
        system_voltage=sizing_input.system_voltage,
        installation=sizing_input.installation,
        form_of_separation=sizing_input.form_of_separation,
        total_feeders=len(feeder_results),
        active_feeders=len(active_feeder_results),
        spare_feeders=len(spare_feeder_results),
        bus_sections=sizing_input.bus_sections,
        bus_couplers=sizing_input.bus_couplers,
        aggregate_design_current_a=_round_value(
            aggregate_design_current_a
        ),
        maximum_feeder_rated_current_a=_round_value(
            maximum_feeder_rated_current_a
        ),
        busbar_rated_current_a=(
            sizing_input.busbar_rated_current_a
        ),
        busbar_loading_percent=_round_value(
            busbar_loading_percent
        ),
        busbar_spare_capacity_a=_round_value(
            busbar_spare_capacity_a
        ),
        maximum_fault_current_ka=_round_value(
            maximum_fault_current_ka
        ),
        busbar_short_time_withstand_current_ka=(
            sizing_input
            .busbar_short_time_withstand_current_ka
        ),
        busbar_fault_margin_ka=_round_value(
            busbar_fault_margin_ka
        ),
        busbar_peak_withstand_current_ka=(
            sizing_input.busbar_peak_withstand_current_ka
        ),
        neutral_bus_rating_percent=(
            sizing_input.neutral_bus_rating_percent
        ),
        earth_bus_rating_percent=(
            sizing_input.earth_bus_rating_percent
        ),
        apfc_required=sizing_input.apfc_required,
        metering_required=sizing_input.metering_required,
        remote_operation_required=(
            sizing_input.remote_operation_required
        ),
        feeder_results=feeder_results,
        status=status,
        warnings=tuple(warnings),
    )


__all__ = [
    "calculate_lt_pcc_sizing",
]
