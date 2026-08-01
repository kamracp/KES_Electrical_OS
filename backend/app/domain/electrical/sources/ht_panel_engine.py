"""
Pure domain engine for HT panel engineering.
KESE-S2-M9
"""

from decimal import Decimal, ROUND_HALF_UP, localcontext

from app.domain.electrical.sources.ht_panel_models import (
    HTFeederInput,
    HTFeederType,
    HTPanelSizingInput,
    HTRelayFunction,
    HTSwitchingDevice,
)
from app.domain.electrical.sources.ht_panel_results import (
    HTFeederResult,
    HTPanelSizingResult,
    HTPanelSizingStatus,
    HTPanelWarning,
    HTPanelWarningCode,
)


DECIMAL_QUANTUM = Decimal("0.0001")
HIGH_LOADING_PERCENT = Decimal("90")
LOW_LOADING_PERCENT = Decimal("25")
LOW_MARGIN_FACTOR = Decimal("1.25")


def _round_value(value: Decimal) -> Decimal:
    """Round engineering values to four decimal places."""

    return value.quantize(
        DECIMAL_QUANTUM,
        rounding=ROUND_HALF_UP,
    )


def _calculate_feeder_result(
    feeder: HTFeederInput,
) -> HTFeederResult:
    """Calculate one HT feeder engineering result."""

    with localcontext() as context:
        context.prec = 50

        current_loading_percent = (
            feeder.design_current_a
            / feeder.rated_normal_current_a
            * Decimal("100")
        )

        breaking_capacity_margin_ka = (
            feeder.rated_short_circuit_breaking_current_ka
            - feeder.prospective_short_circuit_current_ka
        )

        short_time_withstand_margin_ka = (
            feeder.rated_short_time_withstand_current_ka
            - feeder.prospective_short_circuit_current_ka
        )

        ct_margin_a = (
            feeder.ct_primary_current_a
            - feeder.design_current_a
        )

    warnings: list[HTPanelWarning] = []

    if (
        feeder.rated_short_circuit_breaking_current_ka
        < feeder.prospective_short_circuit_current_ka
        * LOW_MARGIN_FACTOR
    ):
        warnings.append(
            HTPanelWarning(
                code=(
                    HTPanelWarningCode
                    .BREAKING_CAPACITY_MARGIN_LOW
                ),
                message=(
                    "HT feeder breaking-capacity margin is "
                    "below 25 percent."
                ),
            )
        )

    if (
        feeder.rated_short_time_withstand_current_ka
        < feeder.prospective_short_circuit_current_ka
        * LOW_MARGIN_FACTOR
    ):
        warnings.append(
            HTPanelWarning(
                code=(
                    HTPanelWarningCode
                    .SHORT_TIME_WITHSTAND_MARGIN_LOW
                ),
                message=(
                    "HT feeder short-time withstand margin is "
                    "below 25 percent."
                ),
            )
        )

    if (
        feeder.ct_primary_current_a
        < feeder.design_current_a
        * LOW_MARGIN_FACTOR
    ):
        warnings.append(
            HTPanelWarning(
                code=HTPanelWarningCode.CT_RATIO_MARGIN_LOW,
                message=(
                    "CT primary-current margin is below "
                    "25 percent."
                ),
            )
        )

    return HTFeederResult(
        code=feeder.code,
        name=feeder.name,
        feeder_type=feeder.feeder_type,
        switching_device=feeder.switching_device,
        design_current_a=feeder.design_current_a,
        rated_normal_current_a=(
            feeder.rated_normal_current_a
        ),
        current_loading_percent=_round_value(
            current_loading_percent
        ),
        prospective_short_circuit_current_ka=(
            feeder.prospective_short_circuit_current_ka
        ),
        rated_short_circuit_breaking_current_ka=(
            feeder.rated_short_circuit_breaking_current_ka
        ),
        breaking_capacity_margin_ka=_round_value(
            breaking_capacity_margin_ka
        ),
        rated_short_time_withstand_current_ka=(
            feeder.rated_short_time_withstand_current_ka
        ),
        short_time_withstand_margin_ka=_round_value(
            short_time_withstand_margin_ka
        ),
        short_time_withstand_duration_s=(
            feeder.short_time_withstand_duration_s
        ),
        rated_peak_withstand_current_ka=(
            feeder.rated_peak_withstand_current_ka
        ),
        ct_primary_current_a=feeder.ct_primary_current_a,
        ct_secondary_current_a=feeder.ct_secondary_current_a,
        ct_ratio=(
            f"{feeder.ct_primary_current_a.normalize()}/"
            f"{feeder.ct_secondary_current_a.normalize()}"
        ),
        ct_margin_a=_round_value(ct_margin_a),
        relay_functions=feeder.relay_functions,
        warnings=tuple(warnings),
    )


def _build_spare_feeder_result(
    panel: HTPanelSizingInput,
    sequence: int,
) -> HTFeederResult:
    """Build one reserved spare-panel compartment result."""

    return HTFeederResult(
        code=f"{panel.code}-SPARE-{sequence:02d}",
        name=f"Reserved Spare HT Feeder {sequence}",
        feeder_type=HTFeederType.OUTGOING_FEEDER,
        switching_device=HTSwitchingDevice.VCB,
        design_current_a=Decimal("0"),
        rated_normal_current_a=panel.busbar_rated_current_a,
        current_loading_percent=Decimal("0"),
        prospective_short_circuit_current_ka=Decimal("0"),
        rated_short_circuit_breaking_current_ka=(
            panel.busbar_short_time_withstand_current_ka
        ),
        breaking_capacity_margin_ka=(
            panel.busbar_short_time_withstand_current_ka
        ),
        rated_short_time_withstand_current_ka=(
            panel.busbar_short_time_withstand_current_ka
        ),
        short_time_withstand_margin_ka=(
            panel.busbar_short_time_withstand_current_ka
        ),
        short_time_withstand_duration_s=(
            panel.busbar_short_time_duration_s
        ),
        rated_peak_withstand_current_ka=(
            panel.busbar_peak_withstand_current_ka
        ),
        ct_primary_current_a=panel.busbar_rated_current_a,
        ct_secondary_current_a=Decimal("1"),
        ct_ratio=(
            f"{panel.busbar_rated_current_a.normalize()}/1"
        ),
        ct_margin_a=panel.busbar_rated_current_a,
        relay_functions=(
            HTRelayFunction.OVERCURRENT,
            HTRelayFunction.EARTH_FAULT,
        ),
        warnings=(),
    )


def calculate_ht_panel_sizing(
    sizing_input: HTPanelSizingInput,
) -> HTPanelSizingResult:
    """Calculate HT panel, busbar, feeder and CT engineering KPIs."""

    if not isinstance(
        sizing_input,
        HTPanelSizingInput,
    ):
        raise TypeError(
            "sizing_input must be an HTPanelSizingInput record"
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

        maximum_feeder_current_a = max(
            feeder.rated_normal_current_a
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

    warnings: list[HTPanelWarning] = []

    if busbar_loading_percent >= HIGH_LOADING_PERCENT:
        warnings.append(
            HTPanelWarning(
                code=HTPanelWarningCode.HIGH_BUSBAR_LOADING,
                message=(
                    "Calculated HT busbar loading is at or "
                    "above 90 percent."
                ),
            )
        )

    if busbar_loading_percent < LOW_LOADING_PERCENT:
        warnings.append(
            HTPanelWarning(
                code=HTPanelWarningCode.LOW_BUSBAR_LOADING,
                message=(
                    "Calculated HT busbar loading is below "
                    "25 percent; review possible oversizing."
                ),
            )
        )

    if sizing_input.arc_classification_required:
        warnings.append(
            HTPanelWarning(
                code=(
                    HTPanelWarningCode
                    .ARC_CLASSIFICATION_REQUIRED
                ),
                message=(
                    "Internal arc classification and installation "
                    "conditions require project verification."
                ),
            )
        )

    if (
        sizing_input.installation.value == "OUTDOOR"
        and not sizing_input.remote_operation_required
    ):
        warnings.append(
            HTPanelWarning(
                code=(
                    HTPanelWarningCode
                    .REMOTE_OPERATION_RECOMMENDED
                ),
                message=(
                    "Remote breaker operation should be reviewed "
                    "for outdoor HT switchgear."
                ),
            )
        )

    status = (
        HTPanelSizingStatus.WARNING
        if warnings
        or any(
            result.warnings
            for result in active_feeder_results
        )
        else HTPanelSizingStatus.VALID
    )

    return HTPanelSizingResult(
        code=sizing_input.code,
        name=sizing_input.name,
        system_voltage=sizing_input.system_voltage,
        installation=sizing_input.installation,
        construction=sizing_input.construction,
        total_feeders=len(feeder_results),
        active_feeders=len(active_feeder_results),
        spare_feeders=len(spare_feeder_results),
        bus_sections=sizing_input.bus_sections,
        bus_couplers=sizing_input.bus_couplers,
        maximum_feeder_current_a=_round_value(
            maximum_feeder_current_a
        ),
        aggregate_design_current_a=_round_value(
            aggregate_design_current_a
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
        feeder_results=feeder_results,
        status=status,
        warnings=tuple(warnings),
    )


__all__ = [
    "calculate_ht_panel_sizing",
]
